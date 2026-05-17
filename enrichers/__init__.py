from typing import Type

from enrichers.adsbdb import AdsbDBSource
from enrichers.aeroapi import AeroAPISource
from enrichers.aerodatabox import AeroDataBoxSource
from enrichers.base import EnrichmentSource
from enrichers.hexdb import HexDBSource

REGISTRY: dict[str, Type[EnrichmentSource]] = {
    "aeroapi": AeroAPISource,
    "aerodatabox": AeroDataBoxSource,
    "hexdb": HexDBSource,
    "adsbdb": AdsbDBSource,
}


def register(type_name: str, cls: Type[EnrichmentSource]) -> None:
    """Register a custom enrichment source so it can be referenced by name in config."""
    REGISTRY[type_name] = cls
