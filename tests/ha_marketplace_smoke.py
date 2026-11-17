"""Offline real Home Assistant 2026.11 Marketplace transactions.

Run separately from worker/stub tests (which replace HA modules)::

    python -B tests/ha_marketplace_smoke.py

Uses the real MarketplaceManager / IntegrationRepository catalog install API,
HA loader discovery, backup/extraction/rollback and Marketplace Store persistence.
Only delivery is replaced with explicitly named local ZIP/raw-file fixtures and
an inert real aiohttp session. No install/copy/rollback/validator is mocked.
The candidate integration source is read from the current working tree; manifest
versions and refs are synthetic fixture variants, NOT actual released versions.
Negative ZIP manifests deliberately disagree with valid raw metadata to reach
the real post-write check and rollback, rather than preflight validation alone.

Limitations: no frontend, live catalog/GitHub, config-flow/setup or hardware E2E;
no running recorder. Real HA Store data and a SQLite history identity fixture
outside custom_components are checked unchanged. No existing user config is used.
All temporary configuration/archive/backup files stay beneath scratch. DNS and
socket connections are fail-closed. Installed HA sources are hashed before/after.
"""
import socket
import unittest
from contextlib import closing, contextmanager


@contextmanager
def offline_guard():
    """Block DNS and outbound socket operations, including worker threads."""
    from contextlib import ExitStack
    from unittest.mock import patch

    def forbidden(*args, **kwargs):
        raise AssertionError("network forbidden: offline test fixture only")

    with ExitStack() as stack:
        for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr", "create_connection"):
            stack.enter_context(patch.object(socket, name, forbidden))
        for name in ("connect", "connect_ex", "sendto"):
            stack.enter_context(patch.object(socket.socket, name, forbidden))
        yield


class OfflineGuardTests(unittest.TestCase):
    def test_dns_and_connections_are_denied_without_network(self):
        with offline_guard():
            for operation, args in (
                (socket.getaddrinfo, ("fixture.invalid", 443)),
                (socket.gethostbyname, ("fixture.invalid",)),
                (socket.create_connection, (("192.0.2.1", 443),)),
            ):
                with self.assertRaisesRegex(AssertionError, "network forbidden"):
                    operation(*args)
            with socket.socket() as client:
                with self.assertRaisesRegex(AssertionError, "network forbidden"):
                    client.connect(("192.0.2.1", 443))


class FixtureBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_explicit_local_delivery_keys_are_served(self):
        fixture = LocalCandidateDeliveryFixture({"fixture/path": b"local-only"})
        self.assertEqual(await fixture.download(type("RemoteFixture", (), {"path": "fixture/path"})()), b"local-only")
        with self.assertRaisesRegex(AssertionError, "unmapped local fixture"):
            await fixture.download(type("RemoteFixture", (), {"path": "unknown"})())


class LocalCandidateDeliveryFixture:
    """The sole content delivery fake; NOT a real catalog or published release."""
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []

    async def download(self, remote, **kwargs):
        self.calls.append(remote.path)
        if remote.path not in self.payloads:
            raise AssertionError(f"unmapped local fixture: {remote.path}")
        return self.payloads[remote.path]


import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import MappingProxyType
from unittest.mock import patch
import zipfile

from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry, ConfigEntries
from homeassistant.components.lovelace import LOVELACE_DATA, LovelaceData
from homeassistant.components.lovelace.resources import ResourceYAMLCollection
from homeassistant.components.marketplace.base import MarketplaceManager
from homeassistant.components.marketplace.enums import RepositoryCategory
from homeassistant.components.marketplace.exceptions import MarketplaceError
from homeassistant.components.marketplace.repositories import base as core_base
from homeassistant.components.marketplace.repositories import integration as core_integration
from homeassistant.components.marketplace.repositories.integration import IntegrationRepository
from homeassistant.helpers.storage import Store
from homeassistant.loader import async_setup as loader_async_setup

DOMAIN = "haier_smartair2"
ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT.parent


class MarketplaceTransactionTests(unittest.IsolatedAsyncioTestCase):
    """Real install, backup, extraction, validation, rollback and Store writes.

    No integration setup, config flow, recorder service, UI or GitHub E2E.
    SQLite history is a local persisted-identity fixture, not a running recorder.
    Synthetic refs below are fixture labels, never published release claims.
    """

    @classmethod
    def setUpClass(cls):
        assert HA_VERSION.startswith("2026.11."), HA_VERSION
        cls.core_hashes = {
            module.__file__: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for module in (core_base, core_integration)
        }
        candidate = ROOT / "custom_components" / DOMAIN
        cls.source_files = {}
        for path in sorted(candidate.rglob("*")):
            if "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
                continue
            if path.is_file():
                if path.is_symlink() or not path.resolve().is_relative_to(candidate.resolve()):
                    raise AssertionError(f"Candidate file escapes integration directory: {path}")
                cls.source_files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
        cls.source_hash = hashlib.sha256(json.dumps({
            name: hashlib.sha256(content).hexdigest()
            for name, content in cls.source_files.items()
        }, sort_keys=True).encode()).hexdigest()
        print(f"\nHA {HA_VERSION}; readonly working-tree candidate; source-map sha256={cls.source_hash}")
        for filename, digest in cls.core_hashes.items():
            print(f"readonly core sha256 {digest} {filename}")

    @classmethod
    def tearDownClass(cls):
        for filename, digest in cls.core_hashes.items():
            assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest

    async def asyncSetUp(self):
        self.guard = offline_guard()
        self.guard.__enter__()
        self.addCleanup(self.guard.__exit__, None, None, None)
        self.temp = tempfile.TemporaryDirectory(prefix="ha-marketplace-fixture-", dir=SCRATCH)
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name)
        self.old_tempdir = tempfile.tempdir
        tempfile.tempdir = str(self.config)
        self.addCleanup(setattr, tempfile, "tempdir", self.old_tempdir)
        self.hass = HomeAssistant(str(self.config))
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()
        loader_async_setup(self.hass)
        self.hass.data[LOVELACE_DATA] = LovelaceData(
            resource_mode="yaml", dashboards={}, resources=ResourceYAMLCollection([]), yaml_dashboards={}
        )
        entry = ConfigEntry(
            domain="marketplace", title="Local marketplace test fixture", data={}, options={},
            source="user", unique_id="marketplace-test-fixture", version=1, minor_version=1,
            discovery_keys=MappingProxyType({}), subentries_data=[]
        )
        # Real inert HTTP session at the delivery boundary. Explicit resolver
        # avoids HA's zeroconf/network bootstrap; socket guard denies its use.
        from aiohttp import ClientSession, TCPConnector, ThreadedResolver
        self.http_fixture_session = ClientSession(connector=TCPConnector(resolver=ThreadedResolver()))
        self.addAsyncCleanup(self.http_fixture_session.close)
        with patch("homeassistant.components.marketplace.base.async_get_clientsession", return_value=self.http_fixture_session):
            self.marketplace = MarketplaceManager(self.hass, entry)
        self.marketplace.enable_category(RepositoryCategory.INTEGRATION)
        self.repo = IntegrationRepository(self.marketplace, "local-test-fixture/haier-candidate")
        self.repo.data.id = "local-candidate-fixture"
        self.repo.data.domain = DOMAIN
        self.marketplace.repositories.register(self.repo, default=True)
        self.delivery = LocalCandidateDeliveryFixture({})
        self.delivery_patch = patch.object(self.marketplace, "async_download_file", self.delivery.download)
        self.delivery_patch.start()
        self.addCleanup(self.delivery_patch.stop)
        # Fail closed if the catalog fast path unexpectedly asks the GitHub API.
        self.api_patch = patch.object(self.marketplace, "async_github_api_method", side_effect=AssertionError("GitHub delivery not in local catalog fixture"))
        self.api_patch.start()
        self.addCleanup(self.api_patch.stop)
        self.target = self.config / "custom_components" / DOMAIN
        self.entry = ConfigEntry(
            domain=DOMAIN, title="Preserved identity fixture", data={"host": "192.0.2.2"}, options={},
            source="user", unique_id="fixture-device-identity", version=1, minor_version=1,
            entry_id="fixture-stable-entry-id", discovery_keys=MappingProxyType({}), subentries_data=[]
        )
        # Register without setting up the integration (would contact hardware).
        self.hass.config_entries._entries[self.entry.entry_id] = self.entry
        # Persist with HA's actual ConfigEntryStore serializer; no setup is run.
        await self.hass.config_entries._store.async_save(self.hass.config_entries._data_to_save())
        self.entries_path = self.config / ".storage/core.config_entries"
        self.entries_bytes = self.entries_path.read_bytes()
        self.store = Store(self.hass, 1, f"{DOMAIN}.fixture_history")
        self.store_data = {"entry_id": self.entry.entry_id, "unique_id": self.entry.unique_id, "history": [{"temperature": 21.5}]}
        await self.store.async_save(self.store_data)
        self.store_path = self.config / ".storage" / f"{DOMAIN}.fixture_history"
        self.store_bytes = self.store_path.read_bytes()
        self.history = self.config / "home-assistant_v2.db"
        with closing(sqlite3.connect(self.history)) as db, db:
            db.execute("CREATE TABLE fixture_history (entry_id TEXT, entity_id TEXT, state TEXT)")
            db.execute("INSERT INTO fixture_history VALUES (?, ?, ?)", (self.entry.entry_id, "climate.fixture_haier", "21.5"))
        self.history_bytes = self.history.read_bytes()

    async def asyncTearDown(self):
        await self.hass.async_block_till_done()
        await self.hass.async_stop(force=True)
        # custom_components is globally mounted by the real HA loader.
        for key in list(sys.modules):
            if key == "custom_components" or key.startswith("custom_components."):
                sys.modules.pop(key)

    async def test_install_update_preserves_identity_and_external_history(self):
        await self.install_fixture("0.3.0")
        original_manifest = (self.target / "manifest.json").read_bytes()
        self.assertEqual((self.target / "climate.py").read_bytes(),
                         (ROOT / "custom_components" / DOMAIN / "climate.py").read_bytes())
        self.assertTrue(self.repo.data.installed)
        self.assertEqual(self.repo.data.installed_version, "fixture-0.3.0")
        (self.target / "obsolete_fixture.txt").write_text("old file must disappear")
        await self.install_fixture("0.3.1")
        self.assertFalse((self.target / "obsolete_fixture.txt").exists())
        self.assertNotEqual((self.target / "manifest.json").read_bytes(), original_manifest)
        self.assertEqual(json.loads((self.target / "manifest.json").read_bytes())["version"], "0.3.1")
        self.assertEqual(self.repo.data.installed_version, "fixture-0.3.1")
        await self.assert_identity_preserved()
        self.assertEqual(self.marketplace.data.content[self.repo.data.id]["version_installed"], "fixture-0.3.1")
        persisted = json.loads((self.config / ".storage/marketplace.repositories").read_text())
        self.assertEqual(persisted["data"][self.repo.data.id]["version_installed"], "fixture-0.3.1")
        self.assertFalse(list((self.config / ".storage/marketplace_backups").iterdir()))

    async def test_invalid_written_manifest_rolls_back_byte_for_byte(self):
        await self.install_fixture("0.3.0")
        for bad, expected in (
            (None, "installed_manifest_unusable"),
            ({"domain": DOMAIN}, "installed_manifest_without_version"),
            ({"domain": DOMAIN, "version": "not a valid version!"}, "installed_manifest_without_version"),
            ({"domain": "different_fixture_domain", "version": "0.3.1"}, "installed_manifest_other_domain"),
        ):
            with self.subTest(expected=expected, bad=bad):
                before = {p.relative_to(self.target): p.read_bytes() for p in self.target.rglob("*") if p.is_file()}
                self.stage_fixture("0.3.1", written_manifest=bad)
                with self.assertRaises(MarketplaceError) as error:
                    await self.repo.async_install_repository()
                self.assertEqual(error.exception.translation_key, expected)
                self.assertEqual({p.relative_to(self.target): p.read_bytes() for p in self.target.rglob("*") if p.is_file()}, before)
                self.assertEqual(self.repo.data.installed_version, "fixture-0.3.0")
                await self.assert_identity_preserved()
                self.assertFalse(list((self.config / ".storage/marketplace_backups").iterdir()))

    async def test_invalid_first_install_leaves_no_partial_directory(self):
        self.stage_fixture("0.3.0", written_manifest={"domain": DOMAIN})
        with self.assertRaises(MarketplaceError) as error:
            await self.repo.async_install_repository()
        self.assertEqual(error.exception.translation_key, "installed_manifest_without_version")
        self.assertFalse(self.target.exists())
        self.assertFalse(self.repo.data.installed)
        await self.assert_identity_preserved()

    async def test_same_domain_owner_refused_before_content_or_backup_changes(self):
        await self.install_fixture("0.3.0")
        contender = IntegrationRepository(self.marketplace, "local-test-fixture/same-domain-fork")
        contender.data.id = "local-collision-fixture"
        contender.data.domain = DOMAIN
        self.marketplace.repositories.register(contender, default=True)
        self.stage_fixture("0.3.1", repository=contender)
        before = {p.relative_to(self.target): (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns) for p in self.target.rglob("*") if p.is_file()}
        backup_before = list((self.config / ".storage/marketplace_backups").iterdir())
        with self.assertRaises(MarketplaceError) as error:
            await contender.async_install_repository()
        self.assertEqual(error.exception.translation_key, "integration_owned")
        self.assertEqual({p.relative_to(self.target): (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns) for p in self.target.rglob("*") if p.is_file()}, before)
        self.assertEqual(list((self.config / ".storage/marketplace_backups").iterdir()), backup_before)
        self.assertFalse(contender.data.installed)
        self.assertIs(self.marketplace.repositories.list_installed[0], self.repo)
        await self.assert_identity_preserved()

    async def test_changed_domain_refused_before_file_replacement(self):
        await self.install_fixture("0.3.0")
        before = (self.target / "manifest.json").read_bytes()
        self.stage_fixture("0.3.1", remote_domain="different_fixture_domain")
        with self.assertRaises(MarketplaceError) as error:
            await self.repo.async_install_repository()
        self.assertEqual(error.exception.translation_key, "domain_changed")
        self.assertEqual((self.target / "manifest.json").read_bytes(), before)
        self.assertFalse((self.target.parent / "different_fixture_domain").exists())
        await self.assert_identity_preserved()

    async def install_fixture(self, version):
        self.stage_fixture(version)
        await self.repo.async_install_repository()

    def stage_fixture(self, version, *, repository=None, written_manifest="valid", remote_domain=DOMAIN):
        repo = repository or self.repo
        ref = f"fixture-{version}"
        repo.data.last_version = ref
        repo.data.last_commit = None
        remote_manifest = json.loads(self.source_files[f"custom_components/{DOMAIN}/manifest.json"])
        remote_manifest.update(domain=remote_domain, version=version)
        files = dict(self.source_files)
        manifest_key = f"custom_components/{DOMAIN}/manifest.json"
        if written_manifest is None:
            files.pop(manifest_key)
        else:
            files[manifest_key] = json.dumps(remote_manifest if written_manifest == "valid" else written_manifest).encode()
        # One top-level directory, exactly as RepositoryArchive expects.
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as candidate:
            for name, content in files.items():
                candidate.writestr(f"local-candidate-fixture/{name}", content)
        self.delivery.payloads.update({
            f"{repo.data.full_name}/{ref}/hacs.json": (ROOT / "hacs.json").read_bytes(),
            f"{repo.data.full_name}/{ref}/{manifest_key}": json.dumps(remote_manifest).encode(),
            f"{repo.data.full_name}/archive/refs/tags/{ref}.zip": archive.getvalue(),
        })

    async def assert_identity_preserved(self):
        self.assertIs(self.hass.config_entries.async_get_entry(self.entry.entry_id), self.entry)
        self.assertEqual(self.entry.unique_id, "fixture-device-identity")
        self.assertEqual(dict(self.entry.data), {"host": "192.0.2.2"})
        self.assertEqual(self.entries_path.read_bytes(), self.entries_bytes)
        saved_entries = (await self.hass.config_entries._store.async_load())["entries"]
        self.assertEqual(saved_entries[0]["entry_id"], self.entry.entry_id)
        self.assertEqual(saved_entries[0]["unique_id"], self.entry.unique_id)
        self.assertEqual(self.store_path.read_bytes(), self.store_bytes)
        self.assertEqual(await Store(self.hass, 1, f"{DOMAIN}.fixture_history").async_load(), self.store_data)
        self.assertEqual(self.history.read_bytes(), self.history_bytes)
        with closing(sqlite3.connect(self.history)) as db, db:
            self.assertEqual(db.execute("SELECT * FROM fixture_history").fetchall(), [(self.entry.entry_id, "climate.fixture_haier", "21.5")])


if __name__ == "__main__":
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    unittest.main(verbosity=2)
