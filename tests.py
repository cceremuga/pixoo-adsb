import datetime
import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from aircraft import Aircraft
from config import Config, DisplayConfig, OperatingHoursConfig, load
from flight_enricher import FlightEnricher, _icao_to_display
from renderer import _alt_str, _dist_str, _fingerprint, compose


class TestAircraftFromDump1090(unittest.TestCase):
    def test_basic_fields(self):
        ac = Aircraft.from_dump1090(
            {
                "hex": "A835AF",
                "flight": "SWA1234 ",
                "r": "N8731Q",
                "t": "b737",
                "lat": 42.6,
                "lon": -73.8,
                "alt_baro": 35000,
                "gs": 450,
                "track": 270.0,
                "baro_rate": -64,
                "squawk": "1200",
                "seen_pos": 1.5,
            }
        )
        self.assertEqual(ac.hex, "a835af")
        self.assertEqual(ac.flight, "SWA1234")
        self.assertEqual(ac.registration, "N8731Q")
        self.assertEqual(ac.aircraft_type, "B737")
        self.assertEqual(ac.altitude_ft, 35000)
        self.assertEqual(ac.speed_kts, 450)
        self.assertEqual(ac.squawk, "1200")

    def test_ground_altitude_becomes_none(self):
        ac = Aircraft.from_dump1090({"hex": "abc", "alt_baro": "ground"})
        self.assertIsNone(ac.altitude_ft)

    def test_missing_optional_fields_default_to_none(self):
        ac = Aircraft.from_dump1090({"hex": "abc"})
        self.assertIsNone(ac.lat)
        self.assertIsNone(ac.lon)
        self.assertIsNone(ac.altitude_ft)
        self.assertIsNone(ac.speed_kts)

    def test_display_name_prefers_flight(self):
        ac = Aircraft.from_dump1090({"hex": "abc123", "flight": "DAL447"})
        self.assertEqual(ac.display_name, "DAL447")

    def test_display_name_falls_back_to_hex(self):
        ac = Aircraft.from_dump1090({"hex": "abc123"})
        self.assertEqual(ac.display_name, "ABC123")

    def test_alt_baro_takes_priority_over_altitude(self):
        ac = Aircraft.from_dump1090({"hex": "x", "alt_baro": 10000, "altitude": 9000})
        self.assertEqual(ac.altitude_ft, 10000)

    def test_gs_takes_priority_over_speed(self):
        ac = Aircraft.from_dump1090({"hex": "x", "gs": 400, "speed": 350})
        self.assertEqual(ac.speed_kts, 400)


class TestConfigLoad(unittest.TestCase):
    def test_defaults_when_file_missing(self):
        cfg = load("/nonexistent/path/config.json")
        self.assertIsInstance(cfg, Config)
        self.assertEqual(cfg.adsb.port, 8080)

    def test_user_values_override_defaults(self):
        data = {
            "adsb": {"host": "10.0.0.1", "receiver_lat": 42.6, "receiver_lon": -73.8},
            "pixoo": {"host": "10.0.0.2", "brightness": 50},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        cfg = load(path)
        self.assertEqual(cfg.adsb.host, "10.0.0.1")
        self.assertEqual(cfg.pixoo.brightness, 50)
        self.assertEqual(cfg.adsb.port, 8080)

    def test_color_parsed_as_tuple(self):
        data = {"display": {"color_flight": [255, 0, 0]}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        cfg = load(path)
        self.assertEqual(cfg.display.color_flight, (255, 0, 0))

    def test_adsb_url_property(self):
        cfg = Config()
        cfg.adsb.host = "192.168.1.1"
        cfg.adsb.port = 8080
        cfg.adsb.path = "/data/aircraft.json"
        self.assertEqual(cfg.adsb_url, "http://192.168.1.1:8080/data/aircraft.json")


class TestRendererHelpers(unittest.TestCase):
    def test_alt_str_below_transition(self):
        self.assertEqual(_alt_str(17999, 18000), "17,999 FT")

    def test_alt_str_at_transition(self):
        self.assertEqual(_alt_str(18000, 18000), "FL180")

    def test_alt_str_above_transition(self):
        self.assertEqual(_alt_str(35000, 18000), "FL350")

    def test_alt_str_none(self):
        self.assertEqual(_alt_str(None, 18000), "--- FT")

    def test_dist_str_km(self):
        self.assertEqual(_dist_str(100.0, "km"), "100KM")

    def test_dist_str_miles(self):
        self.assertEqual(_dist_str(100.0, "mi"), "62MI")

    def test_fingerprint_changes_on_altitude(self):
        ac1 = Aircraft.from_dump1090(
            {"hex": "abc", "flight": "SWA1", "alt_baro": 10000}
        )
        ac2 = Aircraft.from_dump1090(
            {"hex": "abc", "flight": "SWA1", "alt_baro": 20000}
        )
        self.assertNotEqual(
            _fingerprint(ac1, "BOS", "LAX"), _fingerprint(ac2, "BOS", "LAX")
        )

    def test_fingerprint_stable_on_same_data(self):
        ac = Aircraft.from_dump1090({"hex": "abc", "flight": "SWA1", "alt_baro": 10000})
        self.assertEqual(_fingerprint(ac, "BOS", "LAX"), _fingerprint(ac, "BOS", "LAX"))


class TestCompose(unittest.TestCase):
    def _make_aircraft(self, **kwargs):
        defaults = {
            "hex": "aabbcc",
            "flight": "SWA1234",
            "r": "N8731Q",
            "alt_baro": 35000,
            "gs": 450,
            "seen_pos": 1,
        }
        ac = Aircraft.from_dump1090({**defaults, **kwargs})
        ac.distance_km = 12.3
        return ac

    def _logo(self):
        return Image.new("RGB", (16, 16), (255, 100, 0))

    def test_returns_64x64_image(self):
        img = compose(self._make_aircraft(), self._logo(), "BOS", "LAX")
        self.assertEqual(img.size, (64, 64))

    def test_no_route_shows_registration(self):
        ac = self._make_aircraft()
        img = compose(ac, self._logo(), "???", "???")
        self.assertIsInstance(img, Image.Image)

    def test_no_route_no_registration_shows_hex(self):
        ac = self._make_aircraft(r="")
        img = compose(ac, self._logo(), "???", "???")
        self.assertIsInstance(img, Image.Image)

    def test_partial_route_origin_only(self):
        img = compose(self._make_aircraft(), self._logo(), "BOS", "???")
        self.assertIsInstance(img, Image.Image)

    def test_custom_colors_accepted(self):
        colors = DisplayConfig(
            color_flight=(255, 0, 0),
            color_route=(0, 255, 0),
            color_data=(0, 0, 255),
        )
        img = compose(self._make_aircraft(), self._logo(), "BOS", "LAX", colors)
        self.assertIsInstance(img, Image.Image)

    def test_none_altitude_renders(self):
        ac = self._make_aircraft(alt_baro="ground")
        img = compose(ac, self._logo(), "BOS", "LAX")
        self.assertIsInstance(img, Image.Image)


class TestFlightEnricher(unittest.TestCase):
    def _enricher(self, aerodatabox=False):
        cfg = Config()
        cfg.flight_data.enabled = True
        cfg.flight_data.cache_dir = tempfile.mkdtemp()
        if aerodatabox:
            cfg.flight_data.aerodatabox_key = "test-key"
        return FlightEnricher(cfg)

    def test_returns_unknown_when_disabled(self):
        cfg = Config()
        cfg.flight_data.enabled = False
        cfg.flight_data.cache_dir = tempfile.mkdtemp()
        e = FlightEnricher(cfg)
        self.assertEqual(e.get_route("aabbcc", "SWA1234"), ("???", "???"))

    def test_returns_unknown_when_no_callsign(self):
        e = self._enricher()
        self.assertEqual(e.get_route("aabbcc", ""), ("???", "???"))

    def _aerodatabox_ok(self, origin_iata, dest_iata):
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = [
            {
                "departure": {
                    "airport": {"iata": origin_iata, "icao": f"K{origin_iata}"}
                },
                "arrival": {"airport": {"iata": dest_iata, "icao": f"K{dest_iata}"}},
            }
        ]
        return r

    def test_aerodatabox_route_parsed(self):
        e = self._enricher(aerodatabox=True)
        with patch(
            "requests.Session.get",
            return_value=self._aerodatabox_ok("CVG", "BOS"),
        ):
            origin, dest = e.get_route("aabbcc", "RPA5789")
        self.assertEqual(origin, "CVG")
        self.assertEqual(dest, "BOS")

    def test_aerodatabox_skipped_without_key(self):
        e = self._enricher(aerodatabox=False)
        hexdb_resp = MagicMock()
        hexdb_resp.status_code = 200
        hexdb_resp.json.return_value = {"route": "KBOS-KLAX"}
        with patch("requests.Session.get", return_value=hexdb_resp) as mock_get:
            origin, _ = e.get_route("aabbcc", "SWA1234")
        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(origin, "BOS")

    def test_hexdb_route_parsed(self):
        e = self._enricher()
        hexdb_resp = MagicMock()
        hexdb_resp.status_code = 200
        hexdb_resp.json.return_value = {"route": "KBOS-KLAX"}
        with patch("requests.Session.get", return_value=hexdb_resp):
            origin, dest = e.get_route("aabbcc", "SWA1234")
        self.assertEqual(origin, "BOS")
        self.assertEqual(dest, "LAX")

    def test_result_cached_after_first_lookup(self):
        e = self._enricher()
        hexdb_resp = MagicMock()
        hexdb_resp.status_code = 200
        hexdb_resp.json.return_value = {"route": "KBOS-KLAX"}
        with patch("requests.Session.get", return_value=hexdb_resp) as mock_get:
            e.get_route("aabbcc", "SWA1234")
            e.get_route("aabbcc", "SWA1234")
        self.assertEqual(mock_get.call_count, 1)

    def test_falls_back_to_adsbdb_on_hexdb_failure(self):
        e = self._enricher()
        adsbdb_resp = MagicMock()
        adsbdb_resp.status_code = 200
        adsbdb_resp.json.return_value = {
            "response": {
                "flightroute": {
                    "origin": {"iata_code": "BOS", "icao_code": "KBOS"},
                    "destination": {"iata_code": "LAX", "icao_code": "KLAX"},
                }
            }
        }
        fail = MagicMock()
        fail.status_code = 404
        with patch("requests.Session.get", side_effect=[fail, adsbdb_resp]):
            origin, dest = e.get_route("aabbcc", "SWA1234")
        self.assertEqual(origin, "BOS")
        self.assertEqual(dest, "LAX")


class TestOperatingHours(unittest.TestCase):
    def _oh(self, start, end, enabled=True):
        return OperatingHoursConfig(enabled=enabled, start=start, end=end)

    def test_disabled_always_active(self):
        oh = self._oh("09:00", "17:00", enabled=False)
        self.assertTrue(oh.is_active(datetime.time(3, 0)))
        self.assertTrue(oh.is_active(datetime.time(20, 0)))

    def test_within_daytime_window(self):
        oh = self._oh("07:00", "23:00")
        self.assertTrue(oh.is_active(datetime.time(7, 0)))
        self.assertTrue(oh.is_active(datetime.time(12, 0)))
        self.assertTrue(oh.is_active(datetime.time(23, 0)))

    def test_outside_daytime_window(self):
        oh = self._oh("07:00", "23:00")
        self.assertFalse(oh.is_active(datetime.time(6, 59)))
        self.assertFalse(oh.is_active(datetime.time(23, 1)))

    def test_overnight_window_active_after_start(self):
        oh = self._oh("22:00", "06:00")
        self.assertTrue(oh.is_active(datetime.time(22, 30)))
        self.assertTrue(oh.is_active(datetime.time(0, 0)))
        self.assertTrue(oh.is_active(datetime.time(5, 59)))

    def test_overnight_window_inactive_in_middle_of_day(self):
        oh = self._oh("22:00", "06:00")
        self.assertFalse(oh.is_active(datetime.time(6, 1)))
        self.assertFalse(oh.is_active(datetime.time(12, 0)))
        self.assertFalse(oh.is_active(datetime.time(21, 59)))

    def test_config_load_operating_hours(self):
        data = {"operating_hours": {"enabled": True, "start": "08:00", "end": "20:00"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        cfg = load(path)
        self.assertTrue(cfg.operating_hours.enabled)
        self.assertEqual(cfg.operating_hours.start, "08:00")
        self.assertEqual(cfg.operating_hours.end, "20:00")

    def test_config_defaults_to_disabled(self):
        cfg = Config()
        self.assertFalse(cfg.operating_hours.enabled)
        self.assertTrue(cfg.operating_hours.is_active(datetime.time(3, 0)))


class TestIcaoToDisplay(unittest.TestCase):
    def test_k_prefix_stripped(self):
        self.assertEqual(_icao_to_display("KBOS"), "BOS")

    def test_c_prefix_stripped(self):
        self.assertEqual(_icao_to_display("CYUL"), "YUL")

    def test_european_airport_returns_iata(self):
        self.assertEqual(_icao_to_display("EGLL"), "LHR")

    def test_empty_returns_unknown(self):
        self.assertEqual(_icao_to_display(""), "???")

    def test_already_unknown(self):
        self.assertEqual(_icao_to_display("???"), "???")


if __name__ == "__main__":
    unittest.main()
