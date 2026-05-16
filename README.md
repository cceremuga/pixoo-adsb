# Pixoo ADSB

A real-time ADS-B dashboard for the [Divoom Pixoo64](https://www.divoom.com/products/pixoo-64) that tracks the nearest aircraft from a local [dump1090](https://github.com/flightaware/dump1090) receiver and displays live flight data on the 64×64 LED matrix. Route data is enriched automatically via free public APIs, with airline logos fetched and cached from FlightAware's CDN.

<img src="sample.png" width="450">

## Requirements

- Python 3.10+
- A dump1090 receiver on your local network
- A Divoom Pixoo64 on your local network

## Setup

```bash
git clone https://github.com/yourname/pixoo-adsb.git
cd pixoo-adsb
cp sample.config.json config.json
# edit config.json with your receiver and Pixoo64 IPs
bash setup.sh
source venv/bin/activate
python main.py
```

## Configuration

All settings live in `config.json`. See `sample.config.json` for a fully annotated reference.

| Section | Key | Description |
|---|---|---|
| `adsb` | `host` | IP of your dump1090 host |
| `adsb` | `receiver_lat` / `receiver_lon` | Your antenna location (required for distance) |
| `adsb` | `poll_interval` | Seconds between polls (default: 10) |
| `pixoo` | `host` | IP of your Pixoo64 |
| `pixoo` | `brightness` | 0–100 |
| `display` | `distance_unit` | `"km"` or `"mi"` |
| `display` | `fl_transition_ft` | Altitude above which FL notation is used (default: 18000) |
| `display` | `color_flight` | RGB array for flight number and distance |
| `display` | `color_route` | RGB array for origin/destination |
| `display` | `color_data` | RGB array for altitude and speed |
| `flight_data` | `enabled` | Toggle route enrichment on/off |

## Display Layout

```
┌────────────────────────────┐
│ [logo] FLIGHT#             │
│        DISTANCE            │
├────────────────────────────┤
│ ORIGIN - DEST / TAIL       │
├────────────────────────────┤
│ FL350 / 17,500 FT          │
│ 450 KT                     │
└────────────────────────────┘
```

When no route is found, the aircraft tail number is shown in place of origin/destination. At or above `fl_transition_ft`, altitude is displayed as a flight level (e.g. FL350) rather than feet.

## Route Enrichment

Routes are looked up automatically using two free, no-key-required APIs:

1. **[HexDB](https://hexdb.io)** — primary
1. **[AdsbDB](https://adsbdb.com)** — fallback

Results are cached to disk for the duration configured in `flight_data.cache_ttl_seconds`.

______________________________________________________________________

## Release Notes

### v1.0.0 — Initial Release

First working release. Core features:

- Polls a local dump1090 receiver and selects the nearest aircraft by haversine distance
- Displays airline logo (fetched + cached from FlightAware CDN), flight number, tail number, distance, origin/destination route, altitude, and speed
- FL notation above configurable transition altitude
- Distance in km or miles
- Route enrichment via HexDB and AdsbDB (no API key required)
- All display colors configurable via `config.json`
- 60-second force-refresh keeps the Pixoo64 from reverting to its idle screen
- Graceful degradation: shows tail number when route is unknown, grey placeholder when no logo is available, ADSB OFFLINE message when the receiver is unreachable

______________________________________________________________________

## Fonts

Display text is rendered using [JetBrains Mono NL](https://www.jetbrains.com/legalnotice/fonts/) by JetBrains.
Licensed under the [SIL Open Font License 1.1](fonts/OFL.txt).
Copyright 2020 The JetBrains Mono Project Authors.

______________________________________________________________________

## A Note on Development

Portions of this project were written with the assistance of agentic LLM tooling (Claude Code). All generated code was reviewed, tested, and validated by a professional software engineer before being committed. The architecture, feature decisions, and final implementation are the author's own.

## License

Apache 2.0 — see [LICENSE](LICENSE).
