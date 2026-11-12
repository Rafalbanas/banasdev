import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]

class SiteIntegrityParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.h1_count = 0
        self.buttons = []
        self.links = []
        self.sources = []
        self.html_lang = None
        self.fragments = []
        self.all_ids = set()

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == 'html':
            self.html_lang = attrs_dict.get('lang')

        if tag == 'h1':
            self.h1_count += 1

        if tag == 'button':
            self.buttons.append(attrs_dict)

        if tag == 'a':
            self.links.append(attrs_dict)

        if attrs_dict.get('src'):
            self.sources.append(attrs_dict['src'])

        if 'id' in attrs_dict:
            self.ids.append(attrs_dict['id'])
            self.all_ids.add(attrs_dict['id'])

        if 'href' in attrs_dict:
            href = attrs_dict['href']
            if href.startswith('#'):
                self.fragments.append(href[1:])

class TestSiteIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        content = (ROOT / 'index.html').read_text(encoding='utf-8')

        cls.parser = SiteIntegrityParser()
        cls.parser.feed(content)

        # Get all known IDs for fragment validation
        cls.known_ids = cls.parser.all_ids

    def test_no_duplicate_ids(self):
        # ids list contains all ids found. Every entry should be unique.
        self.assertEqual(len(self.parser.ids), len(self.parser.all_ids),
                         f"Duplicate IDs found: {[x for x in self.parser.ids if self.parser.ids.count(x) > 1]}")

    def test_h1_count(self):
        self.assertEqual(self.parser.h1_count, 1, f"Expected exactly one h1 tag, found {self.parser.h1_count}")

    def test_html_lang(self):
        self.assertEqual(self.parser.html_lang, 'pl', f"Expected lang='pl', got '{self.parser.html_lang}'")

    def test_button_types(self):
        for btn in self.parser.buttons:
            expected = 'submit' if btn.get('id') == 'terminalRun' else 'button'
            self.assertEqual(btn.get('type'), expected, f"Incorrect explicit button type: {btn}")

    def test_blank_links_noopener(self):
        for link in self.parser.links:
            if link.get('target') == '_blank':
                rel = link.get('rel', '')
                self.assertIn('noopener', rel.split(), f"Link with target='_blank' does not have rel='noopener' token: {link}")

    def test_fragment_existence(self):
        for fragment in self.parser.fragments:
            self.assertIn(fragment, self.known_ids, f"Fragment '{fragment}' has no matching ID")

    def test_local_assets_exist(self):
        for src in self.parser.sources:
            parsed = urlsplit(src)
            if parsed.scheme or parsed.netloc:
                continue
            path = ROOT / unquote(parsed.path).lstrip('/')
            self.assertTrue(path.is_file(), f"Asset {src} not found at {path}")

if __name__ == '__main__':
    unittest.main()
