import logging
from typing import Optional, Tuple

import diskcache
import requests

from config import Config

log = logging.getLogger(__name__)

_HEXDB_URL = "https://hexdb.io/api/v1/route/icao/{callsign}"
_ADSBDB_URL = "https://api.adsbdb.com/v0/callsign/{callsign}"


class FlightEnricher:
    def __init__(self, cfg: Config):
        fd = cfg.flight_data
        self._enabled = fd.enabled
        self._cache = diskcache.Cache(fd.cache_dir)
        self._ttl = fd.cache_ttl_seconds
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "pixoo-adsb/1.0"
        self._timeout = 8

    def get_route(self, hex_code: str, callsign: str = "") -> Tuple[str, str]:
        if not self._enabled or not callsign:
            return "???", "???"

        cached = self._cache.get(callsign)
        if cached is not None:
            return cached

        result = self._hexdb(callsign) or self._adsbdb(callsign)
        if result:
            self._cache.set(callsign, result, expire=self._ttl)
        return result or ("???", "???")

    def _hexdb(self, callsign: str) -> Optional[Tuple[str, str]]:
        try:
            resp = self._session.get(
                _HEXDB_URL.format(callsign=callsign), timeout=self._timeout
            )
            if resp.status_code != 200:
                return None
            route = resp.json().get("route", "")
            if "-" not in route:
                return None
            icao_origin, icao_dest = route.split("-", 1)
            return _airports(icao_origin, icao_dest)
        except Exception as e:
            log.debug("HexDB failed for %s: %s", callsign, e)
            return None

    def _adsbdb(self, callsign: str) -> Optional[Tuple[str, str]]:
        try:
            resp = self._session.get(
                _ADSBDB_URL.format(callsign=callsign), timeout=self._timeout
            )
            if resp.status_code != 200:
                return None
            fr = resp.json().get("response", {}).get("flightroute", {})
            if not fr:
                return None
            origin = fr.get("origin", {})
            dest = fr.get("destination", {})
            o = origin.get("iata_code") or _icao_to_display(origin.get("icao_code", ""))
            d = dest.get("iata_code") or _icao_to_display(dest.get("icao_code", ""))
            return _airports(o or "???", d or "???")
        except Exception as e:
            log.debug("AdsbDB failed for %s: %s", callsign, e)
            return None


def _airports(origin: str, dest: str) -> Optional[Tuple[str, str]]:
    o = _icao_to_display(origin)
    d = _icao_to_display(dest)
    return (o, d) if o != "???" or d != "???" else None


def _icao_to_display(code: str) -> str:
    if not code or code == "???":
        return "???"
    code = code.upper().strip()
    if len(code) == 4 and code[0] == "K":
        return code[1:]
    return code[:3] if len(code) >= 3 else code
