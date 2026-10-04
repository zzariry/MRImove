"""TCL binary decoding and coordinate conversion, isolated from the viewer."""

from dataclasses import dataclass
import struct
import numpy as np
from scipy.spatial.transform import Rotation
from ..pose import Pose

PACKET_FORMATS = {"windows-le": "<ii8fiii", "native": "@il8fiii"}


@dataclass(frozen=True)
class TCLSample:
    frame: int
    translation: tuple[float, float, float]
    quaternion: tuple[float, float, float, float]  # qr, qx, qy, qz
    quality: float
    frame_time_ms: float
    table_position: int
    flags: int


def parse_tcl_packet(data: bytes, packet_format: str = "windows-le") -> TCLSample:
    """Extract raw TCL fields without transforming the coordinate frame."""
    fmt = PACKET_FORMATS[packet_format]
    if len(data) < struct.calcsize(fmt):
        raise ValueError(f"TCL packet requires at least {struct.calcsize(fmt)} bytes")
    _, frame, x, y, z, qr, qx, qy, qz, quality, stamp, table, flags = struct.unpack_from(fmt, data)
    return TCLSample(frame, (x, y, z), (qr, qx, qy, qz), quality, stamp, table, flags)


def tcl_to_pose(sample: TCLSample) -> Pose:
    """Convert a raw TCL sample using the original experiment's mapping."""
    x, y, z = sample.translation
    qr, qx, qy, qz = sample.quaternion
    if not np.isfinite([x, y, z, qr, qx, qy, qz, sample.quality, sample.frame_time_ms]).all():
        raise ValueError("Non-finite TCL values")
    matrix = np.eye(4)
    matrix[:3, :3] = Rotation.from_quat([qx, qy, qz, qr]).as_matrix()
    matrix[:3, 3] = [x, y, z]
    offset = np.diag([1, -1, 1, 1])
    transformed = np.linalg.inv(offset @ matrix @ offset)
    tz, ty, tx = transformed[:3, 3]
    rx, ry, rz = Rotation.from_matrix(transformed[:3, :3]).as_euler("xyz", degrees=True)
    return Pose(sample.frame, tx, ty, tz, rx, ry, rz, sample.quality,
                sample.frame_time_ms, sample.table_position, sample.flags)


def decode_tcl_packet(data: bytes, packet_format: str = "windows-le") -> Pose:
    """Compose raw parsing and TCL-to-animation coordinate conversion."""
    return tcl_to_pose(parse_tcl_packet(data, packet_format))
