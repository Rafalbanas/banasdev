"""Allowlisted, local-only portfolio commands; no shell interpretation."""
from pathlib import Path
import re
import subprocess
import unittest


class InteractiveTerminalTests(unittest.TestCase):
    def test_command_parser(self):
        html = (Path(__file__).resolve().parents[1] / "index.html").read_text()
        match = re.search(r"            function resolveTerminalCommand\(value\) \{.*?\n            }", html, re.S)
        self.assertIsNotNone(match)
        subprocess.run(["node", "-e", match[0] + r"""
const assert = require('node:assert/strict');
for (const [command, key] of Object.entries({
  help: 'help', whoami: 'whoami', ls: 'sections',
  'cat .motd': 'cat', 'ride --gravel': 'ride', clear: 'clear'
})) {
  assert.deepEqual(resolveTerminalCommand(command), {command, key});
}
assert.equal(resolveTerminalCommand('  '), null);
assert.deepEqual(resolveTerminalCommand(' CAT   .motd '), {command: 'cat .motd', key: 'cat'});
for (const command of ['__proto__', 'constructor', 'rm -rf /', 'help; whoami',
  '$(whoami)', '<img src=x onerror=alert(1)>', 'cat /etc/passwd']) {
  assert.equal(resolveTerminalCommand(command).key, 'unknown');
}
assert.equal(resolveTerminalCommand('x'.repeat(1000)).command.length, 100);
"""], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
