import struct
import unittest
from tcl_animation.pose import decode_packet, Feedback, Pose
from tcl_animation.protocols import load_protocol, target_at


class CoreTests(unittest.TestCase):
    def test_cumulative_trial_and_repeatability(self):
        trial = load_protocol()
        for seconds, expected in [(0, (0, 0)), (10, (120, 0)),
                                  (20, (0, -120)), (30, (-120, 0))]:
            self.assertEqual(target_at(trial, seconds)[:2], expected)
        self.assertEqual(target_at(trial, 10)[:2], (120, 0))
        self.assertTrue(target_at(trial, 5)[2])
        self.assertFalse(target_at(trial, 4.99)[2])

    def test_windows_packet_translation_mapping(self):
        packet = struct.pack('<ii8fiii', 0, 42, 1, 2, 3, 1, 0, 0, 0, 0.9, 123, 7, 8)
        pose = decode_packet(packet)
        self.assertEqual((pose.tx, pose.ty, pose.tz), (-3, 2, -1))
        self.assertEqual((pose.rx, pose.ry, pose.rz), (0, 0, 0))
        self.assertEqual((pose.frame, pose.table_position, pose.flags), (42, 7, 8))

    def test_known_rotation(self):
        import math
        angle = math.radians(20) / 2
        packet = struct.pack('<ii8fiii', 0, 1, 0, 0, 0,
                             math.cos(angle), math.sin(angle), 0, 0, 1, 0, 0, 0)
        self.assertAlmostEqual(decode_packet(packet).rx, 20, places=5)

    def test_invalid_packets(self):
        with self.assertRaises(ValueError):
            decode_packet(b'bad')
        with self.assertRaises(ValueError):
            decode_packet(struct.pack('<ii8fiii', 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0))

    def test_recenter_and_deadband(self):
        feedback = Feedback(recenter=True)
        pose = Pose(0, 0, 0, 0, 2, 3, 4, 1, 0, 0, 0)
        self.assertEqual(feedback.update(pose), (0, 0, 3))
        self.assertEqual(feedback.update(Pose(1, 0, 0, 0, 2.05, 3.05, 4.05, 1, 0, 0, 0)), (0, 0, 3))


if __name__ == '__main__':
    unittest.main()
