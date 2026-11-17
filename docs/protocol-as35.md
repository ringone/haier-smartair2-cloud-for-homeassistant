# Haier AS35 local protocol

The two LAN captures came from an AS35TADHRA-TH with an MK-QTWIFI-04(B) module. The client read ordinary status and extended telemetry over TCP 56800. Both captures are in heating mode. The reported compressor frequency was 40 Hz in the first capture and 1 Hz in the second. The compressor bit was active in both.

## Frame format

**Scope warning:** these observations concern only the AS35TADHRA-TH + MK-QTWIFI-04(B) captures. Compatibility with other AC units, Wi-Fi modules or firmware is unknown. See [compatibility evidence and limits](compatibility.md); V2/V3 labels and frame lengths are not universal hardware profiles.

The 80-byte LAN envelope precedes an EPP frame. The two captures contained type `06` reports and type `02` replies with subcommand `6D 01`, type `02 / 7D 01` extended replies and type `04 / 0F 5A` alarm reports. The captured EPP frames used a checksum and CRC-16/ARC. In the extended frames, wire bytes `FF 55` carry one logical byte `FF`. All offsets below are zero-based within the logical data starting after the two-byte subcommand. Add 12 for the offset in the logical EPP frame.

The two extended replies and one alarm report are reproduced below. The sample contains EPP bytes and omits the LAN envelope.

```text
FF FF 38 40 00 00 00 00 00 02 7D 01 06 0A 85 00 02 01 00 00 00 00 29 00 4E 00 00 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 7C 7E 00 00 46 28 01 FF 55 02 25 00 58 46 2E FC
FF FF 38 40 00 00 00 00 00 02 7D 01 06 06 85 00 02 01 00 00 00 00 2B 00 4E 00 00 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 58 80 00 00 53 01 01 FF 55 02 25 00 58 08 B9 8A
FF FF 12 40 00 00 00 00 00 04 0F 5A 00 00 00 00 00 00 00 00 BF 0A 33
```

[Framing and integrity reference](https://github.com/paveldn/HaierProtocol/blob/main/doc/protocol_reference.rst)

## Normal status and shared fields

The first 32 bytes of both extended replies matched the ordinary status returned to the corresponding poll. The following table records observations and candidate meanings from the reference map.

| Offset / mask | Meaning | AS35 evidence |
|---|---|---|
| 0 | Target temperature, raw + 16 °C | `06` gave 22 °C in both captures. |
| 1 / `0F` | Vertical vane position | `0A` and `06` match the lowest and centre codes. The upper nibble is unassigned here. |
| 2 / `E0`, `07` | Mode and selected fan speed in the reference | `85` agrees with heat and auto on the AS35. The fork uses nibbles. Bits 3–4 are candidate special-mode bits and remained zero. |
| 3 | Unassigned | `00` in both. |
| 4 / `02` | Panel light | `02` in both. |
| 4 / `BD` | Candidate flags for 10 °C heat, half-degree target, intelligent mode, comfort, Fahrenheit and sterilisation, in ascending bit order | Zero in both. The reference adds 0.5 °C to the setpoint when bit 2 is set. AS35 support remains open. Bit 6 is unassigned in the reference. |
| 5 / `7F` | Power, ionisation, electric heat, boost, quiet, sleep and remote lock, in ascending bit order | `01` in both, with the power bit active. This heat flag is a separate field from actual heater state in extended telemetry. |
| 5 / `80` | Candidate command beep suppression | Zero in both. |
| 6 | Candidate humidity target, raw + 30% in the reference | `00` in both. Support remains open. |
| 7 / `07`, `C0` | Candidate horizontal vane and presence settings | `00` in both. Horizontal airflow on this AS35 is adjusted manually. Bits 3–5 are unassigned in the reference. |
| 8 / `01` | Filter replacement flag | Inactive in both. Other bits are unassigned here. |
| 9 / `10` | Self-clean | Inactive in both. |
| 9 / `EF` | Candidate fresh air, humidification, particle cleaning, formaldehyde cleaning, light, energy saving and cleaning-counter flags, in ascending bit order | Zero in both. |
| 10 | Room temperature, raw ÷ 2 | `29` → 20.5 °C and `2B` → 21.5 °C. A spontaneous report also gave `2C` → 22 °C. |
| 11 | Room humidity | `00` in both. The fork treats it as unavailable. |
| 12 | Outdoor ambient temperature, raw − 64 °C | `4E` → 14 °C in both extended replies. A spontaneous report gave `4F` → 15 °C. |
| 13 / `03`, `0C`, `30`, `80` | Candidate particle grade, air quality, presence and unit type | `00` in both. Bit 6 is unassigned in the reference. |
| 14 | Current error code | `00` in both. The separate alarm report also had no active bits. |
| 15 / `03`, `0C`, `80` | Command source, candidate secondary mode and candidate error confirmation | `03` in both, which the fork interprets as Wi-Fi. Bits 4–6 are unassigned in the reference. |
| 16–27 | Candidate two-byte fields for cleaning hours, indoor and outdoor PM2.5, formaldehyde, VOC and CO₂ | All zero. Availability and byte order for these optional measurements remain unverified on this unit. |
| 28–31 | Unassigned on this unit | All zero. Other layouts can include padding or additional fields. |

[ESPHome field definitions](https://github.com/esphome/esphome/blob/dev/esphome/components/haier/hon_packet.h#L62-L145) · [Layout variations](https://github.com/paveldn/haier-esphome/blob/master/docs/protocol_overview.rst#L59-L74)

## Extended telemetry

| Offset | Conversion or meaning | First capture | Second capture |
|---|---|---|---|
| 32–33 | Big-endian watts | 0 W with compressor active | 0 W with compressor active |
| 34 | Indoor coil, raw ÷ 2 − 20 °C | `7C` → 42 °C | `58` → 24 °C |
| 35 | Outdoor discharge, raw − 64 °C | `7E` → 62 °C | `80` → 64 °C |
| 36–37 | Outdoor coil and inlet, raw − 64 °C if supplied | `00 00`, unavailable | `00 00`, unavailable |
| 38 | Defrost probe, raw − 64 °C | `46` → 6 °C | `53` → 19 °C |
| 39 | Compressor frequency, 1 Hz per step | 40 Hz | 1 Hz |
| 40–41 | Compressor current, big-endian tenths of an amp when supplied | `01 FF`, unavailable | `01 FF`, unavailable |
| 42–43 | Big-endian actuator flags | `02 25` | `02 25` |
| 44–45 | Expansion valve field, big-endian raw units | `00 58` → 88 | `00 58` → 88 |

The field at offset 35 likely measures refrigerant discharge at the compressor. ESPHome labels the position as outdoor outlet temperature, and Haismart Local calls it compressor discharge. The probe location remains unverified on this unit. The conversion matches both captures. The existing entity identifier is retained.

The actuator word has two-bit fields at shifts 0, 2, 4, 6, 8 and 10 for compressor, indoor fan, four-way valve, indoor electric heater, outdoor fan and defrost. Values 0 and 1 mean off and on. Values 2 and 3 are exported as unknown. In both captures the compressor and indoor fan were on. Defrost and the electric heater were off. The four-way valve and outdoor fan reported unavailable. Bits 12–15 are unassigned in this map. A transition to defrost has yet to be captured. The valve opening scale and its response to movement remain open.

[ESPHome conversions](https://github.com/esphome/esphome/blob/dev/esphome/components/haier/hon_climate.cpp#L951-L1035) · [Haismart Local engineering fields](https://github.com/enapt/haismart-local/blob/main/PROTOCOL.md#L239-L271) · [Haier service manual on the discharge thermistor](https://www.haierappliances.com/content/downloads/ductless/Forward-Series/Haier-Forward-Series-Service-Manual.pdf)

## Alarm reports

For the observed `04 / 0F 5A` report, the payload is an eight-byte big-endian bitmap. The least significant bit of the last byte is alarm 0. The first byte contains alarms 56–63. Both samples had all bits clear. The live sensor stays unknown until a matching report arrives and resets to unknown after disconnect until the next report. The export preserves active and clear reports. Individual display-code mappings require a correlated observation on this model.

[Reference bitmap parser](https://github.com/esphome/esphome/blob/dev/esphome/components/haier/hon_climate.cpp#L778-L827)

## History and export

The capture path records original incoming EPP bytes before filtering message types. Valid packets are grouped for sampling by device, type and subcommand. A changed frame is saved, as are repeated type `04` reports. Identical frames in the same group are sampled after five minutes. The store contains up to 20,000 records per config entry for up to seven days. Time-based pruning occurs on load, write or diagnostic export. Writes are batched for up to two minutes and pending records are flushed on unload. Removing the integration entry removes its history.

The JSON diagnostics contain UTC timestamps, anonymous device numbers, types, subcommands, lengths and validation results. They include full EPP bytes for recognised telemetry layouts with the expected address bytes. Unknown or invalid EPP payloads are kept only in the local store. The export omits their raw bytes, the LAN envelope, device addresses and credentials. The private store is `<config>/.storage/haier_smartair2.<entry_id>.packets`. It contains device identifiers and raw EPP bytes from unrecognised or invalid frames. Treat that file as local diagnostic data.

Compare a working baseline, the frames around an event and a later sample when investigating a bit. Record the operating mode, the code shown on the unit and the start or end of a real defrost cycle alongside the packet timestamps. A zero in a single capture may be an inactive flag, a valid zero or an unused field.
