# Changelog

## Unreleased development

- Review European Portuguese entity labels and options, using clearer terms such as indoor/outdoor heat exchanger, remote-control lock, self-clean and night mode.
- Keep Health as a function name without inventing purification or health claims; retain uncertainty about probes and raw values.
- Clarify RF-008: improving default labels is allowed, while existing identifiers and user-chosen names must be preserved.
- Add text regressions and real Home Assistant naming/registry checks to both pinned framework versions.

The published version remains [0.3.0](https://github.com/ringone/haier-smartair2-cloud-for-homeassistant/releases/tag/0.3.0), released on 2026-11-17. These translation changes are not part of that tag and do not publish a new release.

## Historical 0.3.0 candidate preparation

The following preparation notes are retained from the pre-publication development snapshot; their unpublished status describes that earlier phase, not the current GitHub release.

The local-only and Marketplace/2026.11 changes are prepared for review. There is no published 0.3.0 release or catalogue submission.

### Changes affecting existing installations

- Require Home Assistant >=2026.11.0 and Python >=3.14.2. The old 2024.11 minimum was not verified and no longer applies to this candidate.
- Remove Haier cloud authentication, discovery, MQTT and fallback. Devices must have compatible plaintext SmartAir2 LAN support and explicit MAC:IPv4 mappings.
- Migrate existing entries in place to config version 2, retaining the domain, MAC-based identities and packet-history key while removing active cloud credentials. Keep the existing entry and make a full configuration backup before upgrading.
- Adopt the native climate-temperature API and test Celsius/Fahrenheit state and service conversion.

### Verification and documentation

- Add Marketplace metadata gates and real-framework install/update/rollback and domain-collision tests with local delivery fixtures.
- Test Home Assistant 2026.11.0 and 2026.11.1 separately in CI.
- Retain the initial audit, historical bug tests, SDLC, requirements, traceability and source-specific verification receipts.
- Reorganize the README and separate installation/rollback details from protocol and development documentation.

Transport, codecs and local history remain as in the local-only implementation. Physical validation and repository handover are still pending. RP-002 (concurrent command overwrites) and RP-003 (combined temperature/HVAC-mode handling) remain open; this candidate does not fix them.

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
