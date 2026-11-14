"""Browser checks for the collaboration route; optional screenshots.

Run: python3 scripts/check_hiring_story.py [--screenshots DIRECTORY]
Requires Playwright and Chromium.
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


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT))
    )
    Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                for width in (360, 768, 1440):
                    page = browser.new_page(
                        viewport={"width": width, "height": 1000},
                        reduced_motion="reduce",
                    )
                    page.set_default_timeout(30000)
                    page.goto(url, wait_until="networkidle")
                    for language in ("pl", "en"):
                        page.locator(f'[data-lang="{language}"]').click()
                        for light in (False, True):
                            current = page.locator("html").evaluate(
                                "e => e.classList.contains('light')"
                            )
                            if current != light:
                                page.locator("#themeToggle").click()
                            expect(page.locator(".work-card")).to_have_count(3)
                            expect(page.locator(".contact-modes li")).to_have_count(3)
                            expect(page.locator(".contact-modes li").first).to_have_text(
                                "Employment" if language == "en" else "Etat"
                            )
                            page.locator(".hero-work-link").click()
                            expect(page).to_have_url(url + "/#work")
                            page.locator("#projectSearch").fill("BM25")
                            expect(page.locator("#homelab")).to_be_hidden()
                            evidence = page.locator('.work-evidence[href="#homelab"]')
                            evidence.focus()
                            page.keyboard.press("Enter")
                            expect(page.locator("#homelab")).to_be_visible()
                            expect(page.locator("#projectSearch")).to_have_value("")
                            assert page.evaluate(
                                "document.documentElement.scrollWidth <= innerWidth"
                            ), f"Overflow at {width}px / {language} / light={light}"
                            if args.screenshots and language == "pl" and not light and width != 768:
                                for section in ("work", "contact"):
                                    page.evaluate(
                                        """id => window.scrollTo({top:
                                        document.getElementById(id).getBoundingClientRect().top
                                        + scrollY - 90, behavior: 'instant'})""", section
                                    )
                                    page.screenshot(
                                        path=str(args.screenshots / f"{section}-{width}.png"),
                                        timeout=60000, animations="disabled",
                                    )
                            print(f"Hiring route OK: {width}px / {language} / light={light}",
                                  flush=True)
                    page.close()
                context = browser.new_context(java_script_enabled=False)
                page = context.new_page()
                page.goto(url)
                expect(page.locator("#work-title")).to_have_text(
                    "W czym mogę pomóc Twojemu zespołowi?"
                )
                expect(page.locator(".contact-modes li").first).to_have_text("Etat")
                expect(page.locator('[data-email-text]').first).to_contain_text("contact")
                context.close()
                print("Hiring route OK: Polish fallback without JavaScript", flush=True)
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    run()
