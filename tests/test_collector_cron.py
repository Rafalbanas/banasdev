"""The release collector must run with isolated data and without root privileges."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestCollectorCron(unittest.TestCase):
    def setUp(self):
        self.content = (ROOT / "deploy/collector.cron").read_text()
        self.jobs = [line.split(maxsplit=6) for line in self.content.splitlines()
                     if line.strip() and not line.startswith(("#", "SHELL=", "PATH="))]

    def test_cron_content(self):
        self.assertIn("SHELL=/bin/sh", self.content)
        self.assertIn("PATH=/usr/bin:/bin", self.content)
        self.assertEqual(len(self.jobs), 2)
        self.assertEqual([job[:5] for job in self.jobs],
                         [["*/15", "*", "*", "*", "*"], ["5", "*", "*", "*", "*"]])
        for job in self.jobs:
            self.assertEqual(job[5], "banasdev-weather")

    def test_paths(self):
        for job, mode in zip(self.jobs, ("--weather-only", "--air-only")):
            self.assertEqual(job[6], "BANASDEV_DATA_DIR=/var/lib/banasdev-weather "
                             "/usr/bin/python3 /var/lib/banasdev/current/fetch_weather.py "
                             f"{mode} >> /var/lib/banasdev-weather/weather.log 2>&1")


if __name__ == "__main__":
    unittest.main()
