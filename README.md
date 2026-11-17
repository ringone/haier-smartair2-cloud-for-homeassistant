# Haier SmartAir2 Local for Home Assistant

Control a compatible Haier air conditioner from Home Assistant over your local network. You do not need a Haier account, and this integration does not use the Haier cloud.

**Current release: [0.3.0](https://github.com/ringone/haier-smartair2-cloud-for-homeassistant/releases/tag/0.3.0).**

## Before you install

- You need **Home Assistant 2026.11.0 or newer** and a compatible older SmartAir2 Wi-Fi module. hOn, encrypted modules and devices that work only through the cloud are not supported.
- The only documented combination is **Haier AS35TADHRA-TH + MK-QTWIFI-04(B)**, based on earlier device captures. **Version 0.3.0 has not been tested on a physical air conditioner.** Compatibility with other models, modules and firmware is unknown. Read the [compatibility notes](docs/compatibility.md) before trying another device.
- Home Assistant must be able to reach the air conditioner on your local network. Give it a fixed local IP address or reserve one in your router. Use a trusted network and do not expose the air conditioner directly to the Internet: its local connection is not encrypted or authenticated.

**Before updating, make a full Home Assistant backup and keep a copy of the old integration files. Keep the existing integration entry; do not delete it to upgrade.** Backups can contain private information. If you need to go back, you may have to restore both the configuration and the old files. Follow the [installation and recovery guide](docs/installation.md).

If you installed the integration from another repository, read that guide first. Switching repository ownership has not been validated; deleting the entry or uninstalling the old files is not a proven safe way to switch.

## Install

<!-- ha-marketplace:exclude-start -->
1. Open **Settings → Marketplace → Add from link**.
2. Add this repository and install **Haier SmartAir2**:
   ```text
   https://github.com/ringone/haier-smartair2-cloud-for-homeassistant
   ```
3. A first installation normally does not require a restart. After updating an existing installation or replacing its files, restart Home Assistant.

For a manual installation, use the ZIP attached to the [0.3.0 release](https://github.com/ringone/haier-smartair2-cloud-for-homeassistant/releases/tag/0.3.0) and follow the [installation guide](docs/installation.md). Downloads and updates need access to GitHub; controlling the air conditioner stays local.
<!-- ha-marketplace:exclude-end -->

## Connect your air conditioner

1. Find the air conditioner's Wi-Fi MAC address and local IP address in your router.
2. Open **Settings → Devices & services → Add integration → Haier SmartAir2**.
3. Enter the MAC address followed by a colon and the IP address. For example:
   ```text
   AA:BB:CC:DD:EE:FF:192.168.1.50
   ```
   For more than one device, separate the pairs with commas. Use local IPv4 addresses, not hostnames or IPv6.

To change an address or add a device later, open **Configure** on the existing integration. Enter the complete list of devices you want to keep. Changing only an IP address keeps the device identity.

## Use the controls

The integration provides temperature, operating mode and fan controls. Extra controls, such as boost, sleep and vertical airflow, depend on the device. Some readings may be unavailable when their meaning is not confirmed; a reported 0 W is not proof that the unit uses no power.

**Known control issues remain:** simultaneous changes can overwrite one another, and a combined temperature/mode request can ignore the requested mode, including off. Version 0.3.0 does not fix these issues. Do not treat publication as proof of correct physical operation.

## If it does not connect

Check the MAC/IP pair, the router's address reservation and whether Home Assistant can reach the device. Close the SmartAir2 phone app if it is holding the device's local connection. There is no cloud fallback if the local connection fails.

When upgrading from a version that used a Haier account, open **Configure** on the existing entry and supply the local addresses. Do not delete and recreate the entry. See the [upgrade and recovery instructions](docs/installation.md#upgrade-an-existing-entry) if it still cannot start.

For help, [open an issue](https://github.com/ringone/haier-smartair2-cloud-for-homeassistant/issues) with your air conditioner model, Wi-Fi module and Home Assistant version. Never post credentials, full configuration backups or private packet-history files. **Download diagnostics** provides an anonymized export for supported data; review it before sharing.

Technical documentation and development information are available on the [`develop` branch](https://github.com/ringone/haier-smartair2-cloud-for-homeassistant/tree/develop). See the [changelog](CHANGELOG.md) for version history.

## Credits and license

Original integration by [bwitosze](https://github.com/bwitosze/haier-smartair2-cloud-for-homeassistant), with protocol work from [fastfend](https://github.com/fastfend), [ESPHome Haier](https://esphome.io/components/climate/haier/) and `paveldn/HaierProtocol`.

This project is not affiliated with or supported by Haier. [MIT license](LICENSE).
