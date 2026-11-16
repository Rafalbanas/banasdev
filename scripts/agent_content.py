"""Generate readable Markdown and check sitemap coverage from public HTML pages."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

if __package__:
    from .package import PUBLIC_FILES
else:
    from package import PUBLIC_FILES

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://banas.dev/"
NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


def canonical(name):
    return ORIGIN if name == "index.html" else urljoin(ORIGIN, name)


class Markdown(HTMLParser):
    """Extract published Polish content, excluding controls and simulated terminals."""
    def __init__(self, base):
        super().__init__()
        self.base = base
        self.stack = []
        self.output = []
        self.in_main = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if not self.in_main and tag != "main":
            return
        if tag == "main":
            self.in_main = True
        skip = (not self.in_main or (self.stack and self.stack[-1][1]) or
                tag in ("script", "style", "button", "select", "form", "canvas", "svg", "nav", "table") or
                "lang-en" in attrs.get("class", "").split() or
                attrs.get("id") in ("weather", "ridePlanner", "pagePetControls") or
                any(word.startswith("terminal") or word in ("lab-terminal", "lab-strip")
                    for word in attrs.get("class", "").split()))
        void = tag in ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr")
        if not skip:
            if re.fullmatch("h[1-6]", tag):
                self.output.append("\n\n" + "#" * int(tag[1]) + " ")
            elif tag in ("p", "section", "article", "details", "div"):
                self.output.append("\n\n")
            elif tag == "li":
                self.output.append("\n- ")
            elif tag == "a":
                self.output.append("[")
            elif tag == "br":
                self.output.append(" ")
            elif tag == "img" and attrs.get("alt"):
                self.output.append(attrs["alt"])
        if not void:
            self.stack.append((tag, bool(skip), attrs.get("href")))

    def handle_endtag(self, tag):
        if not self.stack or tag not in [item[0] for item in self.stack]:
            return
        while self.stack:
            current, skip, href = self.stack.pop()
            if current == tag:
                break
        if not skip:
            if tag == "a":
                self.output.append("](" + urljoin(self.base, href or "") + ")")
            elif re.fullmatch("h[1-6]", tag) or tag in ("p", "section", "article", "details", "div"):
                self.output.append("\n\n")
            elif tag in ("strong", "span", "small", "time"):
                self.output.append(" ")
        if tag == "main":
            self.in_main = False

    def handle_data(self, data):
        if self.in_main and self.stack and not self.stack[-1][1]:
            self.output.append(re.sub(r"\s+", " ", data))

    def text(self):
        text = "".join(self.output)
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text + f"\n\n---\nŹródło: {self.base}\n"


def check_or_write(root=ROOT, write=False):
    pages = [name for name in PUBLIC_FILES if name.endswith(".html")]
    expected = {canonical(name) for name in pages}
    sitemap = ET.parse(root / "sitemap.xml").getroot()
    locations = [node.text for node in sitemap.findall(f"{{{NAMESPACE}}}url/{{{NAMESPACE}}}loc")]
    if sitemap.tag != f"{{{NAMESPACE}}}urlset" or len(locations) != len(expected) or set(locations) != expected:
        raise ValueError("sitemap.xml must list each canonical public HTML page exactly once")
    if f"Sitemap: {ORIGIN}sitemap.xml" not in (root / "robots.txt").read_text().splitlines():
        raise ValueError("robots.txt must reference the sitemap")
    for name in pages:
        parser = Markdown(canonical(name))
        parser.feed((root / name).read_text())
        text = parser.text()
        if name == "hobby.html":
            text += "\n## Pogoda na rower\nOcena wymaga aktualnych danych Open-Meteo i GIOŚ oraz JavaScript. " \
                    "Otwórz panel na stronie HTML; ten dokument nie zawiera prognozy ani rekomendacji na żywo.\n"
        path = root / Path(name).with_suffix(".md")
        if write:
            path.write_text(text)
        elif not path.is_file() or path.read_text() != text:
            raise ValueError(f"{path.name} missing or stale: python3 scripts/agent_content.py --write")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    check_or_write(write=args.write)
    print("Sitemap coverage, robots reference and generated Markdown OK")
