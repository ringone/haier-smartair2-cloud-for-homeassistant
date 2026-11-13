# Hardware compatibility: evidence and uncertainty

## Scope of this fork

**We do not know whether this fork's implementation is valid on other air conditioners, Wi-Fi modules or firmware revisions.** The only explicitly identified hardware combination documented in this fork is **Haier AS35TADHRA-TH + MK-QTWIFI-04(B)**. Its byte map comes from recorded captures and prior calibration described in [the AS35 protocol notes](protocol-as35.md).

The local-only 0.3.0 build has been exercised against recorded frames and a loopback simulator under real Home Assistant, **not a physical air conditioner during this development session**. Do not read those automated results as fresh physical verification, even for the documented AS35 combination.

Other devices are **unverified/experimental**, not declared supported. Similar names, use of the SmartAir2 app, a reachable TCP 56800 port or a valid checksum do not establish a matching control layout. Encrypted/cloud-only modules cannot use this local-only implementation.

## Protocol selection is not universal identification

The original integration selects V2/V3 from the cloud-provided `typeIdentifier` string length. The local-only build instead selects a retained codec from a recognised status-block length: 24 bytes for V2, 32 for V3.

That local rule is a **heuristic for known formats**, not proof that the device uses the corresponding semantic layout. Unrecognised lengths fail, but the check cannot exclude a different layout with a recognised length. Frame length/checksum/CRC validation establishes framing integrity, not the meaning of every control byte.

A V2 codec being present in the source is not evidence of physically verified V2 LAN hardware. Adding explicit per-device profiles and independently validating identification remain separate work; this documentation change does not implement those safeguards.

## What upstream actually identifies

This review inspected the upstream repository at commit `56e6695626512f60a6aeddabd7f493c8344bb966`, its README, public issue/PR descriptions and the file diffs of PRs 4 and 5. It is not a survey of every external project or every installation.

### Product family, not an exact Wi-Fi module

The upstream repository description names **Haier Tundra Plus** and original USB dongles. It does not identify a specific air-conditioner model code, Wi-Fi part number or firmware revision there.[1]

### Main README: two generic generations

Upstream calls V2 cloud support full and V3 local support experimental. It explicitly says that its V3 behavior was calibrated on a single unit, asks for status captures when mode/fan behavior differs, and does not name that unit or its dongle model in the support table. These are upstream claims, not a compatibility guarantee for this local-only fork.[2]

### Open PR 4: another reported V3 field mapping, hardware unnamed

The contributor reports testing V3 controls on a real unit under Home Assistant 2026.10.4, including horizontal vanes, Health, panel display and self-clean. Their proposal enables extra controls only for opted-in MACs. The report does not supply an exact AC or Wi-Fi-module part number. It was an open, unmerged proposal when inspected, not merged upstream behavior or independent verification by this fork.[3]

Its reported horizontal-vane functionality contrasts with the manually adjusted horizontal airflow documented on the AS35 in this fork. That difference is a reason not to generalize available features from the label V3 alone; it does not by itself prove a different framing protocol.[3]

### Open PR 5: reported V2 cloud testing, hardware unnamed

The contributor reports Health control on three V2 cloud units using profile `00000000000000008080000000041410`. They describe dedicated `4d09` / `4d08` commands and a side effect when trying a cumulative group command instead. No exact AC or Wi-Fi part number is given in the proposal. It was open and unmerged when inspected. Cloud validation does not establish plaintext LAN compatibility or validity of this fork's V3 controls.[4]

## Evidence needed before adding a device as verified

Record the exact AC model, Wi-Fi-module part number and firmware when available; distinguish reported user observations from reproducible captures. Check read-only status against the physical display/remote first, then validate individual commands and their side effects. Document the transport and each confirmed feature, not just V2/V3. Never publish account credentials, device addresses or private raw captures in a compatibility report.

## Sources

[1] https://api.github.com/repos/bwitosze/haier-smartair2-cloud-for-homeassistant
[2] https://raw.githubusercontent.com/bwitosze/haier-smartair2-cloud-for-homeassistant/main/README.md
[3] https://github.com/bwitosze/haier-smartair2-cloud-for-homeassistant/pull/4
[4] https://github.com/bwitosze/haier-smartair2-cloud-for-homeassistant/pull/5
