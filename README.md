# Haier SmartAir2 Local for Home Assistant

Control legacy Haier air conditioners directly over your LAN, without a Haier account, MQTT or cloud fallback. This unofficial fork uses plaintext SmartAir2 Wi-Fi modules; it does not support hOn or encrypted/cloud-only modules.

**Status:** 0.3.0 is an **unpublished** candidate. The latest published release, 0.2.3, does not contain this local-only rewrite. Merging this code or adding the repository to Marketplace does not publish a new release.

## Compatibility and requirements

The only documented hardware combination is **Haier AS35TADHRA-TH + MK-QTWIFI-04(B)**, based on earlier captures and calibration. **The 0.3.0 candidate has not been tested on a physical air conditioner.** Compatibility with other models, Wi-Fi modules and firmware is unknown.

- Home Assistant **2026.11.0 or newer**, with Python >=3.14.2. Automated framework checks cover 2026.11.0 and 2026.11.1; later versions need their own verification. The previous, unverified 2024.11 minimum no longer applies to this candidate.
- A plaintext SmartAir2 module reachable from Home Assistant on **TCP 56800**, with a fixed IPv4 address or DHCP reservation. Close the SmartAir2 phone app if it occupies the module's only local session.
- A trusted local network. Do not expose TCP 56800 directly to the Internet: removing the cloud does not add encryption or authentication to the LAN protocol.

The 24-byte → V2 / 32-byte → V3 selection is a heuristic for known captures, not a universal protocol identifier. A valid checksum or matching length does not establish compatibility. The retained V2 codec has no verified LAN hardware coverage. Read the [compatibility notes](docs/compatibility.md) before using another device.

## Installation and upgrades

**Keep your existing integration entry.** The domain remains `haier_smartair2`; migration preserves the entry, MAC-based entity IDs and packet history, while removing active cloud credentials. An entry without a local mapping cannot start until you supply one in **Configure**.

Repository **handover** is separate from upgrading an entry. Marketplace refuses two installed repositories that own the same domain. If you already use the upstream repository, do not delete your entry or uninstall files as a workaround; the handover to this fork still needs manual validation. Home Assistant's automatic HACS-to-Marketplace migration does not change which repository owns the integration.

Before updating, make a full **backup** of Home Assistant's configuration, including private `.storage` data, and the integration files. Rollback may require restoring both the matching configuration and code. Follow the [installation and rollback guide](docs/installation.md); this warning also applies to Marketplace updates.

<!-- ha-marketplace:exclude-start -->
Once a reviewed release is published, add `https://github.com/ringone/haier-smartair2-cloud-for-homeassistant` under **Settings → Marketplace → Add from link**, then install Haier SmartAir2. A first installation with a config flow normally does not require a restart. After updating or replacing code that Home Assistant has already loaded, restart Home Assistant.

To test this unpublished candidate manually after making that backup, replace the entire `config/custom_components/haier_smartair2/` directory with the candidate's directory, then restart Home Assistant. Do not copy over the old files: that could leave the removed `cloud.py` behind.

HACS on Home Assistant versions older than 2026.11 can install appropriate older releases, not this candidate. Use the built-in Marketplace on 2026.11 and later. Downloads and updates need GitHub access; the integration's runtime only connects to the configured LAN devices.

See the [installation, migration and rollback guide](docs/installation.md) for the full procedure.
<!-- ha-marketplace:exclude-end -->

## Configuration

Open **Settings → Devices & services → Add integration → Haier SmartAir2**. Enter comma-separated `MAC:IPv4` pairs:

```text
00:11:22:33:44:55:192.168.1.50, AABBCCDDEEFF:192.168.1.51
```

MAC addresses may include colons. The complete map must be valid and nonempty, with no duplicate MACs or IPs. Hostnames and IPv6 are not supported. There is no account login, cloud discovery or network request during configuration.

Use **Configure** to change IPs or add devices. Options replace the previous local mapping; changing an IP does not change the device's MAC-based identity. An unreachable device or unsupported status causes a local setup failure/retry, never a cloud fallback. [Recovery and migration details](docs/installation.md#upgrade-an-existing-entry).

## Controls and diagnostics

For the documented V3 layout, the implementation provides climate modes and target temperature, fan speeds including quiet, Power/boost and Sleep presets, vertical vane positions, Health, panel light, self-clean, remote lock and electric-heat requests. Self-clean is blocked in heat, auto or sleep. Horizontal airflow on the AS35 is manual; the timer is not exposed.

Telemetry includes temperatures, frequency, actuator flags and alarm diagnostics where the layout is known. Unconfirmed readings remain unknown or disabled by default. In the reference captures, 0 W is not proof of zero consumption, and the expansion-valve value remains a raw value with no verified physical scale. See the [AS35 protocol notes](docs/protocol-as35.md) for mappings and firmware behaviour.

**Download diagnostics** exports recent local frames with anonymous device numbers. Unknown or invalid payloads are exported as metadata rather than raw bytes. The private local history keeps up to seven days or 20,000 records per entry and contains identifiers and raw frames; treat it and configuration backups as private. Deleting the integration entry deletes that entry's packet history.

## Verification and known issues

Automated checks exercise the LAN transport with a loopback simulator, real Home Assistant climate states/services in Celsius and Fahrenheit, and Marketplace installation/update/rollback with local delivery fixtures. They do not establish physical compatibility, live GitHub/catalog behaviour or a complete UI installation. The [Marketplace verification record](docs/marketplace.md) explains those boundaries.

Two known control defects remain open: **RP-002**, where concurrent commands can overwrite an earlier change, and **RP-003**, where a combined temperature/HVAC-mode request can ignore the requested mode, including `off`. These are not fixed by removing the cloud or updating the climate API. The candidate remains experimental; passing CI is not acceptance of these risks or approval to publish a release.

## Documentation and development

The [documentation index](docs/README.md) groups installation, compatibility, protocol, requirements, traceability, SDLC and test evidence. Start there for the development commands and the remaining acceptance gates. Version history is in the [changelog](CHANGELOG.md).

## Credits and license

Original integration by [bwitosze](https://github.com/bwitosze/haier-smartair2-cloud-for-homeassistant). Protocol work builds on Piotr Stadnicki ([fastfend](https://github.com/fastfend)), [ESPHome Haier](https://esphome.io/components/climate/haier/) and `paveldn/HaierProtocol`.

This project is not affiliated with or supported by Haier. [MIT license](LICENSE).
