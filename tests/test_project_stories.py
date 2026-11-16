"""Static contracts for the second public page and release integration."""
from pathlib import Path
import re
import unittest

from scripts.check_site import Site
from scripts.package import PUBLIC_FILES
from deploy.deploy import FILES

ROOT = Path(__file__).resolve().parents[1]


class ProjectStoryTests(unittest.TestCase):
    def test_public_assets_and_release_allowlist_match(self):
        for name in ("projekty.html", "hobby.html", "assets/project-stories.css", "assets/project-stories.js",
                     "assets/ride-planner.css", "assets/ride-planner.js", "assets/hobbies.css", "assets/hobbies.js"):
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())
                self.assertIn(name, PUBLIC_FILES)
                self.assertIn("public/" + name, FILES)

    def test_story_anchors_and_safe_static_page(self):
        html = (ROOT / "projekty.html").read_text()
        page = Site()
        page.feed(html)
        self.assertTrue({"cvtailor", "cycling", "plates", "main"} <= page.ids)
        self.assertEqual(len(page.scripts), 0, "New page needs no inline script")
        self.assertEqual(html.count("<h1 "), 1)
        self.assertIn('http-equiv="Content-Security-Policy"', html)
        self.assertNotIn("unsafe-inline", html)
        for language in ("lang-pl", "lang-en"):
            self.assertGreater(html.count('class="' + language + '"'), 20)
        for source in ("https://cv.banas.dev/", "https://cycling.banas.dev/", "https://plates.banas.dev"):
            self.assertIn(source, page.urls)

    def test_hobby_page_has_a_separate_entry_and_no_inline_scripts(self):
        html = (ROOT / "hobby.html").read_text()
        page = Site()
        page.feed(html)
        self.assertTrue({"hobbies-title", "main", "ridePlanner", "rideDuration", "rideTimeline",
                         "hobbyDataStatus", "storyLanguage", "storyTheme"} <= page.ids)
        self.assertEqual(page.scripts, [])
        self.assertIn('data-page="hobbies"', html)
        self.assertIn('aria-current="page"', html)
        self.assertIn('href="index.html"', html)
        self.assertIn("https://www.strava.com/athletes/9698049", page.urls)

    def test_public_page_scripts_opt_out_of_cloudflare_rewriting(self):
        for name in ("projekty.html", "hobby.html"):
            scripts = re.findall(r"<script\b[^>]*>", (ROOT / name).read_text())
            self.assertTrue(scripts)
            for script in scripts:
                self.assertIn('data-cfasync="false"', script, name)
