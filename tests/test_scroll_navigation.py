"""Execute the actual scrollspy functions against changing section geometry."""
from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ScrollNavigationTests(unittest.TestCase):
    def test_navigation_tracks_geometry_and_accessible_state(self):
        html = (ROOT / "index.html").read_text()
        functions = []
        for name in ("setActiveNavigation", "updateActiveNavigation"):
            match = re.search(r"            function " + name + r"\(.*?\n            }", html, re.S)
            self.assertIsNotNone(match, name)
            functions.append(match[0])
        source = r"""
            const assert = require('node:assert/strict');
            const window = {innerHeight: 900, scrollY: 0};
            const document = {documentElement: {scrollHeight: 20000}};
            let barBottom = 80;
            const topbar = {getBoundingClientRect: () => ({bottom: barBottom})};
            const ids = ['about', 'experience', 'projects', 'skills', 'weather', 'contact'];
            const sectionTargets = ids.map((id, i) => ({id, top: 1000 + i * 3000,
                getBoundingClientRect() {return {top: this.top};}}));
            const navLinks = ids.map(id => {
                const attrs = {href: '#' + id};
                const classes = new Set();
                return {attrs, classes,
                    getAttribute: name => attrs[name] ?? null,
                    setAttribute: (name, value) => attrs[name] = value,
                    removeAttribute: name => delete attrs[name],
                    classList: {toggle(name, active) {
                        if (active) classes.add(name); else classes.delete(name);
                    }}};
            });
            function expectActive(id) {
                updateActiveNavigation();
                assert.deepEqual(navLinks.filter(l => l.classes.has('is-active')).map(l => l.attrs.href),
                                 id ? ['#' + id] : []);
                assert.deepEqual(navLinks.filter(l => l.attrs['aria-current']).map(l => l.attrs.href),
                                 id ? ['#' + id] : []);
                if (id) assert.equal(navLinks.find(l => l.attrs.href === '#' + id).attrs['aria-current'], 'location');
            }
            expectActive(null);
            // Visit every section, then traverse the same geometry in reverse.
            for (const index of [...ids.keys(), ...[...ids.keys()].reverse()]) {
                sectionTargets.forEach((s, i) => s.top = (i - index) * 3000 + 100);
                expectActive(ids[index]);
            }
            sectionTargets.forEach((s, i) => s.top = (i - 2) * 3000 - 2000);
            expectActive('projects');
            sectionTargets[3].top = 100;
            expectActive('skills');
            sectionTargets[3].top = 500;
            expectActive('projects');
            sectionTargets[3].top = 300;
            barBottom = 300;
            expectActive('skills');
            barBottom = 80;
            expectActive('projects');
            window.scrollY = 19100;
            expectActive('contact');
            window.scrollY = 0;
            sectionTargets.forEach((s, i) => s.top = 1000 + i * 3000);
            expectActive(null);
        """
        result = subprocess.run(["node", "-e", "\n".join(functions) + source], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
