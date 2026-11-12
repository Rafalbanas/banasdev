import unittest
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess

class MarkupParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.panels = []
        self.controls = None
        self.buttons = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "section" and "data-lab-model-panel" in attrs:
            self.panels.append(attrs)
        if attrs.get("id") == "labModelSwitch":
            self.controls = attrs
        if tag == "button" and "data-lab-model" in attrs:
            self.buttons.append(attrs)

class TestHomelabModels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.parser = MarkupParser()
        cls.parser.feed((root / "index.html").read_text(encoding="utf-8"))

    def test_panels_contract(self):
        self.assertEqual(len(self.parser.panels), 3)
        ids = [p["id"] for p in self.parser.panels]
        self.assertEqual(set(ids), {"labModelGemma", "labModelQwen", "labModelGptoss"})
        self.assertEqual({p["data-lab-model-panel"]: p["id"] for p in self.parser.panels}, {
            "gemma": "labModelGemma", "qwen": "labModelQwen", "gptoss": "labModelGptoss"
        })

        evidence_map = {
            "gemma": "owner-log",
            "qwen": "inventory",
            "gptoss": "inventory"
        }

        for panel in self.parser.panels:
            model = panel["data-lab-model-panel"]
            self.assertEqual(panel.get("data-evidence"), evidence_map[model])
            self.assertNotIn("hidden", panel, f"Panel {model} should not be hidden")

    def test_controls_contract(self):
        self.assertIsNotNone(self.parser.controls)
        self.assertIn("hidden", self.parser.controls)

        self.assertEqual(len(self.parser.buttons), 3)
        controls_attr = "labModelGemma labModelQwen labModelGptoss"

        press_states = {}
        for btn in self.parser.buttons:
            self.assertEqual(btn.get("type"), "button")
            self.assertEqual(btn.get("aria-controls"), controls_attr)
            model = btn["data-lab-model"]
            press_states[model] = btn.get("aria-pressed")

        self.assertEqual(press_states["gemma"], "true")
        self.assertEqual(press_states["qwen"], "false")
        self.assertEqual(press_states["gptoss"], "false")

    def test_actual_selector_logic(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "index.html").read_text(encoding="utf-8")
        match = re.search(r"            function setupHomelabModels\(.*?\n            }", source, re.S)
        self.assertIsNotNone(match)
        script = match[0] + """
            const assert = require('node:assert/strict');
            const profiles = ['gemma', 'qwen', 'gptoss'];
            const buttons = profiles.map(profile => ({
                dataset: {labModel: profile}, attrs: {}, listeners: {},
                setAttribute(name, value) { this.attrs[name] = value; },
                addEventListener(name, callback) { this.listeners[name] = callback; }
            }));
            const panels = profiles.map(profile => ({dataset: {labModelPanel: profile}, hidden: false}));
            const controls = {hidden: true, querySelectorAll() { return buttons; }};
            const document = {
                getElementById(id) { assert.equal(id, 'labModelSwitch'); return controls; },
                querySelectorAll(selector) {
                    assert.equal(selector, '#labModels [data-lab-model-panel]'); return panels;
                }
            };
            globalThis.fetch = () => assert.fail('A description selector must not load models');
            setupHomelabModels();
            assert.equal(controls.hidden, false);
            function check(profile) {
                panels.forEach(panel => assert.equal(panel.hidden, panel.dataset.labModelPanel !== profile));
                buttons.forEach(button => assert.equal(button.attrs['aria-pressed'], String(button.dataset.labModel === profile)));
            }
            check('gemma');
            for (const profile of ['qwen', 'gptoss', 'gemma']) {
                buttons.find(button => button.dataset.labModel === profile).listeners.click();
                check(profile);
            }
        """
        result = subprocess.run(["node", "-e", script], text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

if __name__ == "__main__":
    unittest.main()
