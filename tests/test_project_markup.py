import unittest
from html.parser import HTMLParser
from pathlib import Path


class MarkupParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards = []
        self.filters = []
        self.project_tools = None
        self.search_input = None
        self.labels = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and "project-card" in attrs.get("class", "").split():
            self.cards.append(attrs)
        if tag == "button" and "data-project-filter" in attrs:
            self.filters.append(attrs)
        if attrs.get("id") == "projectTools":
            self.project_tools = attrs
        if tag == "input" and attrs.get("id") == "projectSearch":
            self.search_input = attrs
        if tag == "label" and "for" in attrs:
            self.labels.append(attrs["for"])


class TestProjectMarkup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.markup = MarkupParser()
        cls.markup.feed((root / "index.html").read_text(encoding="utf-8"))

    def test_parser_handles_class_tokens_and_boolean_attributes(self):
        parser = MarkupParser()
        parser.feed('<article class="card project-card actionable"></article>'
                    '<div id="projectTools" hidden></div>')
        self.assertEqual(len(parser.cards), 1)
        self.assertIn("hidden", parser.project_tools)

    def test_project_cards_contract(self):
        self.assertTrue(self.markup.cards, "Project cards must exist")
        allowed = {"data", "automation", "web"}
        for card in self.markup.cards:
            with self.subTest(card=card):
                categories = card.get("data-project-categories", "").split()
                self.assertTrue(categories, "Every project needs a category")
                self.assertTrue(set(categories) <= allowed)
                self.assertNotIn("hidden", card, "Cards must remain visible without JS")

    def test_project_filters_contract(self):
        filters = self.markup.filters
        allowed = {"all", "data", "automation", "web"}
        self.assertEqual({button["data-project-filter"] for button in filters}, allowed)
        self.assertEqual(len(filters), len(allowed), "No missing or duplicate filters")
        for button in filters:
            with self.subTest(filter=button["data-project-filter"]):
                self.assertEqual(button.get("type"), "button")
                expected = "true" if button["data-project-filter"] == "all" else "false"
                self.assertEqual(button.get("aria-pressed"), expected)

    def test_project_tools_hidden(self):
        self.assertIsNotNone(self.markup.project_tools)
        self.assertIn("hidden", self.markup.project_tools)

    def test_project_search_contract(self):
        search = self.markup.search_input
        self.assertIsNotNone(search)
        self.assertEqual(search.get("type"), "search")
        self.assertEqual(search.get("maxlength"), "100")
        self.assertIn(search["id"], self.markup.labels, "Search needs an explicit label")


if __name__ == "__main__":
    unittest.main()
