"""Contracts for the bilingual, evidence-linked collaboration introduction."""
from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HiringMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_work = False
        self.cards = 0
        self.evidence = []
        self.work_labels = set()
        self.contact_labels = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "section" and attrs.get("id") == "work":
            self.in_work = True
        classes = attrs.get("class", "").split()
        if self.in_work:
            if tag == "article" and "work-card" in classes:
                self.cards += 1
            if tag == "a" and "work-evidence" in classes:
                self.evidence.append(attrs.get("href"))
        key = attrs.get("data-i18n", "")
        if key.startswith("work."):
            self.work_labels.add(key)
        if key.startswith("contact."):
            self.contact_labels.add(key)

    def handle_endtag(self, tag):
        if tag == "section":
            self.in_work = False


class HiringStoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text()
        cls.markup = HiringMarkup()
        cls.markup.feed(cls.html)

    def test_work_introduction_precedes_the_long_resume(self):
        self.assertLess(self.html.index('id="work"'), self.html.index('id="experience"'))
        self.assertIn('aria-labelledby="work-title"', self.html)
        self.assertEqual(self.markup.cards, 3)

    def test_each_area_links_to_existing_evidence(self):
        self.assertEqual(len(self.markup.evidence), 3)
        self.assertEqual(
            set(self.markup.evidence), {"#experience", "#projects", "#homelab"}
        )
        for href in self.markup.evidence:
            self.assertTrue(href and href.startswith("#"))
            self.assertIn(f'id="{href[1:]}"', self.html)

    def test_work_copy_uses_the_existing_translation_system(self):
        self.assertIn("work.title", self.markup.work_labels)
        self.assertGreaterEqual(len(self.markup.work_labels), 10)
        # PL/EN completeness and Polish fallback equality are also covered by
        # test_portfolio; avoid a second bespoke translation parser here.

    def test_existing_contact_channels_are_preserved(self):
        self.assertEqual(self.html.count("data-public-email>"), 2)
        self.assertIn('href="https://github.com/Rafalbanas"', self.html)
        self.assertIn('id="contact"', self.html)

    def test_contact_explains_how_to_start_a_conversation(self):
        self.assertTrue({
            "contact.employment", "contact.briefTitle",
            "contact.briefProject", "contact.briefRole",
        }.issubset(self.markup.contact_labels))


if __name__ == "__main__":
    unittest.main()
