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


def check_dragging(page):
    scene = page.locator("#terminalPetScene")
    pet = page.locator("#terminalPet")
    scene.scroll_into_view_if_needed()
    expect(page.locator("body > #terminalPet")).to_have_count(0)
    petted = pet.evaluate("e => e.classList.contains('is-petted')")

    def start_drag():
        box = pet.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()

    start_drag()
    page.mouse.move(10, 200, steps=12)
    page.mouse.up()
    expect(page.locator("body > #terminalPet")).to_have_count(1)
    expect(page.locator("#pagePetControls")).to_be_visible()
    assert pet.evaluate("e => e.classList.contains('is-petted')") == petted, "A drag must not also pet the cat"

    # A second real mouse drag returns the same DOM node to its home.
    scene.scroll_into_view_if_needed()
    home = page.locator("#terminalPetHome").bounding_box()
    start_drag()
    page.mouse.move(home["x"] + home["width"] / 2, home["y"] + home["height"] / 2, steps=12)
    page.mouse.up()
    expect(page.locator("#terminalPetHome > #terminalPet")).to_have_count(1)
    expect(page.locator("#pagePetControls")).to_be_hidden()

    # Escape cancels a drag that began at home.
    start_drag()
    page.mouse.move(10, 200, steps=12)
    page.keyboard.press("Escape")
    page.mouse.up()
    expect(page.locator("#terminalPetHome > #terminalPet")).to_have_count(1)

    activate(page, "#terminalPetRelease")
    expect(page.locator("body > #terminalPet")).to_have_count(1)
    before = pet.bounding_box()
    start_drag()
    page.mouse.move(100, 220, steps=8)
    page.keyboard.press("Escape")
    page.mouse.up()
    expect(page.locator("body > #terminalPet")).to_have_count(1)
    after = pet.bounding_box()
    assert abs(before["x"] - after["x"]) < 1 and abs(before["y"] - after["y"]) < 1

    viewport = page.viewport_size
    page.set_viewport_size({"width": 320, "height": 640})
    box = pet.bounding_box()
    assert 8 <= box["x"] <= 248 and 8 <= box["y"] <= 496
    page.set_viewport_size(viewport)
    activate(page, "#terminalClose")
    expect(page.locator("body > #terminalPet")).to_have_count(1)
    activate(page, "#pagePetReturn")
    expect(page.locator("#terminalPetHome > #terminalPet")).to_have_count(1)
    expect(page.locator("#labTerminal")).to_be_visible()
    assert pet.evaluate("e => e === document.activeElement")


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
                    expect(page.locator("#labTerminal")).to_be_hidden()
                    expect(page.locator("#terminalShell")).not_to_have_attribute("open", "")
                    activate(page, "#terminalRestore")
                    requests = []
                    page.on("request", lambda request: requests.append(request.url))
                    check_interactions(page)
                    check_dragging(page)
                    assert not errors, errors
                    assert not requests, f"Terminal must not make network requests: {requests}"
                    page.close()

                page = browser.new_page(viewport={"width": 1440, "height": 1000}, reduced_motion="no-preference")
                page.goto(url, wait_until="networkidle")
                activate(page, "#terminalRestore")
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
                activate(page, "#terminalPetRelease")
                pet = page.locator("#terminalPet")
                initial = pet.bounding_box()
                page.wait_for_function("x => Math.abs(document.getElementById('terminalPet').getBoundingClientRect().x - x) > 2", arg=initial["x"])
                activate(page, "#pagePetPause")
                frozen = pet.bounding_box()
                page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                assert pet.bounding_box() == frozen
                page.locator('[data-lang="en"]').click()
                expect(page.locator("#pagePetReturn")).to_have_text("Return to terminal")
                activate(page, "#pagePetPause")
                page.emulate_media(reduced_motion="reduce")
                frozen = pet.bounding_box()
                page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                assert pet.bounding_box() == frozen
                activate(page, "#pagePetReturn")
                page.close()

                context = browser.new_context(java_script_enabled=False, viewport={"width": 320, "height": 900})
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded")
                expect(page.locator("#labTerminal")).to_be_hidden()
                activate(page, "#terminalRestore")
                for selector in ("#terminalControls", "#terminalConsole", "#terminalPetScene", "#pagePetControls"):
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
    print("Interactive terminal OK: closed by default, window controls, real mouse drag/return, Escape, resize, pet motion/pause, commands, PL/EN, 3 widths, no JS, no network")


if __name__ == "__main__":
    check()
