"""Immutable, cumulative movement schedules extracted from the original script."""

from dataclasses import dataclass
from importlib.resources import files
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class Movement:
    name: str
    sec: float
    x: float
    y: float


def load_protocol(name: str = "Trial", path: str | None = None) -> tuple[Movement, ...]:
    """Load a built-in name or a JSON array of incremental movements."""
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    else:
        presets = json.loads(files(__package__).joinpath("protocols.json").read_text())
        if name not in presets:
            raise ValueError(f"Unknown protocol {name!r}; choose from {', '.join(presets)}")
        data = presets[name]
    movements = []
    previous = -1.0
    for item in data:
        movement = Movement(str(item["name"]), float(item["sec"]),
                            float(item["x"]), float(item["y"]))
        if not all(math.isfinite(v) for v in (movement.sec, movement.x, movement.y)):
            raise ValueError("Protocol values must be finite")
        if movement.sec < 0 or movement.sec < previous:
            raise ValueError("Movement times must be nonnegative and ordered")
        previous = movement.sec
        movements.append(movement)
    return tuple(movements)


def target_at(movements: tuple[Movement, ...], elapsed: float,
              scale: float = 30.0, warning_seconds: float = 5.0):
    """Return cumulative pixel offsets and whether an upcoming movement is imminent.

    This pure calculation can be repeated or replayed without mutating a protocol.
    """
    x = y = 0.0
    warning = False
    for movement in movements:
        if elapsed >= movement.sec:
            x += movement.x * scale
            y += movement.y * scale
        elif movement.sec - warning_seconds <= elapsed:
            warning = True
    return x, y, warning
