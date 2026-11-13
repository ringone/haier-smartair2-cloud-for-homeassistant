"""Protocol codecs for Haier SmartAir2 devices.

Two device generations speak slightly different smartair2 dialects; both wrap the
same frame envelope but lay out the status/command block differently:

* V2 (e.g. salon, cloud): status ``6d01`` = 12 big-endian 16-bit words; command
  ``4d5f`` = full 24-byte block (read-modify-write).
* V3 (e.g. maks, local): status ``6d01`` = byte layout; command ``6001`` = first
  10 bytes of the status block (read-modify-write). Extended sensors arrive in
  ``7d01`` (answer to ``4dfe``), 14 bytes starting at offset 32.
"""

from __future__ import annotations

from dataclasses import dataclass

from .const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MID,
    MODE_AUTO,
    MODE_COOL,
    MODE_DRY,
    MODE_FAN,
    MODE_HEAT,
)


@dataclass
class HaierState:
    """Normalised device state decoded from a status frame."""

    power: bool | None = None
    mode: int | None = None
    fan: int | None = None
    quiet: bool | None = None
    turbo: bool | None = None
    sleep: bool | None = None
    health: bool | None = None
    display: bool | None = None
    self_clean: bool | None = None
    lock_remote: bool | None = None
    electric_heat: bool | None = None
    swing_v: bool | None = None
    swing_pos: int | None = None
    target_temp: float | None = None
    current_temp: float | None = None
    outdoor_temp: float | None = None
    humidity: float | None = None
    error_code: int | None = None
    operation_source: str | None = None
    filter_change: bool | None = None
    power_w: float | None = None
    indoor_coil_temp: float | None = None
    outdoor_out_temp: float | None = None
    outdoor_coil_temp: float | None = None
    outdoor_in_temp: float | None = None
    defrost_temp: float | None = None
    compressor_hz: float | None = None
    compressor_current: float | None = None
    expansion_valve: float | None = None
    outdoor_fan: bool | None = None
    defrost_on: bool | None = None
    compressor_on: bool | None = None
    indoor_fan_on: bool | None = None
    four_way_valve: bool | None = None
    indoor_electric_heat_on: bool | None = None
    alarm_bits: tuple[int, ...] | None = None
    raw_block: bytes = b""

    def merged(self, **changes: object) -> "HaierState":
        data = {**self.__dict__, **changes}
        return HaierState(**data)


def _checksum(body: bytes) -> int:
    return sum(body) & 0xFF


def build_frame(ftype: int, subcmd: bytes, data: bytes) -> bytes:
    """Assemble a smartair2 frame: FF FF | len | flags | res(5) | type | sub | data | chk."""
    length = 8 + len(subcmd) + len(data)
    body = bytes([length, 0, 0, 0, 0, 0, 0, ftype]) + subcmd + data
    return b"\xff\xff" + body + bytes([_checksum(body)])


def _crc16_arc(data: bytes) -> int:
    crc = 0
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc


def _validate_frame(frame: bytes, stuffing: int = 0) -> None:
    if len(frame) < 13 or frame[:2] != b"\xff\xff" or frame[2] < 10:
        raise ValueError("not a smartair2 frame with a subcommand")

    checksum_offset = 2 + frame[2]
    has_crc = bool(frame[3] & 0x40)
    if len(frame) != checksum_offset + (3 if has_crc else 1):
        raise ValueError("invalid smartair2 frame length")
    body = frame[2:checksum_offset]
    if frame[checksum_offset] != ((_checksum(body) + stuffing) & 0xFF):
        raise ValueError("invalid smartair2 checksum")
    if has_crc and _crc16_arc(body) != int.from_bytes(frame[checksum_offset + 1 :], "big"):
        raise ValueError("invalid smartair2 CRC")


def parse_local_frame(frame: bytes) -> bytes:
    """Validate the LAN payload and return the frame with any stuffing removed."""
    try:
        _validate_frame(frame)
    except ValueError:
        if frame[:2] != b"\xff\xff" or b"\xff\x55" not in frame[2:]:
            raise
        # The LAN envelope can also carry an EPP frame with FF/55 byte stuffing.
        wire_body = frame[2:]
        logical_body = wire_body.replace(b"\xff\x55", b"\xff")
        if logical_body.replace(b"\xff", b"\xff\x55") != wire_body:
            raise
        end = logical_body[0]
        stuffing = logical_body[:end].count(0xFF) * 0x55
        frame = frame[:2] + logical_body
        _validate_frame(frame, stuffing)
    return frame


def extract_block(frame: bytes) -> tuple[int, bytes]:
    """Return the type and data of a logical frame, excluding the subcommand."""
    if len(frame) < 13 or frame[:2] != b"\xff\xff":
        raise ValueError("not a smartair2 frame")
    end = 2 + frame[2]
    if end < 12 or end >= len(frame):
        raise ValueError("invalid smartair2 frame length")
    return frame[9], frame[12:end]


def decode_alarm_bits(frame: bytes) -> tuple[int, ...]:
    """Decode the eight-byte 04/0F5A alarm report seen on the AS35."""
    frame_type, data = extract_block(frame)
    if frame_type != 0x04 or frame[10:12] != b"\x0f\x5a" or len(data) != 8:
        raise ValueError("not an eight-byte Haier alarm report")
    bitmap = int.from_bytes(data, "big")
    return tuple(bit for bit in range(64) if bitmap & (1 << bit))


POLL_FRAME = build_frame(0x01, b"\x4d\x01", b"")
BIG_POLL_FRAME = build_frame(0x01, b"\x4d\xfe", b"")

_SOURCE = {0: "other", 1: "remote", 2: "panel", 3: "wifi"}


def _temp64(raw: int) -> float | None:
    if raw in (0, 0xFF):
        return None
    return float(raw - 64)


class Codec:
    """Base codec (subclassed per device generation)."""

    poll = POLL_FRAME
    extra_fan_modes: tuple[str, ...] = ()
    supports_fan: bool = True
    supports_swing: bool = False
    supports_presets: bool = False
    supports_extras: bool = False

    def decode(self, frame: bytes) -> HaierState:
        raise NotImplementedError

    def decode_big(self, frame: bytes) -> dict:
        return {}

    def encode_set(self, state: HaierState, **changes) -> bytes:
        raise NotImplementedError


_QUIET_BIT = 1 << 2
_TURBO_BIT = 1 << 1
_SWING_V_BIT = 1 << 0


class CodecV2(Codec):
    """Salon-class device (word layout, 4d5f command). Verified via cloud."""

    extra_fan_modes = ("quiet", "turbo")
    supports_swing = True

    def decode(self, frame: bytes) -> HaierState:
        _ftype, data = extract_block(frame)
        w = [int.from_bytes(data[i : i + 2], "big") for i in range(0, len(data) - 1, 2)]
        if len(w) < 12:
            raise ValueError("short V2 status")
        return HaierState(
            current_temp=float(w[0]),
            mode=w[5],
            fan=w[6],
            quiet=bool(w[9] & _QUIET_BIT),
            turbo=bool(w[9] & _TURBO_BIT),
            swing_v=bool(w[7] & _SWING_V_BIT),
            power=bool(w[8] & 0x01),
            target_temp=float(w[11] + 16),
            raw_block=bytes(data),
        )

    def encode_set(self, state: HaierState, **changes) -> bytes:
        mode = changes.get("mode", state.mode) or 0
        fan = changes.get("fan", state.fan) or 0
        target = changes.get("target_temp", state.target_temp) or 16
        power = changes.get("power", state.power)
        w8 = w10 = w11 = 0
        if len(state.raw_block) >= 24:
            src = state.raw_block
            w8 = int.from_bytes(src[14:16], "big")
            w10 = int.from_bytes(src[18:20], "big")
            w11 = int.from_bytes(src[20:22], "big")
        if "quiet" in changes and changes["quiet"] is not None:
            w10 = (w10 | _QUIET_BIT) if changes["quiet"] else (w10 & ~_QUIET_BIT)
        if "turbo" in changes and changes["turbo"] is not None:
            w10 = (w10 | _TURBO_BIT) if changes["turbo"] else (w10 & ~_TURBO_BIT)
        if "swing_v" in changes and changes["swing_v"] is not None:
            w8 = (w8 | _SWING_V_BIT) if changes["swing_v"] else (w8 & ~_SWING_V_BIT)
        flags9 = 0x0001 if (power if power is not None else True) else 0x0000
        blk = bytearray(24)
        blk[10:12] = int(mode).to_bytes(2, "big")
        blk[12:14] = int(fan).to_bytes(2, "big")
        blk[14:16] = int(w8 & 0xFFFF).to_bytes(2, "big")
        blk[16:18] = int(flags9).to_bytes(2, "big")
        blk[18:20] = int(w10 & 0xFFFF).to_bytes(2, "big")
        blk[20:22] = int(w11).to_bytes(2, "big")
        blk[22:24] = int(round(target) - 16).to_bytes(2, "big")
        return build_frame(0x01, b"\x4d\x5f", bytes(blk))


_V3_MODE_FROM_NIBBLE = {0x0: MODE_AUTO, 0x2: MODE_COOL, 0x4: MODE_DRY, 0x8: MODE_HEAT, 0xC: MODE_FAN}
_V3_MODE_TO_NIBBLE = {v: k for k, v in _V3_MODE_FROM_NIBBLE.items()}
_V3_FAN_FROM_NIBBLE = {0x1: FAN_HIGH, 0x2: FAN_MID, 0x3: FAN_LOW, 0x5: FAN_AUTO}
_V3_FAN_TO_NIBBLE = {v: k for k, v in _V3_FAN_FROM_NIBBLE.items()}

_V3_POWER = 0x01
_V3_HEALTH = 0x02
_V3_EHEAT = 0x04
_V3_TURBO = 0x08
_V3_QUIET = 0x10
_V3_SLEEP = 0x20
_V3_LOCK = 0x40
_V3_DISPLAY = 0x02
_V3_CLEAN = 0x10
_V3_SWING_AUTO = 0x0C
_V3_SWING_CENTER = 0x06
# 10 control bytes + 22 bytes of sensors/reserved on the MK-QTWIFI-04 extended frame.
_V3_BIG_OFFSET = 32


def _set_bit(block: bytearray, index: int, mask: int, enabled: bool) -> None:
    if enabled:
        block[index] |= mask
    else:
        block[index] &= ~mask & 0xFF


def _actuator_state(bits: int, shift: int) -> bool | None:
    value = (bits >> shift) & 0x03
    return bool(value) if value < 2 else None


class CodecV3(Codec):
    """Byte-layout dongle (MK-QTWIFI-04). Command 6001, extended data in 7d01."""

    extra_fan_modes = ("quiet",)
    supports_swing = True
    supports_presets = True
    supports_extras = True

    def decode(self, frame: bytes) -> HaierState:
        _ftype, d = extract_block(frame)
        if len(d) < 10:
            raise ValueError("short V3 status")
        current = float(d[10]) / 2.0 if len(d) > 10 and d[10] > 10 else None
        outdoor = _temp64(d[12]) if len(d) > 12 else None
        humidity = float(d[11]) if len(d) > 11 and 0 < d[11] <= 100 else None
        nibble = d[1] & 0x0F
        source = _SOURCE.get(d[15] & 0x03, "other") if len(d) > 15 else None
        return HaierState(
            target_temp=float(d[0] + 16),
            mode=_V3_MODE_FROM_NIBBLE.get((d[2] >> 4) & 0x0F, MODE_AUTO),
            fan=_V3_FAN_FROM_NIBBLE.get(d[2] & 0x0F),
            quiet=bool(d[5] & _V3_QUIET),
            turbo=bool(d[5] & _V3_TURBO),
            sleep=bool(d[5] & _V3_SLEEP),
            health=bool(d[5] & _V3_HEALTH),
            electric_heat=bool(d[5] & _V3_EHEAT),
            lock_remote=bool(d[5] & _V3_LOCK),
            display=bool(d[4] & _V3_DISPLAY),
            self_clean=bool(d[9] & _V3_CLEAN),
            power=bool(d[5] & _V3_POWER),
            swing_v=nibble in (_V3_SWING_AUTO, 0x0E),
            swing_pos=nibble,
            current_temp=current,
            outdoor_temp=outdoor,
            humidity=humidity,
            error_code=int(d[14]) if len(d) > 14 else None,
            operation_source=source,
            filter_change=bool(d[8] & 0x01),
            raw_block=bytes(d),
        )

    def decode_big(self, frame: bytes) -> dict:
        _, d = extract_block(frame)
        if len(d) < _V3_BIG_OFFSET + 14:
            return {}
        bd = d[_V3_BIG_OFFSET : _V3_BIG_OFFSET + 14]
        current = int.from_bytes(bd[8:10], "big")
        actuators = int.from_bytes(bd[10:12], "big")
        valve = int.from_bytes(bd[12:14], "big")
        return {
            "power_w": float(int.from_bytes(bd[0:2], "big")),
            "indoor_coil_temp": None if bd[2] == 0 else float(bd[2]) / 2.0 - 20.0,
            "outdoor_out_temp": _temp64(bd[3]),
            "outdoor_coil_temp": _temp64(bd[4]),
            "outdoor_in_temp": _temp64(bd[5]),
            "defrost_temp": _temp64(bd[6]),
            "compressor_hz": float(bd[7]) if bd[7] <= 127 else None,
            "compressor_current": None if current >= 0x1FF else current / 10.0,
            "expansion_valve": None if valve > 4095 else float(valve),
            "compressor_on": _actuator_state(actuators, 0),
            "indoor_fan_on": _actuator_state(actuators, 2),
            "four_way_valve": _actuator_state(actuators, 4),
            "indoor_electric_heat_on": _actuator_state(actuators, 6),
            "outdoor_fan": _actuator_state(actuators, 8),
            "defrost_on": _actuator_state(actuators, 10),
        }

    def encode_set(self, state: HaierState, **changes) -> bytes:
        block = bytearray(state.raw_block[:10].ljust(10, b"\x00"))
        if changes.get("target_temp") is not None:
            block[0] = (int(round(changes["target_temp"])) - 16) & 0xFF
        if changes.get("mode") is not None:
            nib = _V3_MODE_TO_NIBBLE.get(changes["mode"])
            if nib is not None:
                block[2] = (nib << 4) | (block[2] & 0x0F)
        if changes.get("fan") is not None:
            nib = _V3_FAN_TO_NIBBLE.get(changes["fan"])
            if nib is not None:
                block[2] = (block[2] & 0xF0) | nib
        if changes.get("swing_pos") is not None:
            block[1] = (block[1] & 0xF0) | (int(changes["swing_pos"]) & 0x0F)
        elif changes.get("swing_v") is not None:
            if changes["swing_v"]:
                block[1] = (block[1] & 0xF0) | _V3_SWING_AUTO
            else:
                current = block[1] & 0x0F
                if current in (_V3_SWING_AUTO, 0x0E):
                    restore = state.swing_pos
                    if restore in (None, _V3_SWING_AUTO, 0x0E):
                        restore = _V3_SWING_CENTER
                    block[1] = (block[1] & 0xF0) | int(restore)
        if "display" in changes and changes["display"] is not None:
            _set_bit(block, 4, _V3_DISPLAY, bool(changes["display"]))
        if "self_clean" in changes and changes["self_clean"] is not None:
            _set_bit(block, 9, _V3_CLEAN, bool(changes["self_clean"]))
        if "quiet" in changes and changes["quiet"] is not None:
            _set_bit(block, 5, _V3_QUIET, bool(changes["quiet"]))
            if changes["quiet"]:
                _set_bit(block, 5, _V3_TURBO, False)
        if "turbo" in changes and changes["turbo"] is not None:
            _set_bit(block, 5, _V3_TURBO, bool(changes["turbo"]))
            if changes["turbo"]:
                _set_bit(block, 5, _V3_QUIET, False)
                _set_bit(block, 5, _V3_SLEEP, False)
        if "sleep" in changes and changes["sleep"] is not None:
            _set_bit(block, 5, _V3_SLEEP, bool(changes["sleep"]))
            if changes["sleep"]:
                _set_bit(block, 5, _V3_TURBO, False)
        if "health" in changes and changes["health"] is not None:
            _set_bit(block, 5, _V3_HEALTH, bool(changes["health"]))
        if "electric_heat" in changes and changes["electric_heat"] is not None:
            _set_bit(block, 5, _V3_EHEAT, bool(changes["electric_heat"]))
        if "lock_remote" in changes and changes["lock_remote"] is not None:
            _set_bit(block, 5, _V3_LOCK, bool(changes["lock_remote"]))
        if "power" in changes and changes["power"] is not None:
            _set_bit(block, 5, _V3_POWER, bool(changes["power"]))
        return build_frame(0x01, b"\x60\x01", bytes(block))


def codec_for_type(type_identifier: str | None) -> Codec:
    """Pick a codec by the device typeIdentifier (per Stadnicki's V2/V3 split)."""
    if type_identifier and len(type_identifier) > 32:
        return CodecV3()
    return CodecV2()
