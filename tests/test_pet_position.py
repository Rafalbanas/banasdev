"""Keep the deliberately released page pet inside the viewport."""
from pathlib import Path
import re
import subprocess
import unittest


class PetPositionTests(unittest.TestCase):
    def test_viewport_bounds(self):
        source = (Path(__file__).resolve().parents[1] / "index.html").read_text()
        match = re.search(r"            function clampPetPosition\(x, y, width, height\) \{.*?\n            }", source, re.S)
        self.assertIsNotNone(match)
        subprocess.run(["node", "-e", match[0] + """
const assert = require('node:assert/strict');
assert.deepEqual(clampPetPosition(100, 120, 1440, 900), {x:100, y:120});
assert.deepEqual(clampPetPosition(-20, -100, 1440, 900), {x:8, y:8});
assert.deepEqual(clampPetPosition(9000, 9000, 320, 640), {x:248, y:496});
const before = clampPetPosition(1200, 700, 1440, 900);
assert.deepEqual(clampPetPosition(before.x, before.y, 320, 640), {x:248, y:496});
assert.deepEqual(clampPetPosition(200, 200, 50, 100), {x:8, y:8});
"""], check=True, capture_output=True, text=True)
