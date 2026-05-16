#!/usr/bin/env python3
import argparse
import logging
import sys
import time

from PIL import Image

import config as cfg_mod
from adsb_client import ADSBClient
from flight_enricher import FlightEnricher
from logo_manager import LogoManager
from renderer import Renderer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pixoo64 ADSB dashboard")
    p.add_argument("--config", default="config.json")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    cfg = cfg_mod.load(args.config)
    adsb = ADSBClient(cfg)
    enricher = FlightEnricher(cfg)
    logos = LogoManager(cfg)
    renderer = Renderer(cfg)

    log.info(
        "Starting — polling every %ds | ADSB %s | Pixoo %s",
        cfg.adsb.poll_interval,
        cfg.adsb.host,
        cfg.pixoo.host,
    )

    consecutive_failures = 0

    while True:
        try:
            aircraft = adsb.fetch_nearest()
        except Exception as e:
            log.error("Unexpected fetch error: %s", e)
            aircraft = None

        if aircraft is None:
            consecutive_failures += 1
            if consecutive_failures == 1:
                log.warning("No aircraft data")
                try:
                    renderer.show_message("ADSB", "OFFLINE")
                except Exception as e:
                    log.error("Renderer error: %s", e)
            time.sleep(cfg.adsb.poll_interval)
            continue

        consecutive_failures = 0
        log.info(
            "Nearest: %s  %.1fkm  alt=%s  spd=%s",
            aircraft.display_name,
            aircraft.distance_km,
            aircraft.altitude_ft,
            aircraft.speed_kts,
        )

        try:
            origin, destination = enricher.get_route(aircraft.hex, aircraft.flight)
        except Exception as e:
            log.debug("Route lookup error: %s", e)
            origin, destination = "???", "???"

        try:
            logo = logos.get(aircraft.flight)
        except Exception as e:
            log.debug("Logo error: %s", e)
            logo = Image.new("RGB", (16, 16), (60, 60, 60))

        try:
            updated = renderer.render(aircraft, logo, origin, destination)
            if updated:
                log.info("Display updated [%s -> %s]", origin, destination)
        except Exception as e:
            log.error("Render error: %s", e)

        time.sleep(cfg.adsb.poll_interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Stopped.")
        sys.exit(0)
