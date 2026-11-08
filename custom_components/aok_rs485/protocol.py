"""A-OK RS-485 protocol v05. No Home Assistant dependencies.

Commands: 9A ID CHANNEL_LOW CHANNEL_HIGH COMMAND DATA XOR
Responses from AM68-EC-P: D8 ID CHANNEL_LOW CHANNEL_HIGH CURRENT VOLTAGE RPM POSITION FLAGS XOR FF
"""

from dataclasses import dataclass
from functools import reduce
from operator import xor

HEADER_COMMAND = 0x9A
HEADER_RESPONSE = 0xD8
COMMAND_UP = 0xDD
COMMAND_STOP = 0xCC
COMMAND_DOWN = 0xEE
COMMAND_ACTION = 0x0A
COMMAND_QUERY = 0xCC
RESPONSE_LENGTH = 11


def checksum(payload: bytes) -> int:
    return reduce(xor, payload, 0)


def channel_mask(channel: int) -> tuple[int, int]:
    if not 1 <= channel <= 16:
        raise ValueError("channel must be between 1 and 16")
    mask = 1 << (channel - 1)
    return mask & 0xFF, (mask >> 8) & 0xFF


def frame(device_id: int, channel: int, command: int, value: int) -> bytes:
    if not 0 <= device_id <= 99:
        raise ValueError("device_id must be between 0 and 99")
    if not 0 <= command <= 255 or not 0 <= value <= 255:
        raise ValueError("command and value must be bytes")
    lo, hi = channel_mask(channel)
    data = bytes((device_id, lo, hi, command, value))
    return bytes((HEADER_COMMAND,)) + data + bytes((checksum(data),))


def open_frame(device_id: int, channel: int) -> bytes:
    return frame(device_id, channel, COMMAND_ACTION, COMMAND_UP)


def close_frame(device_id: int, channel: int) -> bytes:
    return frame(device_id, channel, COMMAND_ACTION, COMMAND_DOWN)


def stop_frame(device_id: int, channel: int) -> bytes:
    return frame(device_id, channel, COMMAND_ACTION, COMMAND_STOP)


def position_frame(device_id: int, channel: int, ha_position: int) -> bytes:
    """HA: 100=open / 0=closed; motor: 0=open / 100=closed."""
    if not 0 <= ha_position <= 100:
        raise ValueError("ha_position must be between 0 and 100")
    return frame(device_id, channel, COMMAND_UP, 100 - ha_position)


def query_frame(device_id: int, channel: int) -> bytes:
    if device_id == 0:
        raise ValueError("Status query requires a specific device ID (1..99)")
    return frame(device_id, channel, COMMAND_QUERY, 0x00)


@dataclass(frozen=True)
class MotorStatus:
    device_id: int
    channels: int
    current: int
    voltage: int
    rpm: int
    motor_position: int
    flags: int

    @property
    def ha_position(self) -> int:
        return 100 - self.motor_position

    @property
    def moving(self) -> bool:
        return bool(self.flags & 0x01)

    @property
    def limits_set(self) -> bool:
        return bool(self.flags & 0x02)

    @property
    def moving_to_position(self) -> bool:
        return bool(self.flags & 0x40)


def parse_status(raw: bytes, expected_id: int, expected_channel: int) -> MotorStatus:
    if len(raw) != RESPONSE_LENGTH:
        raise ValueError(f"Invalid response length: {len(raw)}")
    if raw[0] != HEADER_RESPONSE:
        raise ValueError("Incorrect response header")
    if raw[-1] != 0xFF:
        raise ValueError("Incorrect response terminator (expected FF)")
    if checksum(raw[1:-2]) != raw[-2]:
        raise ValueError("Incorrect response XOR checksum")
    device_id, lo, hi, current, voltage, rpm, position, flags = raw[1:-2]
    if device_id != expected_id:
        raise ValueError(f"Response from unexpected device ID {device_id}")
    bit_low, bit_high = channel_mask(expected_channel)
    if not ((lo & bit_low) or (hi & bit_high)):
        raise ValueError("Response does not include the configured channel")
    if not 0 <= position <= 100:
        raise ValueError(f"Invalid motor position {position}")
    return MotorStatus(device_id, lo | (hi << 8), current, voltage, rpm, position, flags)
