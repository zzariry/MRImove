"""Input transport separated from tracker-specific data conversion."""

from importlib import import_module
import math
import socket
from typing import Callable, Protocol
from .pose import Pose

Decoder = Callable[[bytes], Pose]


def validate_pose(pose: Pose) -> Pose:
    if not isinstance(pose, Pose):
        raise TypeError("A tracker adapter must return tcl_animation.pose.Pose")
    if not all(math.isfinite(value) for value in
               (pose.tx, pose.ty, pose.tz, pose.rx, pose.ry, pose.rz,
                pose.quality, pose.frame_time_ms)):
        raise ValueError("Non-finite converted pose")
    return pose


def load_decoder(spec: str) -> Decoder:
    """Load an installed/importable module:function, without changing sys.path."""
    module, separator, name = spec.partition(":")
    if not separator or not module or not name:
        raise ValueError("Adapter must be specified as module:function")
    decoder = getattr(import_module(module), name)
    if not callable(decoder):
        raise TypeError("Adapter is not callable")
    return decoder


class PoseSource(Protocol):
    """Custom sources may use UDP, serial, an SDK, replay, etc.

    poll() must return promptly, with an empty sequence when no data are ready.
    The viewer owns the context and closes it when exiting.
    """
    def __enter__(self) -> "PoseSource": ...
    def __exit__(self, exc_type, exc, traceback): ...
    def poll(self) -> list[Pose]: ...


class UDPSource:
    def __init__(self, decoder: Decoder, host="0.0.0.0", port=6000):
        self.decoder, self.host, self.port = decoder, host, port
        self.socket = None

    def __enter__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.socket.bind((self.host, self.port))
            self.socket.setblocking(False)
        except BaseException:
            self.socket.close()
            raise
        return self

    def __exit__(self, *args):
        self.socket.close()

    def poll(self) -> list[Pose]:
        poses = []
        for _ in range(256):
            try:
                data, _ = self.socket.recvfrom(65535)
            except BlockingIOError:
                break
            try:
                poses.append(validate_pose(self.decoder(data)))
            except ValueError:
                # Decoders signal malformed/unusable samples with ValueError.
                continue
        return poses
