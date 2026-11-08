"""Standalone protocol tests: python -m unittest discover -s tests -v"""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'custom_components' / 'aok_rs485'))
from protocol import (open_frame, close_frame, stop_frame, position_frame, query_frame,
                      parse_status, checksum, channel_mask)

class TestAokProtocol(unittest.TestCase):
    def test_open_document_example(self):
        self.assertEqual(open_frame(9, 8).hex(' '), '9a 09 80 00 0a dd 5e')
    def test_stop_document_example(self):
        self.assertEqual(stop_frame(9, 8).hex(' '), '9a 09 80 00 0a cc 4f')
    def test_close_document_example(self):
        self.assertEqual(close_frame(9, 8).hex(' '), '9a 09 80 00 0a ee 6d')
    def test_percentage_reverse(self):
        expected = bytes((0x9a, 9, 0x80, 0, 0xdd, 75))
        self.assertEqual(position_frame(9, 8, 25), expected + bytes((checksum(expected[1:]),)))
    def test_query(self):
        self.assertEqual(query_frame(9, 8).hex(' '), '9a 09 80 00 cc 00 45')
    def test_channel_16(self):
        self.assertEqual(channel_mask(16), (0, 128))
    def test_valid_status(self):
        data = bytes((9, 0x80, 0, 3, 24, 50, 75, 0x03))
        raw = b'\xd8' + data + bytes((checksum(data), 0xFF))
        status = parse_status(raw, 9, 8)
        self.assertEqual(status.ha_position, 25)
        self.assertTrue(status.moving)
        self.assertTrue(status.limits_set)
    def test_bad_checksum(self):
        raw = b'\xd8' + bytes((9, 0x80, 0, 3, 24, 50, 75, 0x03, 0, 0xFF))
        with self.assertRaises(ValueError): parse_status(raw, 9, 8)
    def test_real_motor_response_at_100(self):
        raw = bytes.fromhex('D8 01 01 00 05 18 00 64 02 7B FF')
        status = parse_status(raw, 1, 1)
        self.assertEqual(status.motor_position, 100)
        self.assertEqual(status.ha_position, 0)
        self.assertFalse(status.moving)

    def test_real_motor_response_while_moving(self):
        raw = bytes.fromhex('D8 01 01 00 03 18 1F 01 03 06 FF')
        status = parse_status(raw, 1, 1)
        self.assertEqual(status.motor_position, 1)
        self.assertTrue(status.moving)

    def test_real_motor_response_with_position(self):
        raw = bytes.fromhex('D8 01 01 00 25 18 63 1D 03 40 FF')
        self.assertEqual(parse_status(raw, 1, 1).motor_position, 29)

    def test_missing_terminator_rejected(self):
        raw = bytes.fromhex('D8 01 01 00 05 18 00 64 02 7B 00')
        with self.assertRaises(ValueError): parse_status(raw, 1, 1)

    def test_invalid_channels(self):
        for channel in (0, 17):
            with self.assertRaises(ValueError): channel_mask(channel)

if __name__ == '__main__': unittest.main()
