import datetime
import logging
from typing import Optional, Tuple

import requests

from enrichers.base import EnrichmentSource, _airports, _icao_to_display

log = logging.getLogger(__name__)

_BASE = "https://prod.api.market/api/v1/aedbx/aerodatabox"
_URL = _BASE + "/flights/callsign/{callsign}/{date}"


class AeroDataBoxSource(EnrichmentSource):
    def __init__(self, options: dict):
        self._key = options.get("api_key", "")
        self._timeout = options.get("timeout", 8)
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "pixoo-adsb/1.0"

    @property
    def name(self) -> str:
        return "aerodatabox"

    def get_route(self, callsign: str) -> Optional[Tuple[str, str]]:
        if not self._key:
            return None
        today = datetime.date.today()
        for date in (today, today - datetime.timedelta(days=1)):
            result = self._fetch(callsign, date.isoformat())
            if result:
                return result
        return None

    def _fetch(self, callsign: str, date: str) -> Optional[Tuple[str, str]]:
        url = _URL.format(callsign=callsign, date=date)
        log.debug("AeroDataBox req: %s", url)
        try:
            resp = self._session.get(
                url,
                headers={"x-api-market-key": self._key},
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
