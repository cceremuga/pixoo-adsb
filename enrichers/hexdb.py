import logging
from typing import Optional, Tuple

import requests

from enrichers.base import EnrichmentSource, _airports

log = logging.getLogger(__name__)

_URL = "https://hexdb.io/api/v1/route/icao/{callsign}"


class HexDBSource(EnrichmentSource):
    def __init__(self, options: dict):
        self._timeout = options.get("timeout", 8)
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "pixoo-adsb/1.0"

    @property
    def name(self) -> str:
        return "hexdb"

    def get_route(self, callsign: str) -> Optional[Tuple[str, str]]:
        url = _URL.format(callsign=callsign)
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
