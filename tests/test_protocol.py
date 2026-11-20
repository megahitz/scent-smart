"""Offline regression tests; no Home Assistant or Bluetooth required."""
import importlib
import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1] / 'custom_components' / 'scent_smart'
package = types.ModuleType('scent_smart_fixed')
package.__path__ = [str(ROOT)]
sys.modules['scent_smart_fixed'] = package
client = importlib.import_module('scent_smart_fixed.client')

REAL = bytes.fromhex('55 aa 53 88 05 00 01 01 ff 00 00 00 9f 05 0f 00 2c 01 01 00 00 00 00 02 ff 00 00 00 9f 05 05 00 c8 00 15 3a 9f 34 00 03 ff 00 00 00 00 00 3c 00 c8 00 16 3a 9f 34 00 04 ff 00 00 00 00 00 3c 00 c8 00 17 3a 9f 34 00 05 ff 00 00 00 00 00 3c 00 c8 00 18 3a 9f 34 2a 5a')

class ProtocolTest(unittest.TestCase):
    def test_validated_timer_list(self):
        self.assertTrue(hasattr(client, 'parse_timer_list'), 'timer-list parser is missing')
        timers = client.parse_timer_list(REAL)
        self.assertEqual(len(timers), 5)
        self.assertEqual(timers[1].to_payload().hex(), '0101ff0000009f050f002c0101000000')
        self.assertEqual(timers[2].tail, 0x349f3a15)

    def test_status_first_work_word_and_15_byte_timer(self):
        for word, expected in ((2, False), (11, True), (3, True)):
            payload = b'\x00\x00\x01\x00' + word.to_bytes(2, 'little') + b'\x64\x00' + REAL[7:22]
            # Status timer is a 15-byte record, without enable byte.
            state = client.parse_state(client.build_frame(0x21, payload))
            self.assertEqual(state.running, expected)
            self.assertEqual(state.active_timer.run, 15)
            self.assertIsNone(state.active_timer.enable)

    def test_reject_bad_or_truncated_frames(self):
        for data in (REAL[:-1], REAL[:-2], REAL[:-3], REAL[:-2] + b'\x00\x5a'):
            with self.assertRaises(ValueError):
                client.parse_timer_list(data)
        with self.assertRaises(ValueError):
            client.parse_state(client.build_frame(0x21, b'\0' * 4))

    def test_stream_accepts_every_fragment_boundary(self):
        self.assertTrue(hasattr(client, 'FrameStream'), 'stream decoder is missing')
        for cut in range(len(REAL) + 1):
            stream = client.FrameStream()
            result = stream.feed(REAL[:cut]) + stream.feed(REAL[cut:])
            self.assertEqual(result, [REAL])
        stream = client.FrameStream()
        self.assertEqual(stream.feed(b'garbage' + REAL + REAL), [REAL, REAL])

    def test_invalid_counts_duplicate_serial_and_enable(self):
        payload = bytearray(REAL[4:-2])
        for offset, value in [(0, 4), (2, 2), (19, 1)]:
            corrupt = bytearray(payload)
            corrupt[offset] = value
            with self.assertRaises(ValueError):
                client.parse_timer_list(client.build_frame(0x88, bytes(corrupt)))

    def test_stream_rejects_corrupt_frame_and_resynchronizes(self):
        broken = bytearray(REAL)
        broken[-2] ^= 1
        stream = client.FrameStream()
        self.assertEqual(stream.feed(broken + REAL), [REAL])

    def test_checksum_and_query(self):
        self.assertEqual(client.build_frame(8, b''), bytes.fromhex('55 aa 01 08 f8 5a'))
        self.assertEqual(client.checksum(REAL[:-2]), REAL[-2])

if __name__ == '__main__':
    unittest.main()
