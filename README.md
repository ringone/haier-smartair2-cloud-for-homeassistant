# Haier SmartAir2 for Home Assistant

Fork of [bwitosze/haier-smartair2-cloud-for-homeassistant](https://github.com/bwitosze/haier-smartair2-cloud-for-homeassistant) for legacy Haier air conditioners that use the **SmartAir2** app, not hOn.

It keeps the same integration domain, `haier_smartair2`, so an existing config entry (account, region, and local `MAC:IP` map) continues to work after you switch to this repository.

## Why this fork exists

Upstream 0.1.4 already runs these units through the cloud or over the LAN, and basic climate control works once a plaintext dongle is mapped as `MAC:IP`. It does not expose the rest of what that dongle reports.

This fork was made for a Haier **AS35TADHRA-TH** with the **MK-QTWIFI-04(B)** Wi-Fi dongle. That dongle speaks SmartAir2 V3 on TCP port `56800`. The status frame carries Power, Sleep, Health, the panel light, self-clean, remote lock, electric heat, and the vertical vane. A second frame carries outdoor and coil temperatures, defrost temperature, and compressor frequency. Those values were decoded on this unit and added here, together with European Portuguese names.

It is also a separate repository so an update from the upstream project does not replace these changes. Home Assistant 2026.11 installs and updates this kind of repository from the Marketplace.

## What 0.2.0 adds

- Presets **Power** and **Sleep**. Quiet stays a fan mode, shown as **Silêncio** in Portuguese.
- Switches for Health, panel light, self-clean, remote lock, and electric heat.
- Vertical airflow positions on V3, instead of swing on/off only.
- Sensors for outdoor temperature, coil temperatures, defrost temperature, compressor frequency, and the other values this firmware reports.
- European Portuguese translations (`translations/pt.json`).
- Marketplace metadata: category, brand icon, and validation workflows.

V2 behaviour from upstream is unchanged: cloud control, quiet, turbo, and swing on/off.

## Features

- Native `climate` entities (target temperature, HVAC mode, fan speed, on/off)
- **Hybrid transport, chosen per device:**
  - **Cloud** — MQTT gateway (`gw-gea-*.haieriot.net`), for encrypted dongles
  - **Local** — direct TCP `56800`, for plaintext dongles
- Fan speeds `auto`, `low`, `medium`, and `high`, plus quiet on both generations and turbo on V2
- Config flow for the SmartAir2 account, region, and optional local `MAC:IP` pairs
- Options flow to change the region or the local map without removing the integration

## Supported devices

| Generation | Example | Transport | Status |
|---|---|---|---|
| **V2** (`typeIdentifier` of 32 characters or fewer) | wall units with an encrypted dongle | Cloud | Target, mode, fan, quiet, turbo, swing on/off, room temperature |
| **V3** (`typeIdentifier` longer than 32 characters) | MK-QTWIFI-04(B) on AS35TADHRA-TH | Local | The 0.2.0 functions above, calibrated on that unit |

Other V3 dongles can use a different byte layout. If mode or fan speed is wrong, open an issue with a status frame.

On this V3 layout, mode and fan speed share one byte, and quiet is a separate flag. Turning quiet on makes the unit return the fan speed to auto, so quiet and a fixed speed are not used together.

## Installation

### Marketplace (Home Assistant 2026.11 or newer)

1. Connect GitHub in the Marketplace, if it is not connected yet.
2. Go to **Settings → Marketplace → Add from link**.
3. Enter `https://github.com/ringone/haier-smartair2-cloud-for-homeassistant`.
4. Install the latest **Haier SmartAir2** release, then restart Home Assistant.

If this domain is already installed from the upstream repository, remove that repository in the Marketplace first. Do not delete the entry under **Settings → Devices & services**. Deleting that entry removes the account and the local device map.

### HACS (Home Assistant before 2026.11)

1. HACS → three-dot menu → **Custom repositories**.
2. Add `https://github.com/ringone/haier-smartair2-cloud-for-homeassistant`, category **Integration**.
3. Install **Haier SmartAir2**, then restart Home Assistant.

### Manual

Copy `custom_components/haier_smartair2/` into `config/custom_components/` and restart.

## Configuration

**Settings → Devices & services → Add integration → Haier SmartAir2:**

- **E-mail / Password** — the SmartAir2 account
- **Region** — gateway region. Only **Europe** is confirmed. US and Asia are best guesses.
- **Local devices** *(optional)* — `MAC:IP` pairs, comma-separated. Colons in the MAC are kept. Example: `2C:37:C5:0B:54:4A:192.168.10.183`

A device that is not listed, or whose local port refuses a plaintext session, stays on cloud control.

Region and the local map can be changed later with **Configure**. Moving a device between cloud and local can change its `entity_id`.

The SmartAir2 phone app holds the dongle's only local session. Close the app while Home Assistant is using local control.

## Local diagnostics

On compatible V3 units, the integration shows **Compressor running**, **Indoor fan running**, **Defrost active**, and **Active alarms**. Outdoor fan, four-way valve and the actual indoor heater state are disabled by default because many units provide no usable reading. An unavailable actuator code appears as unknown while the device is connected. The alarm sensor includes the active bit numbers and remains unknown until the module sends an alarm report.

Use **Download diagnostics** from the device or integration menu to export recent local frames. The integration keeps a rolling history on the Home Assistant host across reconnects and restarts. It records changes, alarm reports and periodic samples of unchanged packets, keeping up to seven days or 20,000 records per config entry. Known telemetry frames are exported in full with timestamps and anonymous device numbers. Unrecognised or invalid frames are retained locally and appear in the export with metadata only.

See the [AS35 protocol notes](docs/protocol-as35.md) for the byte map, conversions, evidence and capture format.

## Limitations

- SmartAir2 accounts on `uhome.haieriot.net` only. Not hOn, and not the China cloud.
- Self-clean does not start while the unit is in heat, auto, or sleep.
- On the MK-QTWIFI-04(B) firmware used here, the two recorded captures reported 0 W and an unavailable compressor-current value. The expansion valve field reported 88 raw units in both. Its response to changes in valve position remains unverified.
- Left/right airflow on the AS35TADHRA-TH is manual. There is no command for it.
- The timer is not a simple status bit and is not exposed.

## Changelog

- **0.2.3** — expose local V3 actuator states and active alarm bits. Keep a bounded local packet history and make known frames downloadable through Home Assistant diagnostics. Document observed and candidate fields in the AS35 protocol notes.
- **0.2.2** — local sessions reconnect after a disconnect or status timeout. The integration clears stale readings and validates frame length, checksum, and optional CRC while preserving the full telemetry payload.
- **0.2.1** — a MAC written with colons is accepted in the local map; turning swing off restores the last fixed vane instead of jumping to the centre; self-clean is refused in auto, heat, or sleep; the expansion valve is no longer recorded as a measurement without a unit.
- **0.2.0** — V3 controls and telemetry for the MK-QTWIFI-04(B), European Portuguese names, and the metadata the Marketplace expects. Same domain as upstream, so an existing config entry is kept.
- **0.1.4** — upstream: local read and keep-alive loops run in the background, the local TCP connect times out after 10 seconds, and cloud TLS setup no longer blocks startup.
- **0.1.3** — upstream: vertical louvre (swing) on V2 units.
- **0.1.2** — upstream: V3 fan speed and quiet mode calibrated against the remote.

## Credits

The integration itself comes from [bwitosze](https://github.com/bwitosze/haier-smartair2-cloud-for-homeassistant). The protocol work it builds on is from **Piotr Stadnicki** ([fastfend](https://github.com/fastfend)), whose `HaierACBridge` and `homebridge-haieracbridge-platform` mapped the SmartAir2 cloud, and from [ESPHome Haier](https://esphome.io/components/climate/haier/) / `paveldn/HaierProtocol`, which documented the frame format.

## Disclaimer

This is an **unofficial** integration. It is not affiliated with, endorsed by, or supported by Haier. It talks to a private API reconstructed by reverse engineering. Use it at your own risk. Names and trademarks belong to their owners.

## License

[MIT](LICENSE)
