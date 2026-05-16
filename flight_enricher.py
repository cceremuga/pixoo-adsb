import datetime
import logging
from typing import Optional, Tuple

import airportsdata
import diskcache
import requests

from config import Config

_AIRPORTS = airportsdata.load()

log = logging.getLogger(__name__)

_AERODATABOX_URL = "https://prod.api.market/api/v1/aedbx/aerodatabox/flights/callsign/{callsign}/{date}"
_HEXDB_URL = "https://hexdb.io/api/v1/route/icao/{callsign}"
_ADSBDB_URL = "https://api.adsbdb.com/v0/callsign/{callsign}"


class FlightEnricher:
    def __init__(self, cfg: Config):
        fd = cfg.flight_data
        self._enabled = fd.enabled
        self._cache = diskcache.Cache(fd.cache_dir)
        self._ttl = fd.cache_ttl_seconds
        self._aerodatabox_key = fd.aerodatabox_key or None
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "pixoo-adsb/1.0"
        self._timeout = 8

    def get_route(self, hex_code: str, callsign: str = "") -> Tuple[str, str]:
        if not self._enabled or not callsign:
            return "???", "???"

        cached = self._cache.get(callsign)
        log.debug(
            "get_route %s (hex=%s): %s",
            callsign,
            hex_code,
            (
                f"cache hit {cached}"
                if cached is not None
                else "cache miss, querying APIs"
            ),
        )
        if cached is not None:
            return cached

        result = (
            (self._aerodatabox(callsign) if self._aerodatabox_key else None)
            or self._hexdb(callsign)
            or self._adsbdb(callsign)
        )
        if result:
            self._cache.set(callsign, result, expire=self._ttl)
        return result or ("???", "???")

    def _aerodatabox(self, callsign: str) -> Optional[Tuple[str, str]]:
        today = datetime.date.today()
        for date in (today, today - datetime.timedelta(days=1)):
            result = self._aerodatabox_for_date(callsign, date.isoformat())
            if result:
                return result
        return None

    def _aerodatabox_for_date(
        self, callsign: str, date: str
    ) -> Optional[Tuple[str, str]]:
        url = _AERODATABOX_URL.format(callsign=callsign, date=date)
        log.debug("AeroDataBox req: %s", url)
        try:
            resp = self._session.get(
                url,
                headers={"x-api-market-key": self._aerodatabox_key},
                timeout=self._timeout,
            )
            log.debug(
                "AeroDataBox resp: status=%s body=%s", resp.status_code, resp.text[:500]
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data:
                return None
            flight = data[0] if isinstance(data, list) else data
            dep = flight.get("departure", {}).get("airport", {})
            arr = flight.get("arrival", {}).get("airport", {})
            o = dep.get("iata") or _icao_to_display(dep.get("icao", ""))
            d = arr.get("iata") or _icao_to_display(arr.get("icao", ""))
            result = _airports(o or "???", d or "???")
            log.debug("AeroDataBox result for %s on %s: %s", callsign, date, result)
            return result
        except Exception as e:
            log.debug("AeroDataBox failed for %s on %s: %s", callsign, date, e)
            return None

    def _hexdb(self, callsign: str) -> Optional[Tuple[str, str]]:
        url = _HEXDB_URL.format(callsign=callsign)
        log.debug("HexDB req: %s", url)
        try:
            resp = self._session.get(url, timeout=self._timeout)
            log.debug(
                "HexDB resp: status=%s body=%s", resp.status_code, resp.text[:500]
            )
            if resp.status_code != 200:
                return None
            route = resp.json().get("route", "")
            if "-" not in route:
                return None
            icao_origin, icao_dest = route.split("-", 1)
            result = _airports(icao_origin, icao_dest)
            log.debug("HexDB result: %s", result)
            return result
        except Exception as e:
            log.debug("HexDB failed for %s: %s", callsign, e)
            return None

    def _adsbdb(self, callsign: str) -> Optional[Tuple[str, str]]:
        url = _ADSBDB_URL.format(callsign=callsign)
        log.debug("AdsbDB req: %s", url)
        try:
            resp = self._session.get(url, timeout=self._timeout)
            log.debug(
                "AdsbDB resp: status=%s body=%s", resp.status_code, resp.text[:500]
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
            result = _airports(o or "???", d or "???")
            log.debug("AdsbDB result: %s", result)
            return result
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
    ap = _AIRPORTS.get(code)
    if ap and ap.get("iata"):
        return ap["iata"]
    if len(code) == 4 and code[0] in ("K", "C"):
        return code[1:]
    return code[:3] if len(code) >= 3 else code
