import unittest
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def call_evaluate(location, air, now_ms, duration=60, failed=False):
    code = f"""
    try {{
        const result = require('./assets/ride-planner.js').evaluate(
            {json.dumps(location)},
            {json.dumps(air)},
            {now_ms},
            {duration},
            {str(failed).lower()}
        );
        console.log(JSON.stringify(result));
    }} catch (e) {{
        console.error(e);
        process.exit(1);
    }}
    """
    process = subprocess.run(
        ["node", "-e", code],
        capture_output=True,
        text=True,
        cwd=ROOT
    )
    if process.returncode != 0:
        raise Exception(f"Node execution failed: {process.stderr}")
    return json.loads(process.stdout)

class TestRidePlanner(unittest.TestCase):
    def setUp(self):
        start = datetime(2026, 11, 15, 10, tzinfo=timezone.utc)
        self.now = int(start.timestamp() * 1000)
        self.ts = start.isoformat()
        point = {"temperature": 15, "wind_speed": 10, "precipitation": 0,
                 "weather_code": 0, "precipitation_probability": 0}
        self.base_location = {
            "current": {
                "data_time_utc": self.ts,
                "fetched_at_utc": self.ts,
                "temperature": 15,
                "wind_speed": 10,
                "precipitation": 0,
                "weather_code": 0,
                "precipitation_probability": 0
            },
            "forecast": {
                "issued_at_utc": self.ts,
                "intervals": [
                    dict(point,
                         interval_start_utc=(start + timedelta(minutes=i * 15)).isoformat(),
                         interval_end_utc=(start + timedelta(minutes=(i + 1) * 15)).isoformat())
                    for i in range(8)
                ]
            }
        }
        self.base_air = {
            "measured_at": self.ts,
            "pm25": {"value": 10},
            "pm10": {"value": 15},
            "air_index_level": "GOOD",
            "stations": [{"air_index_level": "GOOD"}]
        }

    def test_good_input(self):
        res = call_evaluate(self.base_location, self.base_air, self.now)
        self.assertEqual(res["state"], "go")

    def test_old_data(self):
        loc = self.base_location.copy()
        loc["current"]["data_time_utc"] = "2020-01-01T00:00:00Z"
        res = call_evaluate(loc, self.base_air, self.now)
        self.assertEqual(res["state"], "unknown")

    def test_failed_flag(self):
        res = call_evaluate(self.base_location, self.base_air, self.now, duration=60, failed=True)
        self.assertEqual(res["state"], "unknown")

    def test_null_wind(self):
        loc = self.base_location.copy()
        loc["forecast"]["intervals"][1]["wind_speed"] = None
        res = call_evaluate(loc, self.base_air, self.now)
        self.assertEqual(res["state"], "unknown")

    def test_null_probability(self):
        self.base_location["forecast"]["intervals"][0]["precipitation_probability"] = None
        res = call_evaluate(self.base_location, self.base_air, self.now)
        self.assertEqual(res["state"], "unknown")

    def test_rain_avoid(self):
        loc = self.base_location.copy()
        for point in loc["forecast"]["intervals"]:
            point["precipitation"] = 0.6
        res = call_evaluate(loc, self.base_air, self.now)
        self.assertEqual(res["state"], "avoid")

    def test_strong_wind_avoid(self):
        loc = self.base_location.copy()
        for point in loc["forecast"]["intervals"]:
            point["wind_speed"] = 40
        res = call_evaluate(loc, self.base_air, self.now)
        self.assertEqual(res["state"], "avoid")

    def test_air_bad_station(self):
        air = self.base_air.copy()
        air["stations"] = [{"air_index_level": "BAD"}]
        res = call_evaluate(self.base_location, air, self.now)
        self.assertEqual(res["state"], "avoid")

    def test_caution_temperature(self):
        loc = self.base_location.copy()
        for point in loc["forecast"]["intervals"]:
            point["temperature"] = 5
        res = call_evaluate(loc, self.base_air, self.now)
        self.assertEqual(res["state"], "caution")

    def test_wait_condition(self):
        loc = self.base_location.copy()
        for point in loc["forecast"]["intervals"][:2]:
            point["precipitation"] = 0.8
        res = call_evaluate(loc, self.base_air, self.now, duration=60)
        self.assertEqual(res["state"], "wait")
        self.assertEqual(res["start"], self.now + 30 * 60 * 1000)

    def test_gap_unknown(self):
        loc = self.base_location.copy()
        del loc["forecast"]["intervals"][1]
        res = call_evaluate(loc, self.base_air, self.now, duration=60)
        self.assertEqual(res["state"], "unknown")

    def test_duration_too_long(self):
        loc = self.base_location.copy()
        loc["forecast"]["intervals"] = loc["forecast"]["intervals"][:4]
        res = call_evaluate(loc, self.base_air, self.now, duration=90)
        self.assertEqual(res["state"], "unknown")

    def test_negative_pm(self):
        air = self.base_air.copy()
        air["pm25"]["value"] = -5
        res = call_evaluate(self.base_location, air, self.now)
        self.assertEqual(res["state"], "unknown")

if __name__ == "__main__":
    unittest.main()
