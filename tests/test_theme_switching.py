"""Theme changes must not synchronously rebuild weather history charts."""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ThemeSwitchingTests(unittest.TestCase):
    def test_saved_theme_is_applied_before_styles(self):
        html = (ROOT / "index.html").read_text()
        bootstrap = re.search(r'<script data-cfasync="false" id="themeBootstrap">(.*?)</script>', html, re.S)
        self.assertIsNotNone(bootstrap)
        self.assertLess(bootstrap.start(), html.index("<style>"))
        subprocess.run(["node", "-e", """
const assert = require('node:assert/strict');
let light;
global.document = {documentElement: {classList: {toggle(name, value) {light = value;}}}};
global.localStorage = {getItem() {return 'light';}};
""" + bootstrap.group(1) + """
assert.equal(light, true);
localStorage.getItem = () => {throw Error('Storage blocked');};
""" + bootstrap.group(1)], check=True)

    def test_switch_updates_ui_without_rebuilding_history(self):
        html = (ROOT / "index.html").read_text()
        start = html.index("            function updateWeatherChartTheme()")
        end = html.index("            setupHomelab", start)
        source = html[start:end]
        subprocess.run(["node", "-e", """
const assert = require('node:assert/strict');
let isLight = false;
let queued;
let updates = 0;
const attrs = {};
const themeToggle = {setAttribute(key, value) {attrs[key] = value;}};
const translations = {pl: {theme: {lightTitle: 'ciemny', darkTitle: 'jasny'}}};
const document = {
 documentElement: {lang: 'pl', classList: {toggle(name, value) {isLight = value;}}},
 body: {}, querySelector() {return {setAttribute() {}};}
};
const window = {requestAnimationFrame(fn) {queued = fn;return 1;},
 cancelAnimationFrame() {}, setTimeout(fn) {fn();}};
const getComputedStyle = () => ({getPropertyValue: name => name === '--muted' ? '#123456' : '#abcdef'});
const chart = () => ({options: {plugins: {legend: {labels: {}}}, scales: {
 x: {ticks: {}, grid: {}}, y: {ticks: {}, grid: {}, title: {}}
}}, update(mode) {assert.equal(mode, 'none'); updates++;}});
let weatherChart = chart();
let weatherPrecipitationChart = chart();
function renderWeatherHistory() {throw Error('Synchronous history rebuild');}
""" + source + """
applyTheme('light');
assert.equal(isLight, true);
assert.equal(attrs['aria-pressed'], 'true');
assert.equal(updates, 0);
queued();
assert.equal(updates, 2);
assert.equal(weatherChart.options.scales.x.ticks.color, '#123456');
applyTheme('dark');
assert.equal(isLight, false);
assert.equal(attrs['aria-pressed'], 'false');
weatherChart = null; weatherPrecipitationChart = null;
queued();
"""], check=True)
