"""Keep a hash-based CSP in the HTML synchronized with its inline JS/CSS.

Run with --write after intentional changes; CI checks without rewriting files.
Frame restrictions and HSTS must additionally be sent by the HTTPS server.
"""
import argparse
import base64
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
META = re.compile(r'(<meta http-equiv="Content-Security-Policy" content=")[^"]*(">)')


class InlineAssets(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.blocks = {"script": [], "style": []}
        self.kind = None
        self.content = []

    def handle_starttag(self, tag, attrs):
        if tag in self.blocks and not dict(attrs).get("src"):
            self.kind, self.content = tag, []

    def handle_data(self, data):
        if self.kind:
            self.content.append(data)

    def handle_endtag(self, tag):
        if tag == self.kind:
            self.blocks[tag].append("".join(self.content))
            self.kind, self.content = None, []


def policy(html):
    assets = InlineAssets()
    assets.feed(html)

    def hashes(kind):
        return " ".join("'sha256-" + base64.b64encode(hashlib.sha256(block.encode()).digest()).decode() + "'"
                        for block in assets.blocks[kind])

    return ("default-src 'self'; "
            f"script-src 'self' {hashes('script')}; script-src-attr 'none'; "
            f"style-src 'self' {hashes('style')}; style-src-attr 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'self'; form-action 'none'")


def check(root=ROOT):
    html = (root / "index.html").read_text()
    matches = list(META.finditer(html))
    if len(matches) != 1 or matches[0].group(0) != matches[0].group(1) + policy(html) + matches[0].group(2):
        raise ValueError("CSP is missing or stale: run python3 scripts/security_policy.py --write")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        path = ROOT / "index.html"
        html = path.read_text()
        updated, count = META.subn(lambda match: match[1] + policy(html) + match[2], html)
        if count != 1:
            raise SystemExit("Expected one CSP meta tag")
        path.write_text(updated)
    check()
    print("Hash-based CSP OK")


if __name__ == "__main__":
    main()
