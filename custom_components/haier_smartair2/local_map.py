"""Parse the local-device map from the config flow.

Accepts a MAC with or without colons. The IP is the text after the last colon,
so ``2C:37:C5:0B:54:4A:192.168.10.183`` and ``2C37C50B544A:192.168.10.183``
both work. Several devices are separated by commas.
"""

from __future__ import annotations


def parse_local_map(raw: str | None) -> dict[str, str]:
    """Return ``{MAC: IP}`` with the MAC as 12 uppercase hex characters."""
    out: dict[str, str] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if ":" not in part:
            continue
        mac_raw, ip = part.rsplit(":", 1)
        mac = "".join(character for character in mac_raw if character.isalnum()).upper()
        ip = ip.strip()
        if len(mac) == 12 and ip:
            out[mac] = ip
    return out
