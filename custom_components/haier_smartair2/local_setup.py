"""Length-based codec selection, not universal device/protocol identification."""
from .codec import Codec, CodecV2, CodecV3, extract_block


def codec_for_status(frame: bytes) -> Codec:
    """Match known 6D01 lengths heuristically; do not establish hardware compatibility."""
    frame_type, block = extract_block(frame)
    if frame_type not in (0x02, 0x06) or frame[10:12] != b"\x6d\x01":
        raise ValueError("Expected a validated Haier 6D01 status frame")
    if len(block) == 24:
        return CodecV2()
    if len(block) == 32:
        return CodecV3()
    raise ValueError(f"Unsupported Haier local status block length: {len(block)} (expected 24 or 32)")
