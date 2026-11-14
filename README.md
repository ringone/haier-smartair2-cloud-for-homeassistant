# Haier SmartAir2 Local for Home Assistant

Local-only fork of [bwitosze/haier-smartair2-cloud-for-homeassistant](https://github.com/bwitosze/haier-smartair2-cloud-for-homeassistant) for legacy Haier air conditioners with a **plaintext SmartAir2 LAN dongle**, not hOn.

**Version 0.3.0 removes the Haier cloud transport completely.** Setup, startup and control do not require a Haier account or Internet connection. Devices must be listed explicitly as `MAC:IP` pairs. There is no cloud discovery or fallback.

The integration domain remains `haier_smartair2`. Existing MAC-based entity identifiers, device registrations and local packet history are retained when migrating an existing entry. **Do not delete the existing entry to upgrade.**

## Compatibility warning — hardware coverage is unknown

> **The only specifically documented hardware combination in this fork is Haier AS35TADHRA-TH + MK-QTWIFI-04(B), based on recorded captures and prior calibration. We do not know whether this implementation is valid for other air conditioners, Wi-Fi modules or firmware revisions. Even the local-only 0.3.0 build has not been physically tested on that documented combination.**
>
> The current 24-byte → V2 / 32-byte → V3 selection is a **heuristic for the known captures, not a universal protocol identifier**. Different layouts can have the same length. Passing checksum/CRC or automated tests does not prove that controls are safe or correctly mapped on another device.
>
> Other hardware is **unverified/experimental**, not declared supported. The retained V2 codec is not evidence of tested V2 LAN hardware. Encrypted/cloud-only modules remain unsupported. See [compatibility evidence and limits](docs/compatibility.md).

## Documented hardware and implemented functions

This fork was calibrated on a Haier **AS35TADHRA-TH** with an **MK-QTWIFI-04(B)** dongle, speaking SmartAir2 V3 over **TCP 56800**. These observations must not be generalized to other dongles.

- **V3 implementation:** climate controls, Power and Sleep presets, quiet fan mode, Health, panel light, self-clean, remote lock, electric heat, vertical vane positions, extended telemetry and alarm diagnostics, based on the documented AS35 layout only.
- **V2 implementation retained, LAN hardware unverified:** the existing V2 codec and basic controls remain in the code. This is not a claim of compatibility with any additional model or Wi-Fi module.
- **Encrypted/cloud-only dongles are not supported.** A formerly cloud-controlled device needs plaintext LAN support and a local mapping, which alone does not establish protocol compatibility.
- Unrecognised status lengths are rejected. An incompatible layout with a recognised length is not ruled out by the current heuristic.

Reserve each dongle's IP address in your router. Home Assistant must reach it on TCP 56800. Close the SmartAir2 phone app: it can occupy the dongle's only local session.

The existing local wire commands, polling, frame validation, reconnects, telemetry conversions and packet history are retained. Quiet is a separate V3 flag; the calibrated firmware returns the fan to auto when quiet is selected. Self-clean does not start in heat, auto or sleep. Horizontal airflow on the AS35 is manual.

## Installation

**Candidate status:** 0.3.0 is an **unpublished** branch candidate; the stable release is 0.2.3. Marketplace catalog submission and a 0.3.0 release are pending. Adding the repository does not publish or automatically install this candidate. Do not assume the latest stable download contains these changes.

**Supported baseline:** Home Assistant **2026.11.0 or newer**, Python >=3.14.2. The verification matrix exercises 2026.11.0 and 2026.11.1; future releases still need verification. This minimum is intentionally raised for the native climate-temperature API; the old 2024.11 support claim no longer applies to this candidate.

<!-- ha-marketplace:exclude-start -->
### Marketplace (Home Assistant 2026.11 or newer; release pending)

1. Once a reviewed release is available, use **Settings → Marketplace → Add from link** with `https://github.com/ringone/haier-smartair2-cloud-for-homeassistant`.
2. Install Haier SmartAir2, then add it under **Settings → Devices & services**. A first install using its config flow normally does not require a restart.
3. For updates, removal, or replacement of already loaded integration code, restart Home Assistant before relying on the new code.

GitHub/Internet access may be needed to download updates. That is separate from the integration runtime, which uses no Haier cloud connection.

### HACS (Home Assistant before 2026.11; older releases only)

1. HACS → three-dot menu → **Custom repositories**.
2. Add `https://github.com/ringone/haier-smartair2-cloud-for-homeassistant`, category **Integration**.
3. Install an appropriate published release and follow HACS restart instructions. HACS use before 2026.11 does not make this candidate compatible with older Home Assistant versions.

Home Assistant 2026.11 migrates existing HACS installations to its built-in Marketplace. That automatic migration is different from changing the repository that owns an installed domain, such as switching from upstream to this fork. Same-domain repository ownership **handover is blocked pending manual validation**: do not install both repositories, uninstall as a workaround, or delete the config entry. Make a full backup, preserve the existing config entry and packet history, and keep rollback files before any change. See [Marketplace verification and pending gates](docs/marketplace.md).
<!-- ha-marketplace:exclude-end -->

### Manual

Back up the complete Home Assistant configuration, including private `.storage` data, and the existing integration directory. Replace `config/custom_components/haier_smartair2/` with this version. Replace the whole directory rather than copying over it, so the removed `cloud.py` is not left behind. Restart Home Assistant. Keep the existing integration entry under **Settings → Devices & services**. Rollback may require restoring both the old code and its configuration backup, not just copying back Python files.

## Configuration

Go to **Settings → Devices & services → Add integration → Haier SmartAir2**. Supply comma-separated `MAC:IPv4` pairs:

```text
00:11:22:33:44:55:192.168.1.50, AABBCCDDEEFF:192.168.1.51
```

MAC addresses with or without colons are accepted. Blank or malformed mappings are rejected. IPv6 and hostname mappings are not supported by this format.

Use **Configure** to change addresses or add devices later. There are no e-mail, password, region or cloud client-ID fields. Configuration does not contact devices or the Haier API. Runtime connects only to the mapped devices. An unreachable device or unsupported status causes an explicit setup failure/retry, never a switch to cloud.

### Upgrading an existing entry

Entries migrate in place to config version 2. Options override the original local map. Cloud credentials and connection settings are removed. Domain, entry ID, MAC-based entity identifiers and packet history are retained.

- For devices already working locally, keep the existing entry and local map.
- Devices previously discovered only through the Haier account are no longer discovered. Add their mappings if they support plaintext LAN.
- An entry without a usable map cannot start. Open **Configure**, supply the map and reload. Do not delete the entry: deletion also removes its packet history.

Changing an IP does not change MAC-based unique IDs. Existing device names are reused where available; new devices receive stable local names.

## Local diagnostics

Compatible V3 units expose compressor, indoor fan, defrost and active-alarm diagnostics. Outdoor fan, four-way valve and actual heater state remain disabled by default where useful readings are unconfirmed. Alarm state is unknown until a report arrives and resets after disconnect.

**Download diagnostics** exports recent local frames. History is kept on the Home Assistant host for up to seven days or 20,000 records per entry. Known telemetry is exported with timestamps and anonymous device numbers. Unknown or invalid payloads stay only in the private local store and are exported as metadata.

See [AS35 protocol notes](docs/protocol-as35.md) for byte layouts, conversions and their limits. The private history store contains device identifiers and raw frames; treat it as local diagnostic data.

## Limitations and verification

- Plaintext SmartAir2 LAN only; not hOn or cloud-only/encrypted dongles.
- Sensor and actuator support depends on the device layout.
- Two recorded AS35 captures reported 0 W and unavailable compressor current. The valve field reported 88 raw units; its physical scale is unverified.
- The timer is not exposed. Horizontal airflow on this AS35 is manual.
- This release removes cloud dependencies; it does not claim to fix unrelated command races or all existing climate-service behavior.
- Automated tests do not replace validation against your physical air conditioner. Keep a backup for rollback.

## Requirements and acceptance

The [draft requirements specification](docs/requisitos.md) and [traceability matrix](docs/matriz-requisitos.csv) distinguish implemented behavior, verification gaps, physical tests and proposed fixes. The specification is in Portuguese and is a proposal for review, not a statement that all requirements are satisfied or that additional hardware is supported.

The [SDLC record](docs/sdlc.md), [architecture decision](docs/adr/0001-local-only.md) and [initial audit](docs/auditoria-inicial.md) preserve the reasoning, original probe evidence and repeatable historical cloud tests. Historical audit tests deliberately reproduce the old defects; green historical tests do not mean the remaining local control bugs were fixed.

## Development checks

```sh
python -m compileall -q custom_components
python -m unittest discover -s tests -v
python tests/check_requirements.py
python tests/check_marketplace.py
```

The historical audit needs Git commit `5b77363a05225311fb85ef89eb16136b26440acd`; use a full clone or fetch the baseline. The CI unit-test checkout uses `fetch-depth: 0` rather than silently skipping those tests.

With Home Assistant 2026.11.0 installed in a separate environment, also run:

```sh
python tests/ha_localonly_smoke.py
python tests/ha_climate_compat.py
python tests/ha_marketplace_smoke.py
```

The lightweight tests use Home Assistant doubles. Framework-level checks must run in a separate process with Home Assistant installed, so doubles cannot hide import or setup errors.

## Changelog

- **0.3.0 (unpublished)** — local-only configuration, startup and migration; remove cloud authentication, discovery, MQTT and fallback; preserve LAN protocol, MAC entity IDs and packet history. Require Home Assistant 2026.11.0, use the native climate-temperature API and add Marketplace distribution checks.
- **0.2.3** — V3 actuator states, alarm bits and bounded local packet history with diagnostic export.
- **0.2.2** — local reconnects and frame integrity validation.
- **0.2.1** — colon-separated MAC support, restore fixed vane position and self-clean guards.
- **0.2.0** — V3 controls and telemetry, Portuguese translations and Marketplace metadata.
- **0.1.4 and earlier** — upstream hybrid cloud/local integration.

## Credits and license

Original integration by [bwitosze](https://github.com/bwitosze/haier-smartair2-cloud-for-homeassistant). Protocol work builds on Piotr Stadnicki ([fastfend](https://github.com/fastfend)), [ESPHome Haier](https://esphome.io/components/climate/haier/) and `paveldn/HaierProtocol`.

This is unofficial, not affiliated with or supported by Haier. Use at your own risk. [MIT license](LICENSE).
