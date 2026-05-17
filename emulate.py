#!/usr/bin/env python3
import argparse
import logging
import sys
import threading
import time

import pygame
from PIL import Image

import config as cfg_mod
from adsb_client import ADSBClient
from flight_enricher import FlightEnricher
from logo_manager import LogoManager
from renderer import _fingerprint, compose

SCALE = 4
W = H = 64 * SCALE

log = logging.getLogger("emulate")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


class _FrameBuffer:
    def __init__(self):
        self._frame: Image.Image | None = None
        self._lock = threading.Lock()

    def put(self, frame: Image.Image) -> None:
        with self._lock:
            self._frame = frame

    def take(self) -> Image.Image | None:
        with self._lock:
            frame, self._frame = self._frame, None
            return frame


_FRAME_BUF = _FrameBuffer()


def _pil_to_surface(img: Image.Image) -> pygame.Surface:
    rgb = img.convert("RGB")
    return pygame.image.fromstring(rgb.tobytes(), rgb.size, "RGB")


def poll_loop(cfg) -> None:
    adsb = ADSBClient(cfg)
    enricher = FlightEnricher(cfg)
    logos = LogoManager(cfg)
    last_fp = None
    was_active = True

    while True:
        if not cfg.operating_hours.is_active():
            if was_active:
                log.info("Outside operating hours — going idle")
                was_active = False
            time.sleep(60)
            continue

        if not was_active:
            log.info("Operating hours resumed")
            was_active = True

        try:
            aircraft = adsb.fetch_nearest()
        except Exception as e:
            log.error("Fetch error: %s", e)
            aircraft = None

        if aircraft is None:
            time.sleep(cfg.adsb.poll_interval)
            continue

        log.info(
            "Nearest: %s  %.1fkm  alt=%s  spd=%s",
            aircraft.display_name,
            aircraft.distance_km,
            aircraft.altitude_ft,
            aircraft.speed_kts,
        )

        try:
            origin, dest = enricher.get_route(aircraft.hex, aircraft.flight)
        except Exception as e:
            log.debug("Route lookup: %s", e)
            origin, dest = "???", "???"

        try:
            logo = logos.get(aircraft.flight)
        except Exception as e:
            log.debug("Logo: %s", e)
            logo = Image.new("RGB", (16, 16), (60, 60, 60))

        fp = _fingerprint(aircraft, origin, dest)
        if fp != last_fp:
            _FRAME_BUF.put(compose(aircraft, logo, origin, dest, cfg.display))
            last_fp = fp
            log.info("Frame updated [%s -> %s]", origin, dest)

        time.sleep(cfg.adsb.poll_interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pixoo ADS-B local emulator")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    cfg = cfg_mod.load(args.config)

    t = threading.Thread(target=poll_loop, args=(cfg,), daemon=True)
    t.start()

    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Pixoo ADS-B Emulator")
    clock = pygame.time.Clock()

    screen.fill((10, 10, 10))
    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

        frame = _FRAME_BUF.take()
        if frame is not None:
            surface = _pil_to_surface(frame.resize((W, H), Image.NEAREST))
            screen.blit(surface, (0, 0))
            pygame.display.flip()

        clock.tick(30)


if __name__ == "__main__":
    main()
