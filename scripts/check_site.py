"""Check local assets, fragments and inline JavaScript without external APIs."""
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit
if __package__:
    from . import security_policy
    from . import agent_content
else:
    import security_policy
    import agent_content


class Site(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.urls = []
        self.scripts = []
        self.script = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            if attrs["id"] in self.ids:
                raise ValueError("Duplicate HTML id: " + attrs["id"])
            self.ids.add(attrs["id"])
        for name in ("src", "href"):
            if attrs.get(name):
                self.urls.append(attrs[name])
        if tag == "script" and not attrs.get("src"):
            self.script = []

    def handle_data(self, data):
        if self.script is not None:
            self.script.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.script is not None:
            self.scripts.append("".join(self.script))
            self.script = None


def check(root):
    security_policy.check(root)
    agent_content.check_or_write(root)
    pages = {}
    for path in root.glob("*.html"):
        site = Site()
        site.feed(path.read_text())
        pages[path.name] = site
    external_scripts = set()
    for name, site in pages.items():
        for url in site.urls:
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc:
                continue
            target = unquote(parsed.path).lstrip("/")
            if target and not (root / target).is_file():
                raise ValueError("Missing asset: " + url)
            destination = pages.get(target or name)
            if parsed.fragment and destination and parsed.fragment not in destination.ids:
                raise ValueError("Missing fragment: " + url)
            if target.endswith(".js"):
                external_scripts.add(root / target)
    with tempfile.TemporaryDirectory() as directory:
        for index, script in enumerate(script for site in pages.values() for script in site.scripts):
            path = Path(directory) / f"inline-{index}.js"
            path.write_text(script)
            subprocess.run(["node", "--check", str(path)], check=True)
    for path in sorted(external_scripts):
        subprocess.run(["node", "--check", str(path)], check=True)
    print("HTML pages, assets, cross-page anchors and JavaScript OK")


if __name__ == "__main__":
    check(Path(__file__).resolve().parents[1])
