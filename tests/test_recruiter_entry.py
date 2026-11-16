import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "index.html"

class RecruiterEntryParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hero_actions_elements = []
        self.nav_links = []
        self.current_container = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = {k: v for k, v in attrs}
        if tag == "div" and "hero-actions" in attrs_dict.get("class", ""):
            self.current_container = "hero-actions"
        elif tag == "nav" and "site-sections" in attrs_dict.get("class", ""):
            self.current_container = "nav-site-sections"

        if self.current_container == "hero-actions" and tag == "a":
            self.hero_actions_elements.append(attrs_dict)
        elif self.current_container == "nav-site-sections" and tag == "a":
            self.nav_links.append(attrs_dict)

    def handle_endtag(self, tag):
        if tag == "div" and self.current_container == "hero-actions":
            self.current_container = None
        elif tag == "nav" and self.current_container == "nav-site-sections":
            self.current_container = None

class TestRecruiterEntry(unittest.TestCase):
    def setUp(self):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.parser = RecruiterEntryParser()
        self.parser.feed(content)

    def test_hero_actions_linkedin(self):
        primary_links = [
            e for e in self.parser.hero_actions_elements
            if "primary" in e.get("class", "").split() and
               e.get("href") == "https://linkedin.com/in/rafał-banaś-251583152" and
               e.get("target") == "_blank" and
               "noopener" in e.get("rel", "")
        ]
        self.assertEqual(len(primary_links), 1)

    def test_links_presence(self):
        all_links = self.parser.hero_actions_elements + self.parser.nav_links
        hobby_link = next((e for e in all_links if e.get("href") == "hobby.html"), None)
        projekty_link = next((e for e in all_links if e.get("href") == "projekty.html"), None)

        self.assertIsNotNone(hobby_link)
        self.assertIn("data-hobby-link", hobby_link.keys())

        self.assertIsNotNone(projekty_link)
        self.assertIn("data-story-link", projekty_link.keys())

    def test_nav_current_page(self):
        current = next((e for e in self.parser.nav_links if e.get("href") == "index.html"), None)
        self.assertIsNotNone(current)
        self.assertEqual(current.get("aria-current"), "page")

if __name__ == "__main__":
    unittest.main()
