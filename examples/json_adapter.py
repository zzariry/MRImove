"""Example for an equivalent tracker sending UTF-8 JSON over UDP.

Values in this example must ALREADY be in the animation reference frame.
For your tracker, replace the mapping with its calibration and unit conversion.
"""

import json
from tcl_animation.pose import Pose


def decode_pose(data: bytes) -> Pose:
    """Malformed samples raise ValueError; programming errors should propagate."""
    try:
        fields = json.loads(data.decode("utf-8"))
        return Pose(frame=int(fields.get("frame", 0)),
                    tx=float(fields["tx"]), ty=float(fields["ty"]), tz=float(fields["tz"]),
                    rx=float(fields["rx"]), ry=float(fields["ry"]), rz=float(fields["rz"]),
                    quality=float(fields.get("quality", 1)),
                    frame_time_ms=float(fields.get("frame_time_ms", 0)))
    except (UnicodeError, KeyError, TypeError, AttributeError, OverflowError, ValueError) as error:
        raise ValueError("Invalid JSON pose sample") from error
