"""Static, no-JavaScript contract for the homelab introduction."""
from html.parser import HTMLParser
from pathlib import Path
import unittest


class OverviewParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.nodes = []

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "parents": tuple(self.stack)}
        self.nodes.append(node)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img",
                       "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break


class HomelabOverviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parser = OverviewParser()
        parser.feed((Path(__file__).resolve().parents[1] / "index.html").read_text())
        cls.nodes = parser.nodes

    def by_id(self, value):
        return next(node for node in self.nodes if node["attrs"].get("id") == value)

    def test_anchor_and_accessible_heading(self):
        card = self.by_id("homelab")
        self.assertEqual(card["attrs"]["data-project-id"], "homelab")
        heading = self.by_id("lab-overview-title")
        overview = heading["parents"][-1]
        self.assertEqual(overview["attrs"]["aria-labelledby"], "lab-overview-title")
        self.assertTrue(any(parent is card for parent in overview["parents"]))
        links = [n for n in self.nodes if n["tag"] == "a" and n["attrs"].get("href") == "#homelab"]
        self.assertTrue(any(any(p["attrs"].get("id") == "top" for p in n["parents"]) for n in links))

    def test_three_use_cases_and_visible_fallback(self):
        overview = self.by_id("lab-overview-title")["parents"][-1]
        children = [n for n in self.nodes if any(p is overview for p in n["parents"])]
        articles = [n for n in children if n["tag"] == "article"]
        self.assertEqual(len(articles), 3)
        for article, name in zip(articles, ("ai", "access", "home")):
            keys = {n["attrs"].get("data-i18n") for n in children
                    if any(p is article for p in n["parents"])}
            self.assertTrue({f"labOverview.{name}Title", f"labOverview.{name}Text"} <= keys)
        keys = {n["attrs"].get("data-i18n") for n in children}
        self.assertIn("labOverview.decisionText", keys)
        for node in children:
            for ancestor in (*node["parents"], node):
                self.assertNotEqual(ancestor["tag"], "details")
                self.assertNotIn("hidden", ancestor["attrs"])

    def test_explanation_precedes_technical_details(self):
        card = self.by_id("homelab")
        children = [n for n in self.nodes if any(p is card for p in n["parents"])]
        positions = {}
        for index, node in enumerate(children):
            for name in ("lab-overview", "lab-specs", "lab-models"):
                if name in node["attrs"].get("class", "").split():
                    positions[name] = index
        self.assertLess(positions["lab-overview"], positions["lab-specs"])
        self.assertLess(positions["lab-specs"], positions["lab-models"])
