"""Regression checks for audit fixes; JS checks execute the actual site functions."""
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import unittest

from scripts.security_policy import check, policy


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text()
TRANSLATIONS = HTML.split("const translations = ", 1)[1].split("\n            const projectLinks", 1)[0].strip().removesuffix(";")


def function(name):
    match = re.search(r"            (?:async )?function " + re.escape(name) + r"\(.*?\n            }", HTML, re.S)
    if not match:
        raise AssertionError("Missing site function: " + name)
    return match[0]


def run_js(names, source):
    script = "const assert = require('node:assert/strict');\n" + "\n".join(function(name) for name in names) + "\n" + source
    result = subprocess.run(["node", "-e", script], text=True, capture_output=True)
    if result.returncode:
        raise AssertionError(result.stderr or result.stdout)


class AuditRegressionTests(unittest.TestCase):
    def test_csp_hashes_match_source(self):
        check(ROOT)
        value = policy(HTML)
        self.assertIn("script-src-attr 'none'", value)
        self.assertNotIn("'unsafe-eval'", value)
        self.assertNotIn("'unsafe-inline'", value.split("style-src", 1)[0])
        self.assertNotEqual(value, policy(HTML.replace('const mailbox = "contact"', 'const mailbox = "other"')))

    def test_no_html_sinks_or_inline_event_handlers(self):
        self.assertNotRegex(HTML, r"\.(?:innerHTML|outerHTML)\s*=|insertAdjacentHTML\(")
        class Parser(HTMLParser):
            def handle_starttag(self, tag, attrs):
                for key, _ in attrs:
                    if key.startswith("on"):
                        raise AssertionError("Inline handler: " + key)
        Parser().feed(HTML)

    def test_headers_cover_location_inheritance(self):
        source = (ROOT / "deploy/nginx-public.conf").read_text()
        for name in ("Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options",
                     "X-Content-Type-Options", "Referrer-Policy"):
            self.assertEqual(source.count("add_header " + name + " "), 2, name)
        self.assertIn("frame-ancestors 'none'", source)
        self.assertNotIn("includeSubDomains", source)
        self.assertNotIn("max-age=0", source)

    def test_missing_values_are_not_zero_measurements(self):
        run_js(["mean", "bucketKeyFor", "aggregateWeatherBuckets"], """
            assert.equal(mean([null, undefined, '']), null);
            assert.equal(mean([null, 10, 20]), 15);
            assert.equal(mean([0]), 0);
            const timestamp = '2026-10-31T10:00:00Z';
            const weatherHistory = {days: {today: [{timestamp_utc: timestamp, pm25: null, pm10: 0, temperature: null}]}};
            const weatherModelData = {locations: {kat04bapp: {observations: [{interval_end_utc: timestamp, temperature: null, precipitation: null}]}}};
            const result = aggregateWeatherBuckets([{key: String(Date.parse(timestamp))}], '24h')[0];
            assert.equal(result.pm25, null);
            assert.equal(result.pm10, 0);
            assert.equal(result.collectedTemperature, null);
            assert.equal(result.collectedPrecipitation, null);
        """)

    def test_air_fresh_stale_future_invalid_and_failure(self):
        run_js(["renderWeather", "formatDateTime", "interpolate"], "const translations = " + TRANSLATIONS + ";\n" + """
            const document = {documentElement: {lang: 'pl'}, querySelector: () => null};
            const weatherWidget = {dataset: {}};
            const weatherStatus = {}, weatherUpdated = {};
            const AIR_MAX_AGE_MS = 3 * 60 * 60 * 1000;
            const now = Date.parse('2026-10-31T12:00:00Z'); Date.now = () => now;
            let weatherLoadFailed = false;
            const weatherData = {pm25: {value: 1, unit: 'µg/m³'}, pm10: {value: 2, unit: 'µg/m³'}, stations: [], air_index_level: 'GOOD', measured_at: new Date(now - 3600000).toISOString()};
            renderWeather(); assert.equal(weatherWidget.dataset.state, 'ready');
            weatherData.measured_at = new Date(now - AIR_MAX_AGE_MS - 1).toISOString();
            renderWeather(); assert.equal(weatherWidget.dataset.state, 'stale');
            assert.equal(weatherStatus.textContent, translations.pl.weather.airStale);
            renderWeather('en'); assert.equal(weatherStatus.textContent, translations.en.weather.airStale);
            for (const timestamp of ['invalid', new Date(now + 3600000).toISOString()]) {
                weatherData.measured_at = timestamp; renderWeather();
                assert.equal(weatherWidget.dataset.state, 'stale');
            }
            weatherLoadFailed = true; renderWeather(); assert.equal(weatherWidget.dataset.state, 'error');
        """)

    def test_forecast_attribute_payload_stays_text(self):
        run_js(["renderTwoHourForecast", "classifyPrecipitation", "forecastCondition", "formatNumber", "formatShortTime", "formatDateTime", "interpolate"],
               "const translations = " + TRANSLATIONS + ";\n" + """
            function node() { return {dataset: {}, children: [], append(...nodes) {this.children.push(...nodes)}, replaceChildren() {this.children = []}, set innerHTML(_) {throw Error('Unsafe HTML sink')}}; }
            const document = {documentElement: {lang: 'pl'}, createElement: node};
            const weatherForecast = node(), weatherForecastTitle = node(), weatherForecastMeta = node(), weatherForecastStrip = node(), weatherForecastKicker = node();
            const selectedWeatherRange = 'day', selectedWeatherDate = '2026-10-31';
            const dateKeyInWarsaw = () => selectedWeatherDate;
            const precipitationLoadFailed = false;
            const payload = '\"><img src=x onerror=alert(1)>';
            const interval = {forecast_time_utc: new Date().toISOString(), probability_interval_start_utc: payload, precipitation_probability: 10, temperature: 12, precipitation: 0, weather_code: 0};
            const weatherModelData = {locations: {kat04bapp: {current: interval, forecast: {issued_at_utc: new Date().toISOString(), intervals: [interval]}}}};
            renderTwoHourForecast();
            assert.equal(weatherForecastStrip.children.length, 1);
            const point = weatherForecastStrip.children[0];
            assert.equal(point.children.length, 4);
            assert.equal(point.children[3].title, payload);
            assert.equal(point.children[3].textContent, '10% / godz.');
        """)

    def test_table_contains_every_plotted_series(self):
        run_js(["renderAccessibleHistory", "formatNumber", "interpolate"], "const translations = " + TRANSLATIONS + ";\n" + """
            function node() { return {children: [], append(...nodes) {this.children.push(...nodes)}, replaceChildren(...nodes) {this.children = nodes}}; }
            const elements = Object.fromEntries(['weatherTableSummary', 'weatherTableCaption', 'weatherTableBody'].map(id => [id, node()]));
            const document = {documentElement: {lang: 'en'}, createElement: node, createDocumentFragment: node, getElementById: id => elements[id]};
            const weatherDataDetails = {open: true}, weatherHistoryDate = {textContent: 'Today'}, weatherPrecipitationNote = {textContent: '15 min'};
            const bucket = {label: '12:00', collectedTemperature: 10, backfillTemperature: null, forecastTemperature: 11, pm25: 0, pm10: 3, collectedPrecipitation: 0, backfillPrecipitation: null, forecastPrecipitation: 2};
            renderAccessibleHistory('en', [bucket]);
            const row = elements.weatherTableBody.children[0].children[0];
            assert.deepEqual(row.children.map(cell => cell.textContent), ['12:00', '10', '—', '11', '0', '3', '0', '—', '2']);
            assert.match(elements.weatherTableSummary.textContent, /1 of 1/);
            assert.equal(row.children[0].scope, 'row');
        """)


if __name__ == "__main__":
    unittest.main()
