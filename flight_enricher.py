import logging
from typing import Tuple

import diskcache

import enrichers as enricher_registry
from config import Config

log = logging.getLogger(__name__)


class FlightEnricher:
    def __init__(self, cfg: Config):
        fd = cfg.flight_data
        self._enabled = fd.enabled
        self._cache = diskcache.Cache(fd.cache_dir)
        self._ttl = fd.cache_ttl_seconds
        self._sources = []
        for sc in fd.sources:
            if not sc.enabled:
                continue
            cls = enricher_registry.REGISTRY.get(sc.type)
            if cls is None:
                log.warning("Unknown enrichment source: %s", sc.type)
                continue
            self._sources.append(cls(sc.options))
            log.debug("Loaded enrichment source: %s", sc.type)

    def get_route(self, hex_code: str, callsign: str = "") -> Tuple[str, str]:
        if not self._enabled or not callsign:
            return "???", "???"

        cached = self._cache.get(callsign)
        if cached is not None:
            if cached == ("???", "???"):
                log.debug("get_route %s (hex=%s): cached miss", callsign, hex_code)
            else:
                log.debug(
                    "get_route %s (hex=%s): cache hit %s", callsign, hex_code, cached
                )
            return cached

        log.debug(
            "get_route %s (hex=%s): cache miss, querying sources", callsign, hex_code
        )

        for source in self._sources:
            result = source.get_route(callsign)
            if result:
                log.debug(
                    "Route for %s found via %s: %s", callsign, source.name, result
                )
                self._cache.set(callsign, result, expire=self._ttl)
                return result

        log.debug("get_route %s: all sources exhausted, caching miss", callsign)
        self._cache.set(callsign, ("???", "???"), expire=self._ttl)
        return "???", "???"
