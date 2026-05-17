import functools
import logging
import os
import time
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from aircraft import Aircraft
from config import Config, DisplayConfig
from pixoo_client import Pixoo64

log = logging.getLogger(__name__)

W = H = 64
_FORCE_REFRESH_SECS = 60


_FONT_PATH = os.path.join(
    os.path.dirname(__file__), "fonts", "JetBrainsMonoNL-Regular.ttf"
)


@functools.lru_cache(maxsize=8)
def _font(size: int) -> ImageFont.ImageFont:
    if os.path.exists(_FONT_PATH):
        try:
            return ImageFont.truetype(_FONT_PATH, size)
        except OSError as e:
            log.warning("Failed to load font %s: %s", _FONT_PATH, e)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _draw_text_centre(draw, text, y, font, colour):
    bb = draw.textbbox((0, 0), text, font=font)
    x = max(0, (W - (bb[2] - bb[0])) // 2)
    draw.text((x, y), text, fill=colour, font=font)


def _sep(draw, y, colour):
    draw.line([(0, y), (W - 1, y)], fill=colour)


class Renderer:
    def __init__(self, cfg: Config):
        self._pixoo = Pixoo64(cfg.pixoo.host, brightness=cfg.pixoo.brightness)
        self._colors = cfg.display
        self._last_fingerprint: Optional[str] = None
        self._last_push_time: float = 0.0

    def render(
        self, aircraft: Aircraft, logo: Image.Image, origin: str, destination: str
    ) -> bool:
        fp = _fingerprint(aircraft, origin, destination)
        stale = (time.monotonic() - self._last_push_time) >= _FORCE_REFRESH_SECS
        if fp == self._last_fingerprint and not stale:
            return False
        self._push(compose(aircraft, logo, origin, destination, self._colors))
        self._last_fingerprint = fp
        self._last_push_time = time.monotonic()
        return True

    def show_message(self, line1: str, line2: str, colour=(180, 50, 50)) -> None:
        img = Image.new("RGB", (W, H), self._colors.color_background)
        d = ImageDraw.Draw(img)
        _draw_text_centre(d, line1, 22, _font(13), colour)
        _draw_text_centre(d, line2, 37, _font(13), colour)
        self._push(img)
        self._last_fingerprint = None
        self._last_push_time = time.monotonic()

    def _push(self, img: Image.Image) -> None:
        try:
            self._pixoo.push(img)
        except Exception as e:
            log.error("Pixoo push failed: %s", e)


def compose(
    aircraft: Aircraft, logo: Image.Image, origin: str, destination: str, colors=None
) -> Image.Image:
    c = colors if colors is not None else DisplayConfig()

    img = Image.new("RGB", (W, H), c.color_background)
    d = ImageDraw.Draw(img)

    f10 = _font(10)
    f8 = _font(8)

    img.paste(logo.resize((16, 16), Image.NEAREST), (2, 4))

    flight = aircraft.display_name
    avail = W - 19
    while flight and d.textbbox((0, 0), flight, font=f10)[2] > avail:
        flight = flight[:-1]
    d.text((21, -1), flight, fill=c.color_flight, font=f10)

    if aircraft.distance_km:
        d.text(
            (21, 12),
            _dist_str(aircraft.distance_km, c.distance_unit),
            fill=c.color_flight,
            font=f8,
        )

    _sep(d, 23, c.color_separator)

    if origin != "???" and destination != "???":
        route = f"{origin} - {destination}"
    elif origin != "???":
        route = f"{origin} - ???"
    elif destination != "???":
        route = f"??? - {destination}"
    else:
        route = aircraft.registration or aircraft.hex.upper()
    d.text((2, 24), route.upper(), fill=c.color_route, font=f10)

    _sep(d, 38, c.color_separator)

    alt_str = _alt_str(aircraft.altitude_ft, c.fl_transition_ft)
    spd_str = f"{aircraft.speed_kts} KT" if aircraft.speed_kts is not None else "-- KT"
    d.text((2, 38), alt_str, fill=c.color_data, font=f10)
    d.text((2, 51), spd_str, fill=c.color_data, font=f10)

    return img


def _dist_str(distance_km: float, unit: str) -> str:
    if unit == "mi":
        return f"{distance_km * 0.621371:.0f}MI"
    return f"{distance_km:.0f}KM"


def _alt_str(altitude_ft: Optional[int], fl_transition_ft: int) -> str:
    if altitude_ft is None:
        return "--- FT"
    if altitude_ft >= fl_transition_ft:
        return f"FL{altitude_ft // 100}"
    return f"{altitude_ft:,} FT"


def _fingerprint(aircraft: Aircraft, origin: str, destination: str) -> str:
    return "|".join(
        [
            aircraft.hex,
            aircraft.flight,
            str(aircraft.altitude_ft),
            str(aircraft.speed_kts),
            origin,
            destination,
        ]
    )
