import logging
from typing import Optional, Tuple

import requests

from enrichers.base import EnrichmentSource, _airports, _icao_to_display

log = logging.getLogger(__name__)

_URL = "https://aeroapi.flightaware.com/aeroapi/flights/{ident}"


class AeroAPISource(EnrichmentSource):
    def __init__(self, options: dict):
        self._key = options.get("api_key", "")
        self._timeout = options.get("timeout", 8)
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "pixoo-adsb/1.0"

    @property
    def name(self) -> str:
        return "aeroapi"

    def get_route(self, callsign: str) -> Optional[Tuple[str, str]]:
        if not self._key:
            return None
        url = _URL.format(ident=callsign)
        log.debug("AeroAPI req: %s", url)
        try:
            resp = self._session.get(
                url,
                headers={"x-apikey": self._key},
                timeout=self._timeout,
            )
            log.debug(
                "AeroAPI resp: status=%s body=%s", resp.status_code, resp.text[:500]
            )
            if resp.status_code != 200:
                return None
            flights = resp.json().get("flights", [])
            for flight in flights:
                origin = flight.get("origin") or {}
                dest = flight.get("destination") or {}
                o = origin.get("code_iata") or _icao_to_display(
                    origin.get("code_icao", "")
                )
                d = dest.get("code_iata") or _icao_to_display(dest.get("code_icao", ""))
                result = _airports(o or "???", d or "???")
                if result:
                    log.debug("AeroAPI result for %s: %s", callsign, result)
                    return result
            return None
        except Exception as e:
            log.debug("AeroAPI failed for %s: %s", callsign, e)
            return None
