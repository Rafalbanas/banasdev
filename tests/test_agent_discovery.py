import unittest
import json
from pathlib import Path
from urllib.parse import urlsplit
import scripts.agent_content as agent_content

ROOT = Path(__file__).resolve().parents[1]

class TestAgentDiscovery(unittest.TestCase):
    def test_agent_content_check(self):
        # 1) scripts.agent_content.check_or_write(ROOT) przechodzi
        agent_content.check_or_write(ROOT)

    def test_sitemap(self):
        # 2) XML ma standard namespace i 3 kanoniczne loc
        from xml.etree import ElementTree as ET
        tree = ET.parse(ROOT / "sitemap.xml")
        root = tree.getroot()
        namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
        self.assertEqual(root.tag, f"{{{namespace}}}urlset")
        locs = [node.text for node in root.findall(f"{{{namespace}}}url/{{{namespace}}}loc")]
        expected = [
            "https://banas.dev/",
            "https://banas.dev/projekty.html",
            "https://banas.dev/hobby.html"
        ]
        self.assertEqual(len(locs), 3)
        self.assertEqual(set(locs), set(expected))
        self.assertEqual(len(set(locs)), 3)

    def test_robots(self):
        # 3) robots zachowuje User-agent:* i Allow:/, dokładnie jeden Sitemap; Content-Signal
        content = (ROOT / "robots.txt").read_text()
        self.assertIn("User-agent: *", content)
        self.assertIn("Allow: /", content)
        self.assertIn("Sitemap: https://banas.dev/sitemap.xml", content)
        self.assertEqual(sum(line.startswith("Sitemap:") for line in content.splitlines()), 1)
        signals = next(line.split(":", 1)[1] for line in content.splitlines() if line.startswith("Content-Signal:"))
        self.assertEqual(dict(part.strip().split("=") for part in signals.split(",")),
                         {"ai-train": "no", "search": "yes", "ai-input": "yes"})

    def test_api_catalog(self):
        # 4) JSON .well-known/api-catalog ma linkset listę, w każdym anchor i niepuste service-desc oraz service-doc tablice zawierające URL na banas.dev; brak wymyślonego status endpointu.
        catalog = json.loads((ROOT / ".well-known/api-catalog").read_text())
        linkset = catalog.get("linkset", [])
        self.assertTrue(len(linkset) > 0)
        for entry in linkset:
            self.assertEqual(urlsplit(entry.get("anchor", "")).netloc, "banas.dev")
            self.assertTrue(len(entry.get("service-desc", [])) > 0)
            self.assertTrue(len(entry.get("service-doc", [])) > 0)
            for item in entry.get("service-desc", []) + entry.get("service-doc", []):
                self.assertEqual(urlsplit(item.get("href", "")).netloc, "banas.dev")
            self.assertNotIn("status", entry)

    def test_openapi(self):
        # 5) openapi.json ma openapi=3.1.0 i GET dla /data.json,/history.json,/weather.json, żadnego POST; externalDocs api.md.
        data = json.loads((ROOT / "openapi.json").read_text())
        self.assertEqual(data.get("openapi"), "3.1.0")
        paths = data.get("paths", {})
        for path in ["/data.json", "/history.json", "/weather.json"]:
            self.assertIn(path, paths)
            self.assertIn("get", paths[path])
            self.assertNotIn("post", [k.lower() for k in paths[path]])
        self.assertEqual(data.get("externalDocs", {}).get("url"), "https://banas.dev/api.md")

    def test_hobby_md(self):
        # 6) Markdown hobby.md zawiera # Po godzinach. i uczciwą informację że nie zawiera prognozy na żywo; nie zawiera <script ani angielskiego nagłówka '# After hours.'; index.md ma Rafał Banaś i LinkedIn; projekty.md ma CVTailor,Cycling,Plates.
        content = (ROOT / "hobby.md").read_text()
        self.assertIn("# Po godzinach.", content)
        self.assertIn("nie zawiera prognozy ani rekomendacji na żywo", content)
        self.assertNotIn("<script", content)
        self.assertNotIn("# After hours.", content)

        index_content = (ROOT / "index.md").read_text()
        self.assertIn("Rafał Banaś", index_content)
        self.assertIn("LinkedIn", index_content)

        projekty_content = (ROOT / "projekty.md").read_text()
        self.assertIn("CVTailor", projekty_content)
        self.assertIn("Cycling", projekty_content)
        self.assertIn("Plates", projekty_content)

if __name__ == "__main__":
    unittest.main()
