"""Optional terminal interaction checks; requires Playwright and Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def activate(page, selector):
    page.locator(selector).focus()
    page.keyboard.press("Enter")


def check_interactions(page):
    terminal = page.locator("#labTerminal")
    content = page.locator("#terminalContent")
    activate(page, "#terminalMinimize")
    expect(content).to_be_hidden()
    expect(page.locator("#terminalMinimize")).to_have_attribute("aria-expanded", "false")
    activate(page, "#terminalExpand")
    expect(content).to_be_visible()
    expect(terminal).to_have_class("lab-terminal is-expanded")
    expect(page.locator("#terminalExpand")).to_have_attribute("aria-pressed", "true")
    activate(page, "#terminalExpand")
    expect(page.locator("#terminalExpand")).to_have_attribute("aria-pressed", "false")
    activate(page, "#terminalClose")
    expect(terminal).to_be_hidden()
    assert page.locator("#terminalRestore").evaluate("e => e === document.activeElement")
    page.keyboard.press("Enter")
    expect(terminal).to_be_visible()
    expect(page.locator("#terminalRestore")).to_be_hidden()
    assert page.locator("#terminalClose").evaluate("e => e === document.activeElement")

    command = page.locator("#terminalCommand")
    output = page.locator("#terminalOutput")

    def submit(value):
        command.fill(value)
        command.press("Enter")

    submit("help")
    expect(output).to_contain_text("whoami")
    submit("cat .motd")
    expect(page.locator("#terminalMotd")).to_have_attribute("open", "")
    expect(page.locator("#terminalPet")).to_be_visible()
    activate(page, "#terminalPet")
    expect(page.locator("#terminalPet")).to_have_class("terminal-pet is-petted")
    expect(page.locator("#terminalPetReaction")).to_contain_text("Mrrr")
    activate(page, "#terminalPetPause")
    expect(page.locator("#terminalPetPause")).to_have_attribute("aria-pressed", "true")
    assert page.locator("#terminalPet").evaluate("e => getComputedStyle(e).animationName") == "none"
    page.locator('[data-lang="en"]').click()
    expect(page.locator("#terminalPetReaction")).to_contain_text("Purrr")
    expect(output).to_contain_text("Log keeper awake")
    expect(page.locator("#terminalPetPause")).to_have_text("Resume cat movement")
    submit("ride --gravel")
    expect(page.locator("#terminalGravel")).to_have_attribute("open", "")
    submit("whoami")
    expect(output).to_contain_text("Rafał Banaś")
    submit('<img src=x onerror="alert(1)">')
    expect(output).to_contain_text("Unknown command")
    expect(output.locator("img")).to_have_count(0)
    submit("ls")
    expect(output).to_contain_text("Projects / Homelab")
    submit("clear")
    expect(output.locator("p")).to_have_count(0)
    for index in range(25):
        submit(f"cmd{index}")
    expect(output.locator("p")).to_have_count(8)
    command.fill("draft")
    for _ in range(25):
        command.press("ArrowUp")
    expect(command).to_have_value("cmd5")
    for _ in range(25):
        command.press("ArrowDown")
    expect(command).to_have_value("draft")
    submit("clear")
    command.fill("   ")
    command.press("Enter")
    expect(output.locator("p")).to_have_count(0)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def check():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                url = f"http://127.0.0.1:{server.server_port}"
                for width in (320, 768, 1440):
                    page = browser.new_page(viewport={"width": width, "height": 900}, reduced_motion="reduce")
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(url, wait_until="networkidle")
                    requests = []
                    page.on("request", lambda request: requests.append(request.url))
                    check_interactions(page)
                    assert not errors, errors
                    assert not requests, f"Terminal must not make network requests: {requests}"
                    page.close()

                page = browser.new_page(viewport={"width": 1440, "height": 1000}, reduced_motion="no-preference")
                page.goto(url, wait_until="networkidle")
                activate(page, "#terminalMotd summary")
                scene = page.locator("#terminalPetScene")
                scene.scroll_into_view_if_needed()
                expect(scene).to_have_class("terminal-pet-scene pet-running")
                activate(page, "#terminalPetPause")
                expect(scene).to_have_class("terminal-pet-scene")
                activate(page, "#terminalPetPause")
                expect(scene).to_have_class("terminal-pet-scene pet-running")
                page.emulate_media(reduced_motion="reduce")
                expect(scene).to_have_class("terminal-pet-scene")
                page.emulate_media(reduced_motion="no-preference")
                expect(scene).to_have_class("terminal-pet-scene pet-running")
                activate(page, "#terminalMinimize")
                expect(scene).to_have_class("terminal-pet-scene")
                activate(page, "#terminalMinimize")
                scene.scroll_into_view_if_needed()
                expect(scene).to_have_class("terminal-pet-scene pet-running")
                activate(page, "#terminalClose")
                expect(scene).to_have_class("terminal-pet-scene")
                page.locator("#terminalRestore").click()
                scene.scroll_into_view_if_needed()
                expect(scene).to_have_class("terminal-pet-scene pet-running")
                page.locator("#contact").scroll_into_view_if_needed()
                expect(scene).to_have_class("terminal-pet-scene")
                page.close()

                context = browser.new_context(java_script_enabled=False, viewport={"width": 320, "height": 900})
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded")
                for selector in ("#terminalControls", "#terminalConsole", "#terminalRestore", "#terminalPetScene"):
                    expect(page.locator(selector)).to_be_hidden()
                for selector in ("#terminalMotd", "#terminalGravel"):
                    activate(page, selector + " summary")
                    expect(page.locator(selector + " > p")).to_be_visible()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    print("Interactive terminal OK: controls, focus, pet, motion, commands, history, PL/EN, 3 widths, no JS, no network")


if __name__ == "__main__":
    check()
