"""Optional Chromium checks: python3 scripts/check_project_explorer.py.

Requires Playwright and its Chromium browser. No live GitHub or project APIs.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ("cycling", "plates", "resume", "chat", "lanari", "thesis",
            "automation", "banas", "homelab")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def check():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}"
    errors, external, violations = [], [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(reduced_motion="reduce")
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda request: external.append(request.url)
                        if not request.url.startswith(url + "/") else None)
                page.on("console", lambda message: violations.append(message.text)
                        if "Content Security Policy" in message.text else None)
                page.goto(url, wait_until="networkidle")
                expect(page.locator("#projects .project-card")).to_have_count(9)
                expect(page.locator("#projectResults")).to_have_text("Projekty: 9 z 9")

                # All nine studies use the same accessible, keyboard-operated model.
                for project in PROJECTS:
                    study = page.locator(f'[data-case-study="{project}"]')
                    study.locator("summary").click()
                    tabs = study.get_by_role("tab")
                    expect(tabs).to_have_count(3)
                    expect(tabs.nth(0)).to_have_attribute("aria-selected", "true")
                    expect(study.get_by_role("tabpanel")).to_have_count(1)
                    tabs.nth(0).focus()
                    page.keyboard.press("ArrowRight")
                    expect(tabs.nth(1)).to_be_focused()
                    expect(tabs.nth(1)).to_have_attribute("aria-selected", "true")
                    expect(study.locator('[data-case-panel="flow"]')).to_be_visible()
                    page.keyboard.press("End")
                    expect(tabs.nth(2)).to_be_focused()
                    page.keyboard.press("ArrowRight")
                    expect(tabs.nth(0)).to_be_focused()
                    page.keyboard.press("ArrowLeft")
                    expect(tabs.nth(2)).to_be_focused()
                    page.keyboard.press("Home")
                    expect(tabs.nth(0)).to_be_focused()
                    tabs.nth(2).click()
                    expect(study.locator('[data-case-panel="quality"]')).to_be_visible()
                    # Translation must not reset the active tab or open state.
                    page.locator('[data-lang="en"]').click()
                    expect(tabs.nth(2)).to_have_text("Validation & limitations")
                    expect(tabs.nth(2)).to_have_attribute("aria-selected", "true")
                    expect(study).to_have_attribute("open", "")
                    page.locator('[data-lang="pl"]').click()
                    study.locator("summary").click()

                # Search includes the study content, including both languages.
                search = page.locator("#projectSearch")
                visible = page.locator("#projects .project-card:visible")
                search.fill("Alembic")
                expect(visible).to_have_count(1)
                expect(visible).to_have_attribute("data-project-id", "lanari")
                page.locator('[data-lang="en"]').click()
                expect(visible).to_have_count(1)
                search.fill("RTX 3060")
                expect(visible).to_have_count(1)
                expect(visible).to_have_attribute("data-project-id", "homelab")
                search.fill("no-such-project-12345")
                expect(page.locator("#projectEmpty")).to_be_visible()
                page.locator("[data-project-reset]").click()
                expect(search).to_be_focused()
                expect(visible).to_have_count(9)

                page.locator('[data-project-filter="automation"]').click()
                page.locator('[data-project-id="homelab"] .tag button', has_text="Ollama").click()
                expect(search).to_have_value("Ollama")
                expect(search).to_be_focused()
                expect(page.locator('[data-project-filter="all"]')).to_have_attribute("aria-pressed", "true")
                expect(visible).to_have_count(3)
                page.locator("#projectReset").click()
                page.locator('[data-project-id="cycling"] .tag button').first.click()
                expect(visible).to_have_count(2)
                page.locator('[data-lang="pl"]').click()
                expect(visible).to_have_count(2)
                page.locator("#projectReset").click()

                # List/cards and filters are independent; both layouts work on phones.
                for width in (320, 360, 768, 1440):
                    page.set_viewport_size({"width": width, "height": 900})
                    for lang in ("pl", "en"):
                        page.locator(f'[data-lang="{lang}"]').click()
                        for light in (True, False):
                            if page.locator("body").evaluate("e => e.classList.contains('light')") != light:
                                page.locator("#themeToggle").click()
                            for view in ("list", "grid"):
                                page.locator(f'[data-project-view="{view}"]').click()
                                expect(page.locator(f'[data-project-view="{view}"]')).to_have_attribute("aria-pressed", "true")
                                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (width, lang, light, view)
                                if view == "list":
                                    assert page.locator("#projectMore").evaluate(
                                        "e => getComputedStyle(e).gridTemplateColumns.split(' ').length") == 1
                                study = page.locator('[data-case-study="homelab"]')
                                study.locator("summary").click()
                                study.get_by_role("tab").nth(1).click()
                                expect(study.locator(".case-flow")).to_be_visible()
                                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                                study.locator("summary").click()
                page.close()

                # Every panel is statically available without JavaScript; controls are not fake.
                page = browser.new_page(java_script_enabled=False, viewport={"width": 360, "height": 800})
                page.goto(url)
                expect(page.locator("#projectTools")).to_be_hidden()
                expect(page.locator('[role="tablist"]')).to_have_count(0)
                expect(page.locator("#projects .project-card")).to_have_count(9)
                for project in PROJECTS:
                    study = page.locator(f'[data-case-study="{project}"]')
                    study.locator("summary").click()
                    expect(study.locator(".case-panel:visible")).to_have_count(3)
                homelab = page.locator('[data-project-id="homelab"]')
                expect(homelab.locator("a")).to_have_count(0)
                assert "KVM / libvirt" in homelab.inner_text()
                assert page.locator("[data-email-text]").first.inner_text() == "contact [at] banas [dot] dev"
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                assert not errors, errors
                assert not external, external
                assert not violations, violations
                print("Project explorer OK: 9 studies, keyboard tabs, filters/tags, PL/EN, 4 widths, 2 themes, cards/list, no JS, privacy, no external requests")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


if __name__ == "__main__":
    check()
