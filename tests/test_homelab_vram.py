import unittest
import subprocess
import json
import re
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

class TestCompareLabVram(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        index_path = os.path.join(ROOT, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract the function block
        match = re.search(r'            function compareLabVram\(.*?\n            }', content, re.S)
        if not match:
            raise RuntimeError("Could not find compareLabVram function in index.html")

        cls.js_code = match.group(0)

    def run_js(self, gui_text, headless_text, capacity=12288):
        script = self.js_code + f"""
        const assert = require('node:assert/strict');
        const result = compareLabVram({json.dumps(gui_text)}, {json.dumps(headless_text)}, {capacity});
        for (const value of Object.values(result)) {{
            if (typeof value === 'number') assert.ok(Number.isFinite(value));
        }}
        console.log(JSON.stringify(result));
        """

        result = subprocess.run(
            ["node", "-e", script], capture_output=True, text=True, encoding="utf-8"
        )
        if result.returncode != 0:
            self.fail(f"JS Execution Error: {result.stderr.strip()}")
        return json.loads(result.stdout.strip())

    def test_empty_state(self):
        res = self.run_js("", "")
        self.assertEqual(res["state"], "empty")
        res = self.run_js(None, None)
        self.assertEqual(res["state"], "empty")

    def test_one_missing_reading(self):
        self.assertEqual(self.run_js("", "8899"), {"state": "empty"})
        self.assertEqual(self.run_js("9088", "  "), {"state": "empty"})

    def test_whitespace(self):
        res = self.run_js(" 9088 ", " 8899 ")
        self.assertEqual(res["state"], "lower")
        self.assertEqual(res["delta"], 189)

    def test_increase_from_zero_has_no_percentage(self):
        self.assertEqual(self.run_js("0", "1"), {"state": "higher", "delta": 1})

    def test_invalid_negative(self):
        res = self.run_js("-100", "1000")
        self.assertEqual(res["state"], "invalid")

    def test_invalid_too_large(self):
        res = self.run_js("13000", "1000")
        self.assertEqual(res["state"], "invalid")

    def test_invalid_float(self):
        res = self.run_js("100.5", "1000")
        self.assertEqual(res["state"], "invalid")

    def test_invalid_nan(self):
        res = self.run_js("NaN", "1000")
        self.assertEqual(res["state"], "invalid")

    def test_invalid_infinity(self):
        res = self.run_js("Infinity", "1000")
        self.assertEqual(res["state"], "invalid")

    def test_lower_state(self):
        res = self.run_js("9088", "8899")
        self.assertEqual(res["state"], "lower")
        self.assertEqual(res["delta"], 189)
        expected_percent = 100 * 189 / 9088
        self.assertAlmostEqual(res["percent"], expected_percent, delta=1e-10)

    def test_equal_zero(self):
        res = self.run_js("0", "0")
        self.assertEqual(res["state"], "equal")
        self.assertEqual(res["delta"], 0)

    def test_equal_500(self):
        res = self.run_js("500", "500")
        self.assertEqual(res["state"], "equal")
        self.assertEqual(res["delta"], 0)

    def test_higher_state(self):
        res = self.run_js("100", "150")
        self.assertEqual(res["state"], "higher")
        self.assertEqual(res["delta"], 50)

    def test_lower_max_savings(self):
        res = self.run_js("12288", "0")
        self.assertEqual(res["state"], "lower")
        self.assertEqual(res["delta"], 12288)
        self.assertEqual(res["percent"], 100)

if __name__ == "__main__":
    unittest.main()
