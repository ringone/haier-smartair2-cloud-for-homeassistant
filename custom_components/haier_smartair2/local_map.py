"""Validate a comma-separated MAC:IPv4 map without network lookups."""
from __future__ import annotations

from ipaddress import IPv4Address
import re

_MAC = re.compile(r"(?:[0-9a-fA-F]{12}|(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})\Z")


def parse_local_map(raw: str | None) -> dict[str, str]:
    """Return normalized MACs and literal IPv4 addresses, or reject the map."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Configure at least one local MAC:IPv4 mapping")
    out: dict[str, str] = {}
    for part in raw.split(","):
        try:
            mac_raw, ip_raw = part.strip().rsplit(":", 1)
        except ValueError as err:
            raise ValueError("Expected MAC:IPv4, separated by commas") from err
        mac_raw = mac_raw.strip()
        if not _MAC.fullmatch(mac_raw):
            raise ValueError("MAC must contain exactly 12 hexadecimal digits")
        mac = mac_raw.replace(":", "").upper()
        ip = IPv4Address(ip_raw.strip())
        if ip.is_unspecified or ip.is_multicast or ip == IPv4Address("255.255.255.255"):
            raise ValueError("Use a unicast IPv4 device address")
        if mac in out or str(ip) in out.values():
            raise ValueError("Duplicate MAC or IPv4 address")
        out[mac] = str(ip)
    return out


def format_local_map(mapping: dict[str, str]) -> str:
    """Serialize a validated mapping for config entries and forms."""
    return ",".join(f"{mac}:{ip}" for mac, ip in mapping.items())
