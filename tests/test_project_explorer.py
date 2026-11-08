"""Static/no-JS contracts for the project explorer; no browser dependency in CI."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROJECT_IDS = ("cycling", "plates", "resume", "chat", "lanari", "thesis",
               "automation", "banas", "homelab")
PUBLIC_IDS = set(PROJECT_IDS) - {"automation", "homelab"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
             "link", "meta", "param", "source", "track", "wbr"}


class ProjectExplorerParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.cards = {}
        self.card = None
        self.view_buttons = []
        self.project_tools = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        frame = {"tag": tag, "attrs": attrs, "panel": None, "card": False}
        if attrs.get("id") == "projectTools":
            self.project_tools = attrs
        if tag == "button" and "data-project-view" in attrs:
            self.view_buttons.append(attrs)
        if tag == "article" and "data-project-id" in attrs:
            project_id = attrs["data-project-id"]
            if project_id in self.cards:
                raise ValueError("Duplicate project ID: " + project_id)
            self.card = {"attrs": attrs, "studies": [], "summaries": [],
                         "panels": [], "evidence": [], "links": [], "text": []}
            self.cards[project_id] = self.card
            frame["card"] = True
        if self.card is not None:
            if tag == "details" and "data-case-study" in attrs:
                self.card["studies"].append(attrs["data-case-study"])
            if tag == "summary":
                self.card["summaries"].append([])
            if tag == "div" and "data-case-panel" in attrs:
                panel = {"attrs": attrs, "has_h4": False}
                self.card["panels"].append(panel)
                frame["panel"] = panel
            if tag == "h4":
                for ancestor in reversed(self.stack):
                    if ancestor["panel"] is not None:
                        ancestor["panel"]["has_h4"] = True
                        break
            if tag == "a":
                self.card["links"].append(attrs)
                if any("case-evidence" in item["attrs"].get("class", "").split()
                       for item in self.stack):
                    self.card["evidence"].append(attrs)
        if tag not in VOID_TAGS:
            self.stack.append(frame)

    def handle_data(self, data):
        if self.card is not None:
            self.card["text"].append(data)
            if any(item["tag"] == "summary" for item in self.stack):
                self.card["summaries"][-1].append(data)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                if any(item["card"] for item in self.stack[index:]):
                    self.card = None
                del self.stack[index:]
                break


class TestProjectExplorer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = ProjectExplorerParser()
        cls.parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))

    def test_card_ids_and_native_studies(self):
        self.assertEqual(tuple(self.parser.cards), PROJECT_IDS)
        for project_id, card in self.parser.cards.items():
            with self.subTest(project=project_id):
                self.assertIn("project-card", card["attrs"].get("class", "").split())
                self.assertNotIn("hidden", card["attrs"])
                self.assertEqual(card["studies"], [project_id])
                self.assertEqual(len(card["summaries"]), 1)
                self.assertTrue("".join(card["summaries"][0]).strip())
                self.assertEqual([panel["attrs"]["data-case-panel"] for panel in card["panels"]],
                                 ["overview", "flow", "quality"])
                for panel in card["panels"]:
                    self.assertNotIn("hidden", panel["attrs"], "All panels must work without JS")
                    self.assertTrue(panel["has_h4"])

    def test_view_controls_and_progressive_enhancement(self):
        self.assertIsNotNone(self.parser.project_tools)
        self.assertIn("hidden", self.parser.project_tools)
        self.assertEqual([item["data-project-view"] for item in self.parser.view_buttons],
                         ["grid", "list"])
        for item in self.parser.view_buttons:
            self.assertEqual(item.get("type"), "button")
            self.assertEqual(item.get("aria-pressed"),
                             "true" if item["data-project-view"] == "grid" else "false")
            self.assertEqual(item.get("aria-controls"), "projectFeatured projectMore")

    def test_sources_are_nonempty_and_pinned(self):
        for project_id in PUBLIC_IDS:
            with self.subTest(project=project_id):
                links = self.parser.cards[project_id]["evidence"]
                self.assertTrue(links, "A vacuous loop does not validate sources")
                for link in links:
                    self.assertRegex(link.get("href", ""),
                                     r"^https://github\.com/Rafalbanas/[^/]+/(?:blob|tree)/[a-f0-9]{40}(?:/|$)")
                    self.assertEqual(link.get("target"), "_blank")
                    self.assertIn("noopener", link.get("rel", "").split())
        self.assertEqual(self.parser.cards["automation"]["evidence"], [])

    def test_homelab_is_a_project_not_a_private_data_export(self):
        card = self.parser.cards["homelab"]
        text = " ".join(card["text"])
        for required in ("Ubuntu", "Ollama", "KVM / libvirt", "systemd",
                         "Home Assistant OS", "dokumentacja prywatna"):
            with self.subTest(term=required):
                self.assertIn(required, text)
        self.assertEqual(card["links"], [], "Do not link private documentation")
        self.assertNotRegex(text, r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
        self.assertNotRegex(text, r"https?://|:[1-9]\d{1,4}\b|/(?:home|root|etc|var)/")

    def test_parser_checks_boolean_attributes_and_nested_content(self):
        # Prove the parser notices invalid states instead of silently skipping cards.
        parser = ProjectExplorerParser()
        parser.feed('<div id="projectTools" hidden></div>'
                    '<button data-project-view="grid" type="button" aria-pressed="true"></button>'
                    '<article class="card project-card" data-project-id="sample">'
                    '<details data-case-study="sample"><summary>Read <span>more</span></summary>'
                    '<div data-case-panel="overview" hidden><div><h4>Heading</h4></div></div>'
                    '<div class="case-evidence"><a href="https://example.com">Source</a></div>'
                    '</details><p>Still part of the card</p></article><p>Outside</p>')
        card = parser.cards["sample"]
        self.assertIn("hidden", parser.project_tools)
        self.assertIn("hidden", card["panels"][0]["attrs"])
        self.assertTrue(card["panels"][0]["has_h4"])
        self.assertEqual("".join(card["summaries"][0]), "Read more")
        self.assertEqual(len(card["evidence"]), 1)
        self.assertIn("Still part of the card", card["text"])
        self.assertNotIn("Outside", card["text"])


if __name__ == "__main__":
    unittest.main()
