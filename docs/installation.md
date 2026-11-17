# Installation, migration and rollback

This guide describes the unpublished 0.3.0 local-only candidate. The current published release is 0.2.3 and still contains the previous hybrid implementation. Neither a pull request nor a merge publishes 0.3.0.

Before installing, read the [hardware and firmware limits](compatibility.md). This candidate requires Home Assistant >=2026.11.0 and Python >=3.14.2. It has not been physically validated on an air conditioner.

## Prepare a backup and LAN access

1. Back up the complete Home Assistant configuration and the old `custom_components/haier_smartair2/` directory. Include private `.storage` data, configuration entries and the history you need for rollback. Keep the backup private.
2. Record the source repository and installed integration version. Keep the matching old files with the backup.
3. Reserve each module's IPv4 address in DHCP, or assign a fixed address. Home Assistant must reach the module on TCP 56800.
4. Close the SmartAir2 app if it occupies the module's only local connection. Keep the module on a trusted LAN; do not expose that plaintext port to the Internet.
5. Prepare the MAC:IPv4 map. Knowing an address does not prove the module has a compatible plaintext protocol.

Do not delete an existing integration entry to upgrade. Deleting it also removes its packet history and can remove device/entity registrations.

## Install from Marketplace after publication

Once a reviewed release is available:

1. Open **Settings → Marketplace → Add from link**.
2. Add `https://github.com/ringone/haier-smartair2-cloud-for-homeassistant` and install Haier SmartAir2.
3. On a first installation with a config flow, Home Assistant can normally load it and open setup without a restart. If needed, open **Settings → Devices & services → Add integration**.
4. After updating or replacing code already loaded by Home Assistant, restart it before relying on the new code. The Marketplace provides a restart repair when required.

The ordinary repository link does not select a feature branch. While 0.3.0 is unpublished, do not assume a stable download contains the local-only candidate.

## Test a candidate manually

Use only the reviewed candidate branch or an artifact identified by its commit. The directory to install is `custom_components/haier_smartair2/` from that candidate, not the entire repository.

1. Make the full backup described above.
2. Replace `config/custom_components/haier_smartair2/` completely. Do not merge new files into the old directory: that can leave the removed `cloud.py` behind.
3. Restart Home Assistant, keeping the existing integration entry.
4. Open **Configure** and confirm the local map before depending on the integration. Review the logs for an unsupported layout, timeout or missing mapping.

Manual replacement changes the files, not Marketplace's repository-ownership records. It is not a demonstrated workaround for switching repositories.

## Upgrade an existing entry

The local-only migration keeps the integration domain `haier_smartair2`, entry ID, MAC-based entity identities and existing packet-history key. It moves the entry to config version 2 and removes the active cloud connection settings and credentials from data/options.

- A device already working locally must keep its MAC mapping.
- Devices formerly discovered through a Haier account are no longer discovered. They need explicit mappings and compatible plaintext LAN support.
- Options take precedence over the original map as a whole. Removed devices are not recovered by merging an old map back in.
- An entry with no usable map cannot start. Use **Configure** to enter a valid map; do not delete and recreate the entry.
- Changing only an IP preserves the MAC-based identity. Existing registry names are reused where available.

Enter comma-separated pairs, for example:

```text
00:11:22:33:44:55:192.168.1.50, AABBCCDDEEFF:192.168.1.51
```

The map must be nonempty and valid in full. MACs may contain colons; IPv6, hostnames and duplicate MACs/IPs are rejected. Configuration does not contact the devices or the Haier API. Runtime failures stay local and never trigger a cloud fallback.

## HACS migration and repository handover

Home Assistant 2026.11 migrates existing HACS installations to the built-in Marketplace. HACS instructions for versions before 2026.11 apply only to older releases that support those versions, not this candidate.

Changing from the upstream repository to this fork is a different operation. Both use `haier_smartair2`, and Marketplace refuses a second repository that tries to own the installed domain. The automated tests verify that refusal, not a successful ownership transfer.

**Upstream-to-fork handover remains unverified.** Do not delete the integration entry, uninstall the original files or edit manager storage as an assumed safe workaround. Preserve the original setup and a full backup until an ownership-transfer procedure has been tested in a disposable instance. A manual file replacement does not prove the handover is complete.

## Roll back safely

The migration removes active cloud credentials and changes the stored config-entry version. Copying old Python files over the candidate may therefore be insufficient.

Restore the matching code and configuration from the full backup using Home Assistant's normal backup/recovery procedure. Keep the old repository/version information, and avoid mixing files from different releases. Do not restore individual `.storage` fragments into a running instance as a substitute for a tested recovery procedure.

A full backup/restore on the user's installation is still a manual acceptance gate. Marketplace rollback tests cover failed file-install transactions with local fixtures; they do not prove operational rollback of a running air conditioner or a real recorder database.

## Checks after installation

Confirm the expected entry and entity identities, the local mapping and reachable IPs. Review status readings before attempting physical controls. The [requirements and acceptance plan](requisitos.md) lists the remaining hardware checks; [Marketplace verification](marketplace.md) separates automated cases from UI, live-download and physical validation.

Known command defects RP-002/RP-003 remain open. This guide does not provide a fix for concurrent command overwrites or combined temperature/HVAC-mode requests.
