# Documentation

The `main` [README](../README.md) is for installation and everyday use. The [`develop` branch](https://github.com/ringone/haier-smartair2-cloud-for-homeassistant/tree/develop) preserves the earlier technical README and source snapshot. Detailed references and tests remain in the repository; separating the README audiences does not remove verification from `main`. When bringing development changes back to `main`, retain its user-facing README.

## Install and use the integration

- [Installation, migration and rollback](installation.md): prerequisites, Marketplace/manual procedures, recovery of existing entries and repository-ownership limits.
- [Compatibility and evidence](compatibility.md): documented AC/module combination, firmware uncertainty, V2/V3 heuristic and unsupported modules.
- [AS35 protocol notes](protocol-as35.md): captures, controls, telemetry conversions and fields with unknown physical meaning.
- [Version history](../CHANGELOG.md): published releases and later documentation changes. Version 0.3.0 was published on 2026-11-17; publishing does not resolve the known control or hardware-validation gaps.

## Requirements, decisions and verification

- [Requirements](requisitos.md) and [traceability matrix](matriz-requisitos.csv): measurable criteria, implementation state, evidence and remaining gaps. The specification is in Portuguese. A requirement listed here is not automatically approved or fully satisfied.
- [SDLC record](sdlc.md): development, review, testing and release gates.
- [ADR-001: local-only](adr/0001-local-only.md) and [ADR-002: Marketplace/2026.11](adr/0002-marketplace-202611.md): scope and compatibility decisions.
- [Initial audit](auditoria-inicial.md): retained cloud/local findings and the meaning of the historical defect tests.
- [Marketplace verification](marketplace.md): static policy gates, real-framework transaction tests and boundaries of local delivery fixtures.

The evidence is split by the increment it actually tested:

- [Local-only verification](evidence/verification-local.json) and [review](evidence/review-final.json) describe that earlier source snapshot.
- [Marketplace verification](evidence/verification-marketplace.json) and [review](evidence/review-marketplace.json) describe the subsequent compatibility increment.
- The consolidated PR for `main` carries its own verification receipt and live CI checks. An older receipt does not certify a newer commit merely because the runtime code is unchanged.

Physical hardware validation, live Marketplace UI/downloads, upstream-to-fork repository handover and operational backup/restore remain separate acceptance work. RP-002/RP-003 remain known defects, not successful acceptance tests.

## Run the checks

Use Python compatible with the Home Assistant version under test. The CI workflow pins Python 3.14 and Home Assistant 2026.11.0/2026.11.1. It is a tested matrix, not a claim about future versions.

From the repository root, run the lightweight checks:

```sh
python -m compileall -q custom_components tests
python -m unittest discover -s tests -v
python tests/check_requirements.py
python tests/check_marketplace.py
ruff check --select F custom_components tests
```

The historical audit needs Git commit `5b77363a05225311fb85ef89eb16136b26440acd`. Use a full clone or fetch that commit; the unit-test CI checkout uses `fetch-depth: 0`. Historical tests pass when they reproduce the original bugs. They do not prove those bugs are fixed in the current integration.

In an isolated environment with actual Home Assistant installed, run each framework harness as a separate process:

```sh
python -B -W error::ResourceWarning tests/ha_localonly_smoke.py
python -B -W error::ResourceWarning tests/ha_climate_compat.py
python -B -W error::ResourceWarning tests/ha_marketplace_smoke.py
python -m pip check
```

Do not import the stub-based unit suite and then run framework checks in the same interpreter. The unit suite replaces Home Assistant modules; separate processes prevent those doubles from hiding integration failures.

The LAN smoke uses a loopback AC simulator and replaces platform forwarding/unload. Climate tests register an entity and dispatch services through real Home Assistant, but use a fixture coordinator. Marketplace tests run real installation/update/backup/rollback code with local delivery fixtures, not GitHub releases or a live recorder. Standard custom-integration warnings remain visible.

Before pushing, inspect the staged candidate with `git diff --cached HEAD --check`, review the diff and run the checks for the exact content being delivered. HACS/hassfest success does not constitute a security endorsement or catalogue acceptance.
