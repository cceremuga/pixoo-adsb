import logging
from typing import Optional, Tuple

import requests

from enrichers.base import EnrichmentSource, _airports, _icao_to_display

log = logging.getLogger(__name__)

_URL = "https://api.adsbdb.com/v0/callsign/{callsign}"


class AdsbDBSource(EnrichmentSource):
    def __init__(self, options: dict):
        self._timeout = options.get("timeout", 8)
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "pixoo-adsb/1.0"

    @property
    def name(self) -> str:
        return "adsbdb"

    def get_route(self, callsign: str) -> Optional[Tuple[str, str]]:
        url = _URL.format(callsign=callsign)
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
