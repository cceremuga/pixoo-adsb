from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Aircraft:
    hex: str
    flight: str = ""
    registration: str = ""
    aircraft_type: str = ""
    category: str = "A0"
    lat: Optional[float] = None
    lon: Optional[float] = None
    altitude_ft: Optional[int] = None
    speed_kts: Optional[int] = None
    track: Optional[float] = None
    vert_rate: Optional[int] = None
    squawk: str = ""
    seen_pos: float = 999.0
    distance_km: float = 0.0

    @property
    def display_name(self) -> str:
        return self.flight or self.hex.upper()

    @classmethod
    def from_dump1090(cls, raw: dict) -> Aircraft:
        alt = raw.get("alt_baro") or raw.get("altitude")
        if isinstance(alt, str):
            alt = None
        speed = raw.get("gs") or raw.get("speed")
        return cls(
            hex=raw.get("hex", "").lower().strip(),
            flight=(raw.get("flight") or raw.get("callsign") or "").strip(),
            registration=(raw.get("r") or "").strip(),
            aircraft_type=(raw.get("t") or "").strip().upper(),
            category=(raw.get("category") or "A0").strip().upper(),
            lat=raw.get("lat"),
            lon=raw.get("lon"),
            altitude_ft=int(alt) if alt is not None else None,
            speed_kts=int(speed) if speed is not None else None,
            track=raw.get("track"),
            vert_rate=raw.get("baro_rate") or raw.get("geom_rate"),
            squawk=raw.get("squawk") or "",
            seen_pos=float(raw.get("seen_pos", 999)),
        )
