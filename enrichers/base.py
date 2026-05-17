from abc import ABC, abstractmethod
from typing import Optional, Tuple

import airportsdata

_AIRPORTS = airportsdata.load()


class EnrichmentSource(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def get_route(self, callsign: str) -> Optional[Tuple[str, str]]: ...


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


def _airports(origin: str, dest: str) -> Optional[Tuple[str, str]]:
    o = _icao_to_display(origin)
    d = _icao_to_display(dest)
    return (o, d) if o != "???" or d != "???" else None
