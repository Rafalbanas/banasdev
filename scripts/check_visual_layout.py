"""Optional responsive checks; requires Playwright and Chromium.

Run: python3 scripts/check_visual_layout.py [--screenshots DIRECTORY]
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def check_page(page):
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Horizontal overflow"
    expect(page.locator("#hero-title")).to_be_visible()
    expect(page.locator("#profilePhoto")).to_be_visible()
    for section in ("about", "experience", "projects", "skills", "weather", "contact"):
        expect(page.locator(f"#{section}")).to_be_visible()

    cards = page.locator("#projects .project-card")
    total = cards.count()
    search = page.locator("#projectSearch")
    search.fill("BM25")
    expect(page.locator("#projects .project-card:visible")).to_have_count(1)
    search.fill("")
    expect(page.locator("#projects .project-card:visible")).to_have_count(total)

    menu = page.locator("#mobileMenuToggle")
    if menu.is_visible():
        menu.click()
        expect(menu).to_have_attribute("aria-expanded", "true")
        link = page.locator('.nav-links a[href="#projects"]')
        link.click()
        expect(menu).to_have_attribute("aria-expanded", "false")
        expect(link).to_have_attribute("aria-current", "location")


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshots", type=Path, help="Optional screenshot directory")
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(timeout=20000)
            try:
                for width in (360, 768, 1440):
                    context = browser.new_context(
                        viewport={"width": width, "height": 900}, reduced_motion="reduce"
                    )
                    try:
                        page = context.new_page()
                        page.set_default_timeout(10000)
                        page.goto(f"http://127.0.0.1:{server.server_port}",
                                  wait_until="domcontentloaded", timeout=30000)
                        expect(page.locator("#projectTools")).to_be_visible()
                        for language in ("pl", "en"):
                            page.locator(f'[data-lang="{language}"]').click()
                            expect(page.locator("html")).to_have_attribute("lang", language)
                            for theme in ("dark", "light"):
                                is_light = page.evaluate("document.documentElement.classList.contains('light')")
                                if is_light != (theme == "light"):
                                    page.locator("#themeToggle").click()
                                expect(page.locator("#themeToggle")).to_have_attribute(
                                    "aria-pressed", str(theme == "light").lower()
                                )
                                check_page(page)
                                if args.screenshots and language == "pl" and theme == "dark" and width in (360, 1440):
                                    page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
                                    page.screenshot(path=str(args.screenshots / f"pl_dark_{width}.png"), full_page=True)
                                print(f"Layout OK: {width}px / {language} / {theme}", flush=True)
                    finally:
                        context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    run()
