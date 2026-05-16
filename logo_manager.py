import hashlib
import logging
import os
import re
from io import BytesIO
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont

from config import Config

log = logging.getLogger(__name__)

LOGO_SIZE = (16, 16)

_AIRLINE_COLOURS: dict[str, tuple] = {
    "AAL": (153, 0, 0, 255, 255, 255),
    "DAL": (0, 53, 128, 255, 255, 255),
    "UAL": (0, 56, 101, 255, 204, 0),
    "SWA": (221, 68, 0, 255, 200, 0),
    "BAW": (0, 33, 71, 255, 255, 255),
    "DLH": (0, 100, 200, 255, 204, 0),
    "AFR": (0, 36, 125, 255, 255, 255),
    "RYR": (0, 0, 0, 255, 204, 0),
    "EZY": (255, 102, 0, 255, 255, 255),
    "UAE": (220, 0, 0, 255, 255, 255),
    "QFA": (227, 20, 30, 255, 255, 255),
    "SKW": (0, 82, 147, 255, 255, 255),
    "ASA": (0, 100, 200, 255, 255, 255),
    "JBU": (0, 100, 200, 255, 255, 255),
    "FFT": (128, 0, 128, 255, 255, 255),
    "NKS": (255, 200, 0, 0, 0, 0),
}

_FETCH_URLS = [
    "https://www.flightaware.com/images/airline_logos/90p/{icao3}.png",
]


class LogoManager:
    def __init__(self, cfg: Config):
        self._cache_dir = cfg.logos.cache_dir
        self._timeout = cfg.logos.fetch_timeout
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "pixoo-adsb/1.0"
        os.makedirs(self._cache_dir, exist_ok=True)

    def get(self, callsign: str) -> Image.Image:
        icao3 = _icao3(callsign)
        if not icao3:
            return _placeholder("?", (80, 80, 80))

        cache_path = os.path.join(self._cache_dir, f"{icao3}.png")
        if os.path.exists(cache_path):
            try:
                return (
                    Image.open(cache_path)
                    .convert("RGB")
                    .resize(LOGO_SIZE, Image.LANCZOS)
                )
            except Exception:
                os.remove(cache_path)

        img = self._fetch_remote(icao3)
        if img:
            try:
                img.save(cache_path)
            except OSError:
                pass
            return img

        return _coloured_placeholder(icao3)

    def _fetch_remote(self, icao3: str) -> Optional[Image.Image]:
        for url_tpl in _FETCH_URLS:
            url = url_tpl.format(icao3=icao3)
            try:
                resp = self._session.get(url, timeout=self._timeout)
                if resp.status_code != 200:
                    continue
                img = Image.open(BytesIO(resp.content)).convert("RGBA")
                bg = Image.new("RGB", img.size, (0, 0, 0))
                bg.paste(img, mask=img.split()[3])
                return bg.resize(LOGO_SIZE, Image.LANCZOS)
            except Exception as e:
                log.debug("logo fetch failed (%s): %s", url, e)
        return None


def _icao3(callsign: str) -> str:
    m = re.match(r"[A-Z]{3}", callsign.upper())
    return m.group() if m else ""


def _coloured_placeholder(icao3: str) -> Image.Image:
    colours = _AIRLINE_COLOURS.get(icao3)
    if colours:
        bg, fg = colours[:3], colours[3:]
    else:
        h = int(hashlib.md5(icao3.encode()).hexdigest()[:6], 16)
        r, g, b = (h >> 16) & 0xFF, (h >> 8) & 0xFF, h & 0xFF
        bg = (max(30, r % 200), max(30, g % 200), max(30, b % 200))
        fg = (255, 255, 255)
    return _placeholder(icao3[:2], bg, fg)


def _placeholder(text: str, bg: tuple, fg: tuple = (255, 255, 255)) -> Image.Image:
    img = Image.new("RGB", LOGO_SIZE, bg)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (LOGO_SIZE[0] - (bbox[2] - bbox[0])) // 2 - bbox[0]
        y = (LOGO_SIZE[1] - (bbox[3] - bbox[1])) // 2 - bbox[1]
        draw.text((x, y), text, fill=fg, font=font)
    except Exception:
        pass
    return img
