from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class AdsbConfig:
    host: str = "192.168.1.100"
    port: int = 8080
    path: str = "/data/aircraft.json"
    poll_interval: int = 10
    receiver_lat: float = 0.0
    receiver_lon: float = 0.0


@dataclass
class PixooConfig:
    host: str = "192.168.1.200"
    brightness: int = 100


@dataclass
class LogosConfig:
    cache_dir: str = "cache/logos"
    fetch_timeout: int = 5


@dataclass
class DisplayConfig:
    color_flight: tuple = (66, 122, 181)
    color_route: tuple = (247, 221, 125)
    color_data: tuple = (64, 106, 175)
    fl_transition_ft: int = 18000
    distance_unit: str = "km"


@dataclass
class FlightDataConfig:
    enabled: bool = True
    cache_dir: str = "cache/routes"
    cache_ttl_seconds: int = 3600


@dataclass
class Config:
    adsb: AdsbConfig = field(default_factory=AdsbConfig)
    pixoo: PixooConfig = field(default_factory=PixooConfig)
    logos: LogosConfig = field(default_factory=LogosConfig)
    flight_data: FlightDataConfig = field(default_factory=FlightDataConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)

    @property
    def adsb_url(self) -> str:
        return f"http://{self.adsb.host}:{self.adsb.port}{self.adsb.path}"


def load(path: str = "config.json") -> Config:
    defaults = Config()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        log.warning("%s not found, using defaults", path)
        return defaults

    def get(section: dict, key: str, default):
        return section.get(key, default)

    def color(section: dict, key: str, default: tuple) -> tuple:
        val = section.get(key)
        if isinstance(val, list) and len(val) == 3:
            return tuple(val)
        return default

    a = data.get("adsb", {})
    p = data.get("pixoo", {})
    lo = data.get("logos", {})
    fd = data.get("flight_data", {})
    di = data.get("display", {})
    d = defaults

    cfg = Config(
        adsb=AdsbConfig(
            host=get(a, "host", d.adsb.host),
            port=get(a, "port", d.adsb.port),
            path=get(a, "path", d.adsb.path),
            poll_interval=get(a, "poll_interval", d.adsb.poll_interval),
            receiver_lat=get(a, "receiver_lat", d.adsb.receiver_lat),
            receiver_lon=get(a, "receiver_lon", d.adsb.receiver_lon),
        ),
        pixoo=PixooConfig(
            host=get(p, "host", d.pixoo.host),
            brightness=get(p, "brightness", d.pixoo.brightness),
        ),
        logos=LogosConfig(
            cache_dir=get(lo, "cache_dir", d.logos.cache_dir),
            fetch_timeout=get(lo, "fetch_timeout", d.logos.fetch_timeout),
        ),
        flight_data=FlightDataConfig(
            enabled=get(fd, "enabled", d.flight_data.enabled),
            cache_dir=get(fd, "cache_dir", d.flight_data.cache_dir),
            cache_ttl_seconds=get(
                fd, "cache_ttl_seconds", d.flight_data.cache_ttl_seconds
            ),
        ),
        display=DisplayConfig(
            color_flight=color(di, "color_flight", d.display.color_flight),
            color_route=color(di, "color_route", d.display.color_route),
            color_data=color(di, "color_data", d.display.color_data),
            fl_transition_ft=get(di, "fl_transition_ft", d.display.fl_transition_ft),
            distance_unit=get(di, "distance_unit", d.display.distance_unit),
        ),
    )

    if cfg.adsb.receiver_lat == 0.0 and cfg.adsb.receiver_lon == 0.0:
        log.warning(
            "receiver_lat/receiver_lon are both 0.0 — "
            "distance calculations will be inaccurate. Set them in config.json."
        )

    return cfg
