# Marketplace verification and release boundaries

## Status and support policy

0.3.0 is an unpublished candidate on `chore/marketplace-ha-2026.11`; stable remains 0.2.3. No release, merge, catalog submission or repository-manager handover is authorized by this work. The Home Assistant minimum is intentionally raised to **2026.11.0**, Python **3.14** (Home Assistant package currently requires >=3.14.2). Older HACS installation routes are not a compatibility promise for this candidate.

## Sources checked on 2026-11-14

Authoritative contributor documentation (retrieved with Python requests):

- https://contributors.home-assistant.io/marketplace/guides/integrations/
- https://contributors.home-assistant.io/marketplace/reference/validation/
- https://contributors.home-assistant.io/marketplace/guides/catalog/
- https://contributors.home-assistant.io/marketplace/guides/releases/
- https://contributors.home-assistant.io/marketplace/reference/hacs-json/
- Native climate migration: https://contributors.home-assistant.io/blog/2026/10/08/climate-native-temperature/

Independently retrieved official PyPI JSON, https://pypi.org/pypi/homeassistant/json, at **2026-11-14T00:09:23Z**: newest non-yanked stable `2026.11.x` is **2026.11.1**, wheel uploaded **2026-11-09T19:09:35.980313Z**, requires Python **>=3.14.2**. CI pins minimum 2026.11.0 and this patch version; it is not a rolling latest claim. Recheck metadata before updating the matrix.

## Repeatable local gates

```sh
python -m unittest discover -s tests -p 'test_marketplace_metadata.py' -v
python tests/check_marketplace.py
```

The checker uses only Python stdlib AST, JSON, struct and paths; it never imports or executes integration modules and makes no network requests. Negative temporary fixtures cover root metadata/minimum, one integration and domain/manifest coherence, malformed manifests, metadata URLs, candidate version, config flow, translations, PNG dimensions, explicit flow step IDs, native climate names, and README installation/release messaging.

These are **project policy gates**, not a reimplementation of every Marketplace installer rule. This project checks English fallback text, localized flow text in en/pt/pl, 256/512 local PNG icon headers/dimensions, HTTPS metadata, a local-push hub with no pip requirements, explicit flow step IDs, and the native temperature API. Partial entity translations (including Polish) are retained and may fall back to English; strict pt/pl equality is not a platform requirement and is not imposed. English fallback completeness for dynamic runtime use still requires framework/hassfest and rendered-UI review. Categories are optional platform-wide (missing categories produce a warning); this project retains its known climate category. The optional README markers use the official `ha-marketplace:exclude-start` / `ha-marketplace:exclude-end` names. Brand images have been supported since Home Assistant 2026.3. Explicit step IDs become mandatory for custom integrations in 2027.5; the climate native-temperature deadline is 2027.11. Bool config-entry setup/unload returns remain explicitly supported; no None-return gate is imposed.

A JSON-decodable manifest plus static AST is not proof that Home Assistant can load it. The separate real-framework scripts are:

```sh
python tests/ha_localonly_smoke.py
python tests/ha_climate_compat.py
python tests/ha_marketplace_smoke.py
```

Run each in a fresh process with actual Home Assistant installed, never following stub-based discovery in the same interpreter. CI invokes them separately for both pinned versions. The static fixture suite constructs valid localization fixtures, so run the checker CLI against the actual repository too: green negative fixtures alone do not prove the repository passes.

## Transaction harness: what is actually exercised

`ha_marketplace_smoke.py` calls real `IntegrationRepository.async_install_repository()` with the **current candidate files**, actual Home Assistant loader discovery, ZIP extraction, backup/restore, post-write manifest validation and Marketplace Store persistence. Only delivery is replaced with fail-closed local ZIP/raw-file fixtures and an inert HTTP session. Fixture refs/manifest versions are deliberately synthetic; they are not real published releases. Socket and DNS access are denied.

Cases cover install/update, removal of obsolete files, four invalid-written-manifest rollback variants, cleanup of a failed first install, same-domain ownership refusal before files/backups change, and refusal of a changed domain. A real ConfigEntry object and serialized entry Store remain unchanged; external HA Store and SQLite history **fixtures** retain their bytes/identity. No live recorder or device setup is involved. Installed core source hashes are checked unchanged. Separate helper cases prove the network guard and delivery mapping fail closed.

The climate harness registers a real HA entity attached to a ConfigEntry, writes real states and dispatches real climate services, while replacing the device coordinator. It checks Celsius/Fahrenheit conversion, missing readings, bounds, identity and absence of the deprecated-temperature import warnings. This is not a physical control test.

## What remains pending

- Require official HACS validation and hassfest to pass for the exact release candidate SHA; read the live CI checks instead of treating a local checker as an official validation pass. Catalog review is a separate gate.
- Verify Add from link, download/extraction, first config-flow install without restart, update/replacement restart repairs, removal, rollback and rendered translations/branding in a live Home Assistant UI.
- Verify same-domain ownership transfer between upstream and fork repositories. This is **blocked**, not a documented safe uninstall path. Preserve the existing config entry, entity IDs and packet history; make a full backup first. Do not delete an entry to transfer repositories. This is distinct from Home Assistant's automatic HACS-to-Marketplace migration.
- Review catalog identity, uniqueness, topics/issues, licensing, release assets, public repository/release visibility and upstream ownership concerns.
- Tag/version/release coherence and actual published 0.3.0 artifacts; a manifest version or candidate branch is not a release. No publishing happens in this gate.
- Physical-device validation, non-AS35 hardware coverage and real Internet-isolated installation/runtime observations. Framework harnesses with synthetic packets cannot certify physical safety, dongle compatibility, online Marketplace behavior or catalog acceptance.

First config-flow installs normally load immediately. Updates, removal and replacement of already loaded code require a restart. Download access to GitHub is separate from the integration's offline LAN runtime.
