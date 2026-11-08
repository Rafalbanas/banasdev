import unittest
import threading
import time
import functools
from pathlib import Path
import os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]

class TestServer(ThreadingHTTPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.port = self.server_port

def run_test():
    server = TestServer(("127.0.0.1", 0), functools.partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    time.sleep(1)
    server.port = server.server_port
    host = f"http://127.0.0.1:{server.port}"

    page_errors = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            def test_standard():
                try:
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 720},
                        reduced_motion="reduce"
                    )
                    page = context.new_page()
                    page.on('pageerror', lambda error: page_errors.append(str(error)))
                    page.goto(host, wait_until="domcontentloaded")

                    btn = page.locator("#backToTop")
                    expect(btn).to_be_hidden()

                    page.evaluate("window.scrollTo(0, window.innerHeight + 200)")
                    expect(btn).to_be_visible()

                    # Use focus + Enter as per requirements
                    page.evaluate("history.replaceState(null, '', '#projects')")
                    btn.focus()
                    page.keyboard.press("Enter")

                    expect(page.locator("h1")).to_be_focused()
                    expect(btn).to_be_hidden()
                    assert page.evaluate("window.scrollY") == 0
                    assert page.evaluate('location.hash') == '#projects'

                    context.close()
                except Exception as e:
                    page_errors.append(f"test_standard: {e}")

            def test_mobile():
                try:
                    context = browser.new_context(
                        viewport={"width": 360, "height": 800},
                        color_scheme="dark"
                    )
                    page = context.new_page()
                    page.on('pageerror', lambda error: page_errors.append(str(error)))
                    page.goto(host)
                    page.evaluate("window.scrollTo(0, window.innerHeight + 200)")

                    btn = page.locator("#backToTop")
                    expect(btn).to_be_visible()

                    box = btn.bounding_box()
                    assert box["width"] >= 44 and box["height"] >= 44
                    assert box["x"] >= 0 and box["y"] >= 0
                    assert box["x"] + box["width"] <= 360
                    assert box["y"] + box["height"] <= 800
                    context.close()
                except Exception as e:
                    page_errors.append(f"test_mobile: {e}")

            def test_no_js():
                try:
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 720},
                        java_script_enabled=False
                    )
                    page = context.new_page()
                    page.on('pageerror', lambda error: page_errors.append(str(error)))
                    page.goto(host)

                    expect(page.locator('#backToTop')).to_be_hidden()
                    email = page.locator('[data-email-text]').first
                    assert "contact [at] banas [dot] dev" in email.inner_text()
                    context.close()
                except Exception as e:
                    page_errors.append(f"test_no_js: {e}")

            def test_reduced_motion_no_pref():
                try:
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 720},
                        reduced_motion="no-preference"
                    )
                    page = context.new_page()
                    page.on('pageerror', lambda error: page_errors.append(str(error)))
                    page.goto(host)
                    page.evaluate("window.scrollTo(0, window.innerHeight + 200)")

                    btn = page.locator("#backToTop")
                    expect(btn).to_be_visible()
                    btn.focus()
                    page.keyboard.press("Enter")
                    expect(btn).to_be_hidden()
                    expect(page.locator("h1")).to_be_focused()
                    context.close()
                except Exception as e:
                    page_errors.append(f"test_reduced_motion_no_pref: {e}")

            def test_theme_and_locale():
                try:
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 720},
                        color_scheme="dark"
                    )
                    page = context.new_page()
                    page.on('pageerror', lambda error: page_errors.append(str(error)))
                    page.goto(host)
                    page.evaluate("window.scrollTo(0, window.innerHeight + 200)")
                    btn = page.locator("#backToTop")
                    expect(btn).to_be_visible()

                    # Test Themes
                    for theme in ["light", "dark"]:
                        body_class = page.locator("body").get_attribute("class")

                        if theme == "light" and "light" not in body_class:
                            page.click("#themeToggle")
                            time.sleep(0.5)
                        elif theme == "dark" and "light" in body_class:
                            page.click("#themeToggle")
                            time.sleep(0.5)

                        # Test Locales
                        for lang in ["pl", "en"]:
                            lang_btn = page.locator(f"button[data-lang='{lang}']")
                            lang_btn.click()
                            time.sleep(0.5)

                            expect(btn).to_have_text("Powrót na górę" if lang == "pl" else "Back to top")

                            page.evaluate("window.scrollTo(0, window.innerHeight + 200)")

                    context.close()
                except Exception as e:
                    page_errors.append(f"test_theme_and_locale: {e}")

            test_standard()
            test_mobile()
            test_no_js()
            test_reduced_motion_no_pref()
            test_theme_and_locale()

            browser.close()

    except Exception as e:
        print(f"Test failed: {e}")
        raise
    finally:
        server.shutdown()
        server.server_close()

    if page_errors:
        print("\n".join(page_errors))
        exit(1)

if __name__ == "__main__":
    run_test()
