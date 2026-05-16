import logging
from typing import Optional

import requests
from haversine import Unit, haversine

from aircraft import Aircraft
from config import Config

log = logging.getLogger(__name__)


class ADSBClient:
    def __init__(self, cfg: Config):
        self._url = cfg.adsb_url
        self._receiver = (cfg.adsb.receiver_lat, cfg.adsb.receiver_lon)
        self._session = requests.Session()
        self._timeout = 8

    def fetch_nearest(self) -> Optional[Aircraft]:
        try:
            resp = self._session.get(self._url, timeout=self._timeout)
            resp.raise_for_status()
            raw_list = resp.json().get("aircraft", [])
        except requests.RequestException as e:
            log.warning("dump1090 fetch failed: %s", e)
            return None
        except ValueError as e:
            log.warning("dump1090 JSON parse error: %s", e)
            return None

        candidates = []
        for raw in raw_list:
            ac = Aircraft.from_dump1090(raw)
            if ac.lat is None or ac.lon is None or ac.seen_pos > 60:
                continue
            ac.distance_km = round(
                haversine(self._receiver, (ac.lat, ac.lon), unit=Unit.KILOMETERS), 1
            )
            candidates.append(ac)

        return min(candidates, key=lambda a: a.distance_km) if candidates else None
