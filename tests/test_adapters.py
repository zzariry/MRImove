import json
import socket
import struct
import unittest
from tcl_animation.adapters.tcl import parse_tcl_packet, tcl_to_pose, decode_tcl_packet
from tcl_animation.pose import Pose
from tcl_animation.sources import UDPSource, load_decoder, validate_pose


class AdapterTests(unittest.TestCase):
    def test_tcl_separate_parse_and_transform(self):
        data = struct.pack('<ii8fiii', 0, 9, 1, 2, 3, 1, 0, 0, 0, 1, 5, 0, 0)
        raw = parse_tcl_packet(data)
        self.assertEqual(raw.translation, (1, 2, 3))
        self.assertEqual(tcl_to_pose(raw), decode_tcl_packet(data))
        self.assertEqual(tcl_to_pose(raw).tx, -3)

    def test_custom_udp_decoder_not_tcl(self):
        # Independent JSON converter: no TCL transformation is applied.
        def decoder(data):
            fields = json.loads(data)
            return Pose(1, 0, 0, 0, fields['vertical'], 0, fields['horizontal'])
        with UDPSource(decoder, '127.0.0.1', 0) as source:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                sender.sendto(b'bad', source.socket.getsockname())
                sender.sendto(b'{"horizontal":4,"vertical":2}', source.socket.getsockname())
            import select
            select.select([source.socket], [], [], 1)
            poses = source.poll()
            self.assertEqual(len(poses), 1)
            self.assertEqual((poses[0].rx, poses[0].rz), (2, 4))
        self.assertEqual(source.socket.fileno(), -1)

    def test_adapter_validation(self):
        self.assertTrue(callable(load_decoder('tcl_animation.adapters.tcl:decode_tcl_packet')))
        with self.assertRaises(ValueError):
            load_decoder('invalid-spec')
        with self.assertRaises(TypeError):
            validate_pose({})
        with self.assertRaises(ValueError):
            validate_pose(Pose(0, float('nan'), 0, 0, 0, 0, 0))
