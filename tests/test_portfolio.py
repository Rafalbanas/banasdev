"""Content contracts for the static, bilingual portfolio (requires Node.js)."""
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def flatten(value, prefix=""):
    result = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            result.update(flatten(item, path))
        else:
            result[path] = item
    return result


class PortfolioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text()
        source = cls.html.split("const translations = ", 1)[1]
        source = source.split("\n            const projectLinks", 1)[0].strip().removesuffix(";")
        output = subprocess.run(
            ["node", "-e", f"console.log(JSON.stringify({source}))"],
            check=True, capture_output=True, text=True,
        )
        cls.copy = {lang: flatten(data) for lang, data in json.loads(output.stdout).items()}
        cls.elements = Elements()
        cls.elements.feed(cls.html)

    def test_translation_keys_and_references(self):
        self.assertEqual(self.copy["pl"].keys(), self.copy["en"].keys())
        for _, attrs in self.elements.elements:
            paths = [attrs["data-i18n"]] if "data-i18n" in attrs else []
            for item in attrs.get("data-i18n-attr", "").split(";"):
                if ":" in item:
                    paths.append(item.split(":", 1)[1].strip())
            for path in paths:
                for lang in ("pl", "en"):
                    with self.subTest(lang=lang, path=path):
                        self.assertTrue(self.copy[lang].get(path))

    def test_polish_fallback_matches_translations(self):
        matches = re.finditer(
            r'<([\w-]+)\b[^>]*data-i18n="([^"]+)"[^>]*>([^<]*)</\1>', self.html
        )
        count = 0
        for match in matches:
            count += 1
            with self.subTest(key=match[2]):
                self.assertEqual(" ".join(unescape(match[3]).split()), self.copy["pl"][match[2]])
        self.assertGreater(count, 100)

    def test_current_profile_and_honest_project_scope(self):
        self.assertNotRegex(self.html, r"student(?:em)? informatyki|computer science student")
        for lang in ("pl", "en"):
            copy = self.copy[lang]
            for fact in ("Tier 2", "EMEA", "WAVE PTX"):
                self.assertIn(fact, copy["hero.subtitle"])
            self.assertIn("2026", copy["education.uek"])
            self.assertIn("B2", copy["experience.motorola4"])
            self.assertIn("BM25", copy["projects.resumeText"])
            self.assertIn("Open WebUI", copy["projects.chatText"])
            self.assertNotEqual(copy["projects.resumeDemoCta"], "Demo")
            self.assertIn("MMP20", copy["projects.cyclingText"])

    def test_public_project_links_and_contact_preserved(self):
        links = {attrs.get("href"): attrs for tag, attrs in self.elements.elements if tag == "a"}
        for url in (
            "https://plates.banas.dev",
            "https://github.com/Rafalbanas/automatic_plate_number_recognition",
            "https://cycling.banas.dev",
            "https://github.com/Rafalbanas/Cycling",
            "https://cv.banas.dev/",
            "https://github.com/Rafalbanas/ai-resume-tailoring-platform",
            "https://github.com/Rafalbanas/chat",
        ):
            with self.subTest(url=url):
                self.assertIn(url, links)
                self.assertNotIn("aria-disabled", links[url])
        self.assertNotIn("https://n8n.banas.dev", links)
        self.assertEqual(self.html.count("data-public-email>"), 2)
        self.assertIn('const mailbox = "contact";', self.html)
        self.assertIn('link.href = ["mail", "to", ":", address].join("");', self.html)


if __name__ == "__main__":
    unittest.main()
