"""Negative fixtures for offline Marketplace project policy (no product imports)."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketplaceMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / "custom_components", self.root / "custom_components")
        for name in ("hacs.json", "README.md"):
            shutil.copy(ROOT / name, self.root / name)
        # Build a known-valid localization fixture; repository parity is checked by CLI.
        translations = self.root / "custom_components/haier_smartair2/translations"
        shutil.copy(translations / "en.json", translations / "pl.json")

    def check(self):
        path = ROOT / "tests/check_marketplace.py"
        self.assertTrue(path.exists(), "static checker is missing")
        spec = importlib.util.spec_from_file_location("marketplace_checker", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.validate(self.root)

    def edit_json(self, relative, change):
        path = self.root / relative
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data))

    def test_root_metadata_contract(self):
        self.assertEqual(self.check(), [])
        for change in (lambda d: d.pop("name"), lambda d: d.update(homeassistant="2024.11.0")):
            with self.subTest(change=change):
                shutil.copy(ROOT / "hacs.json", self.root / "hacs.json")
                self.edit_json("hacs.json", change)
                self.assertTrue(any("hacs" in e for e in self.check()))

    def test_manifest_and_single_domain_contract(self):
        manifest = "custom_components/haier_smartair2/manifest.json"
        mutations = [lambda d: d.update(domain="wrong"), lambda d: d.pop("version"),
                     lambda d: d.update(version="9.9.9"), lambda d: d.update(config_flow=False),
                     lambda d: d.update(documentation="not-a-url"), lambda d: d.update(issue_tracker="file:///tmp/issues"),
                     lambda d: d.update(categories=[]), lambda d: d.update(codeowners=[]),
                     lambda d: d.update(iot_class="bad"), lambda d: d.update(name="Wrong")]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                shutil.copy(ROOT / manifest, self.root / manifest)
                self.edit_json(manifest, mutation)
                self.assertTrue(any("manifest" in e for e in self.check()))
        shutil.copy(ROOT / manifest, self.root / manifest)
        (self.root / "custom_components/extra").mkdir()
        self.assertTrue(any("integration" in e for e in self.check()))

    def test_malformed_manifest_is_reported(self):
        path = self.root / "custom_components/haier_smartair2/manifest.json"
        for value in ("{", "[]", "null"):
            with self.subTest(value=value):
                path.write_text(value)
                self.assertTrue(any("manifest" in e for e in self.check()))

    def test_domain_slug_is_validated_not_just_equal_to_folder(self):
        integration = self.root / "custom_components/haier_smartair2"
        renamed = integration.with_name("INVALID")
        integration.rename(renamed)
        self.edit_json("custom_components/INVALID/manifest.json", lambda d: d.update(domain="INVALID"))
        constants = renamed / "const.py"
        constants.write_text(constants.read_text().replace("haier_smartair2", "INVALID"))
        self.assertTrue(any("domain" in e for e in self.check()))

    def test_translations_and_brand_contract(self):
        base = "custom_components/haier_smartair2/"
        for language in ("en", "pt", "pl"):
            relative = base + f"translations/{language}.json"
            with self.subTest(language=language):
                self.edit_json(relative, lambda d: d["config"]["step"]["user"].pop("title"))
                self.assertTrue(any("translations" in e for e in self.check()))
                shutil.copy(ROOT / relative, self.root / relative)
        for filename in ("icon.png", "icon@2x.png"):
            path = self.root / base / "brand" / filename
            original = path.read_bytes()
            for broken in (b"not PNG", original[:16] + b"\0\0\0\1" + original[20:]):
                with self.subTest(filename=filename, broken=broken[:24]):
                    path.write_bytes(broken)
                    self.assertTrue(any("brand" in e for e in self.check()))
            path.write_bytes(original)

    def test_explicit_step_id_contract(self):
        base = self.root / "custom_components/haier_smartair2"
        flow = base / "config_flow.py"
        flow.write_text(flow.read_text().replace('step_id="user",', ''))
        self.assertTrue(any("step_id" in e for e in self.check()))

    def test_native_climate_contract(self):
        climate = self.root / "custom_components/haier_smartair2/climate.py"
        climate.write_text(climate.read_text().replace("native_current_temperature", "current_temperature"))
        self.assertTrue(any("climate" in e for e in self.check()))

    def test_readme_contract(self):
        readme = self.root / "README.md"
        readme.write_text("# Haier 0.3.0")
        self.assertTrue(any("README" in e for e in self.check()))

    def test_official_readme_marker_names(self):
        readme = self.root / "README.md"
        content = readme.read_text().replace("<!-- marketplace:", "<!-- ha-marketplace:")
        readme.write_text(content)
        self.assertEqual(self.check(), [])
        readme.write_text(content.replace("<!-- ha-marketplace:", "<!-- marketplace:"))
        self.assertTrue(any("README" in e for e in self.check()))

    def test_partial_entity_locale_uses_complete_english_fallback(self):
        self.edit_json("custom_components/haier_smartair2/translations/pl.json",
                       lambda d: d["entity"]["sensor"].pop("room_temperature"))
        self.assertEqual(self.check(), [])

    def test_progress_done_and_external_flow_contract(self):
        flow = self.root / "custom_components/haier_smartair2/config_flow.py"
        original = flow.read_text()
        flow.write_text(original + '\ndef fixture_next(flow):\n    return flow.async_show_progress_done(next_step_id="finish")\n')
        self.assertEqual(self.check(), [])
        flow.write_text(original + '\ndef fixture_external(flow):\n    return flow.async_external_step(url="https://example.invalid")\n')
        self.assertTrue(any("step_id" in e for e in self.check()))

    def test_missing_files_and_malformed_metadata_do_not_crash(self):
        for relative in ("README.md", "hacs.json", "custom_components/haier_smartair2/config_flow.py"):
            with self.subTest(relative=relative):
                path = self.root / relative
                data = path.read_bytes()
                path.unlink()
                self.assertTrue(self.check())
                path.write_bytes(data)
        manifest = "custom_components/haier_smartair2/manifest.json"
        self.edit_json(manifest, lambda d: d.update(documentation="https://[broken"))
        self.assertTrue(any("manifest" in e for e in self.check()))


if __name__ == "__main__":
    unittest.main()
