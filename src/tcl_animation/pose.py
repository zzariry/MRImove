"""System-independent pose contract and display mapping."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Pose:
    """Pose in the animation reference frame, after adapter calibration.

    Rotations are degrees: rz drives horizontal feedback, rx vertical feedback,
    and ry square rotation. Translation uses tx horizontally and -tz vertically.
    Adapters must convert their axes, signs, units and reference frame accordingly.
    Frame/quality/timestamps are metadata; unknown values may use the defaults.
    """
    frame: int
    tx: float
    ty: float
    tz: float
    rx: float
    ry: float
    rz: float
    quality: float = 1.0
    frame_time_ms: float = 0.0
    table_position: int = 0
    flags: int = 0


def decode_packet(data: bytes, packet_format: str = "windows-le") -> Pose:
    """Compatibility entry point; new code should use adapters.tcl.decode_tcl_packet."""
    from .adapters.tcl import decode_tcl_packet
    return decode_tcl_packet(data, packet_format)


class Feedback:
    """Apply the original 0.1-unit deadband to the displayed pose."""

    def __init__(self, translation=False, recenter=False, deadband=0.1):
        self.translation = translation
        self.recenter = recenter
        self.deadband = deadband
        self.values = [0.0, 0.0, 0.0]
        self.origin = None

    def update(self, pose: Pose):
        incoming = (pose.tx, -pose.tz, pose.ty) if self.translation else (pose.rz, pose.rx, pose.ry)
        for index, value in enumerate(incoming):
            if abs(value - self.values[index]) >= self.deadband:
                self.values[index] = value
        if self.origin is None:
            self.origin = self.values[:2] if self.recenter else [0.0, 0.0]
        return (self.values[0] - self.origin[0], self.values[1] - self.origin[1], self.values[2])
