# Changelog

## Unreleased documentation

- Rewrite the `main` README for users: installation, configuration, controls, recovery and known limitations.
- Preserve the previous technical README and source snapshot on `develop`.
- Align current documentation and static checks with the published 0.3.0 release. These documentation changes do not replace or retag that release.

## [0.3.0](https://github.com/ringone/haier-smartair2-cloud-for-homeassistant/releases/tag/0.3.0) — 2026-11-17

Published from merged PR #4, commit `bd4d653254d5d4ce364c9fb7232395d7f8e9275d`. Public catalogue inclusion is not confirmed. Historical verification records retain their pre-publication context.

### Changes affecting existing installations

- Require Home Assistant >=2026.11.0 and Python >=3.14.2. The old 2024.11 minimum was not verified and no longer applies to 0.3.0.
- Remove Haier cloud authentication, discovery, MQTT and fallback. Devices must have compatible plaintext SmartAir2 LAN support and explicit MAC:IPv4 mappings.
- Migrate existing entries in place to config version 2, retaining the domain, MAC-based identities and packet-history key while removing active cloud credentials. Keep the existing entry and make a full configuration backup before upgrading.
- Adopt the native climate-temperature API and test Celsius/Fahrenheit state and service conversion.

### Verification and documentation

- Add Marketplace metadata gates and real-framework install/update/rollback and domain-collision tests with local delivery fixtures.
- Test Home Assistant 2026.11.0 and 2026.11.1 separately in CI.
- Retain the initial audit, historical bug tests, SDLC, requirements, traceability and source-specific verification receipts.
- Reorganize the README and separate installation/rollback details from protocol and development documentation.

Transport, codecs and local history remain as in the local-only implementation. Physical validation and repository handover are still pending. RP-002 (concurrent command overwrites) and RP-003 (combined temperature/HVAC-mode handling) remain open; 0.3.0 does not fix them.

## 0.2.3

V3 actuator states, alarm bits and bounded local packet history with diagnostic export.

## 0.2.2

Local reconnects and frame integrity validation.

## 0.2.1

Colon-separated MAC support, fixed vane-position restore and self-clean guards.

## 0.2.0

V3 controls and telemetry, Portuguese translations and Marketplace metadata.

## 0.1.4 and earlier

Upstream hybrid cloud/local integration.
