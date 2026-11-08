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


def check_headless_lab(page):
    study = page.locator('[data-case-study="homelab"]')
    expect(page.locator('[data-project-id="homelab"] .lab-specs')).to_contain_text("Ryzen 5 5500")
    expect(page.locator('[data-project-id="homelab"] .lab-specs')).to_contain_text("30,7 GiB")
    study.locator("summary").click()
    study.get_by_role("tab").first.click()
    controls = page.locator("#labModeSwitch")
    expect(controls).to_be_visible()
    expect(page.locator("#lab-route-title")).to_have_text("Mac → jumphost Mikrus → homelab")
    gui_button = controls.locator('[data-lab-mode="gui"]')
    headless_button = controls.locator('[data-lab-mode="headless"]')
    expect(page.locator("#labModeHeadless")).to_be_visible()
    expect(page.locator("#labModeGui")).to_be_hidden()
    expect(page.locator("#labVramMeter")).to_have_attribute("value", "8899")
    gui_button.focus()
    page.keyboard.press("Enter")
    expect(gui_button).to_be_focused()
    expect(gui_button).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#labModeGui")).to_be_visible()
    expect(page.locator("#labModeHeadless")).to_be_hidden()
    expect(page.locator("#labVramMeter")).to_have_attribute("value", "9088")
    expect(page.locator("#labSnapshotOther")).to_have_text("230 MiB")
    expect(page.locator("#labSnapshotFree")).to_have_text("3200 MiB")
    page.locator('#labReadingSwitch [data-lab-mode="headless"]').click()
    expect(headless_button).to_have_attribute("aria-pressed", "true")
    expect(gui_button).to_have_attribute("aria-pressed", "false")
    expect(page.locator("#labVramMeter")).to_have_attribute("value", "8899")
    page.locator('#labReadingSwitch [data-lab-mode="gui"]').click()
    expect(gui_button).to_have_attribute("aria-pressed", "true")

    gui = page.locator("#labVramGui")
    headless = page.locator("#labVramHeadless")
    result = page.locator("#labVramResult")
    expect(gui).to_have_value("")
    expect(headless).to_have_value("")
    page.locator("#labUseSnapshot").click()
    expect(result).to_contain_text("189 MiB")
    expect(result).to_contain_text("2,08%")
    page.locator('[data-lang="en"]').click()
    expect(page.locator("#lab-route-title")).to_have_text("Mac → Mikrus jumphost → homelab")
    expect(page.locator('[data-project-id="homelab"] .lab-specs')).to_contain_text("6 cores / 12 threads")
    expect(page.locator('[data-project-id="homelab"] .lab-specs')).to_contain_text("30.7 GiB")
    expect(gui_button).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#labSnapshotMode")).to_contain_text("GUI · 9088")
    expect(gui).to_have_value("9088")
    expect(headless).to_have_value("8899")
    expect(result).to_contain_text("2.08%")
    gui.fill("0")
    headless.fill("0")
    expect(result).to_contain_text("0 MiB difference")
    headless.fill("1")
    expect(result).to_contain_text("1 MiB more")
    for invalid in ("-1", "12289", "8899.5"):
        gui.fill(invalid)
        expect(result).to_contain_text("whole numbers")
        expect(gui).to_have_attribute("aria-invalid", "true")
    gui.fill("")
    expect(result).to_contain_text("Enter two readings")
    gui.fill("12288")
    headless.fill("0")
    expect(result).to_contain_text("100%")
    expect(gui).to_have_attribute("aria-invalid", "false")

    # Both simulated modes remain usable on a phone and in either theme.
    for width in (320, 360, 768, 1440):
        page.set_viewport_size({"width": width, "height": 900})
        for light in (True, False):
            if page.locator("body").evaluate("e => e.classList.contains('light')") != light:
                page.locator("#themeToggle").click()
            for button, used, free in ((headless_button, "8899", "3389"), (gui_button, "9088", "3200")):
                button.click()
                expect(page.locator("#labVramMeter")).to_have_attribute("value", used)
                expect(page.locator("#labSnapshotFree")).to_have_text(free + " MiB")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (width, light)
    headless_button.click()
    expect(page.locator("#labSnapshotOther")).to_have_text("41 MiB")
    gui.fill("")
    headless.fill("")
    page.locator('[data-lang="pl"]').click()
    expect(result).to_contain_text("Wpisz dwa odczyty")
    study.locator("summary").click()


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

                check_headless_lab(page)

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
                                expect(study.locator('[data-case-panel="flow"] .case-flow')).to_be_visible()
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
                expect(page.locator("#labModeHeadless")).to_be_visible()
                expect(page.locator("#labModeGui")).to_be_visible()
                expect(page.locator("#labModeSwitch")).to_be_hidden()
                expect(page.locator("#labReadingSwitch")).to_be_hidden()
                expect(page.locator("#labVramCalculator")).to_be_hidden()
                assert "9088 MiB" in homelab.inner_text() and "189 MiB" in homelab.inner_text()
                expect(homelab.locator("a")).to_have_count(0)
                assert "KVM / libvirt" in homelab.inner_text()
                assert page.locator("[data-email-text]").first.inner_text() == "contact [at] banas [dot] dev"
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                assert not errors, errors
                assert not external, external
                assert not violations, violations
                print("Project explorer OK: 9 studies, keyboard tabs, headless/GUI readings, VRAM calculator, filters/tags, PL/EN, 4 widths, 2 themes, cards/list, no JS, privacy, no external requests")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


if __name__ == "__main__":
    check()
