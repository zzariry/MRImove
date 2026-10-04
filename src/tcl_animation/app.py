"""Pygame UI and command-line entry point."""

import argparse
import csv
from dataclasses import asdict
import logging
import math
import time
from contextlib import ExitStack

from .protocols import load_protocol, target_at


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Expected a positive finite number")
    return number


def parser():
    result = argparse.ArgumentParser(description="Timed target and streamed head-pose feedback")
    result.add_argument("--protocol", default="Trial")
    result.add_argument("--protocol-file", help="JSON array overriding the built-in protocol")
    result.add_argument("--demo", action="store_true", help="Synthetic pose; no UDP input")
    result.add_argument("--translation", action="store_true", help="Use translation and force reference target")
    result.add_argument("--recenter", action="store_true", help="Center feedback on first valid pose")
    result.add_argument("--host", default="0.0.0.0", help="UDP bind address")
    result.add_argument("--port", type=int, default=6000)
    result.add_argument("--packet-format", choices=["windows-le", "native"], default="windows-le")
    result.add_argument("--adapter", help="Custom UDP decoder as module:function; defaults to TCL")
    result.add_argument("--scale", type=positive, default=30, help="Pixels per degree or tracker translation unit")
    result.add_argument("--fps", type=positive, default=60)
    result.add_argument("--duration", type=positive, help="Stop after this many seconds")
    result.add_argument("--fullscreen", action="store_true")
    result.add_argument("--display", type=int, default=0)
    result.add_argument("--log", help="Create a new CSV pose log; existing files are protected")
    return result


def main(argv=None, *, source=None):
    """Run the viewer; optionally supply a context-managed PoseSource."""
    command = parser()
    args = command.parse_args(argv)
    if not 0 <= args.port <= 65535 or args.display < 0:
        command.error("Invalid port or display index")
    try:
        movements = load_protocol("ref" if args.translation else args.protocol,
                                  None if args.translation else args.protocol_file)
    except (ValueError, OSError, KeyError, TypeError) as error:
        command.error(str(error))
    import pygame
    from .pose import Feedback, Pose
    from .adapters.tcl import decode_tcl_packet
    from .sources import UDPSource, load_decoder, validate_pose
    from functools import partial

    if source is not None and (args.demo or args.adapter):
        command.error("An injected source cannot be combined with --demo or --adapter")
    try:
        decoder = load_decoder(args.adapter) if args.adapter else partial(decode_tcl_packet, packet_format=args.packet_format)
    except (ImportError, AttributeError, ValueError, TypeError) as error:
        command.error(f"Cannot load adapter: {error}")
    source_label = "demo" if args.demo else ("custom-source" if source is not None else (args.adapter or "tcl"))

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    feedback = Feedback(args.translation, args.recenter or args.protocol in ("RL_8d4d", "UD_8d4d"))
    pygame.init()
    try:
        with ExitStack() as stack:
            receiver = None
            if not args.demo:
                receiver = stack.enter_context(source if source is not None else UDPSource(decoder, args.host, args.port))
            writer = None
            if args.log:
                output = stack.enter_context(open(args.log, "x", newline="", encoding="utf-8"))
                writer = csv.DictWriter(output, fieldnames=["elapsed_s", "source", *Pose.__dataclass_fields__])
                writer.writeheader()
            screen = pygame.display.set_mode((0, 0) if args.fullscreen else (1024, 768),
                                              pygame.FULLSCREEN if args.fullscreen else 0,
                                              display=args.display)
            pygame.display.set_caption("TCL animation — head pose feedback")
            font = pygame.font.Font(None, 32)
            clock = pygame.time.Clock()
            center_x, center_y = screen.get_rect().center
            start = time.monotonic()
            last_received = None
            values = (0, 0, 0)
            running = True
            while running:
                elapsed = time.monotonic() - start
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_SPACE)):
                        running = False
                if not running or (args.duration and elapsed >= args.duration):
                    break
                poses = []
                if args.demo:
                    poses.append(Pose(int(elapsed * args.fps), 0, 0, 0,
                                      3 * math.sin(elapsed / 2), 8 * math.sin(elapsed / 3),
                                      3 * math.cos(elapsed / 2), 1, elapsed * 1000, 0, 0))
                else:
                    poses = receiver.poll()
                for pose in poses:
                    validate_pose(pose)
                    values = feedback.update(pose)
                    last_received = elapsed
                    if writer:
                        writer.writerow({"elapsed_s": elapsed, "source": source_label, **asdict(pose)})
                dx, dy, warning = target_at(movements, elapsed, args.scale)
                screen.fill((255, 255, 255))
                pygame.draw.rect(screen, (0, 0, 255), (round(center_x + dx), round(center_y + dy + 20), 60, 60), 10)
                if last_received is not None:
                    px, py = round(center_x + 3 + values[0] * args.scale), round(center_y + 23 + values[1] * args.scale)
                    border = pygame.draw.rect(screen, (0, 0, 0), (px, py, 55, 55), 4)
                    square = pygame.Surface((50, 50), pygame.SRCALPHA)
                    square.fill((255, 0, 0))
                    rotated = pygame.transform.rotate(square, values[2])
                    screen.blit(rotated, rotated.get_rect(center=border.center))
                status = "DEMO — synthetic data" if args.demo else source_label
                if last_received is None or elapsed - last_received > 3:
                    status += " — waiting for tracker"
                screen.blit(font.render(status + " | Esc / Space: quit", True, (0, 0, 0)), (20, 20))
                if warning:
                    message = font.render("Movement within 5 seconds", True, (255, 255, 0), (255, 0, 0))
                    screen.blit(message, message.get_rect(center=(center_x, 120)))
                pygame.display.flip()
                clock.tick(args.fps)
    finally:
        pygame.quit()
