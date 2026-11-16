"""Professional / after-hours journeys, including the direct LinkedIn CTA."""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright

from check_ride_and_stories import ROOT, QuietHandler, fixtures


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                for width in (360, 768, 1440):
                    context = browser.new_context(viewport={"width": width, "height": 900},
                                                  reduced_motion="reduce")
                    page = context.new_page()
                    errors = []
                    external = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("request", lambda request: external.append(request.url)
                            if not request.url.startswith(base) else None)
                    location, air = fixtures()
                    page.route("**/weather.json", lambda route: route.fulfill(
                        json={"locations": {"kat04bapp": location}}))
                    page.route("**/data.json", lambda route: route.fulfill(json=air))
                    page.goto(base, wait_until="networkidle")
                    expect(page.locator("#weatherArchive")).not_to_have_attribute("open", "")
                    cta = page.locator(".hero-actions .primary")
                    expect(cta).to_contain_text("LinkedIn")
                    assert "linkedin.com/in/" in cta.get_attribute("href")
                    contrast = cta.evaluate("""element => {
                        const s=getComputedStyle(element);
                        const luminance=color => {
                            const rgb=color.match(/[\\d.]+/g).slice(0,3).map(Number).map(v=>{
                                v/=255; return v<=.04045 ? v/12.92 : ((v+.055)/1.055)**2.4;
                            });
                            return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;
                        };
                        const a=luminance(s.color), b=luminance(s.backgroundColor);
                        return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
                    }""")
                    assert contrast >= 4.5, f"LinkedIn CTA contrast: {contrast}"
                    if width == 1440:
                        box = cta.bounding_box()
                        assert box["y"] + box["height"] <= 900, "LinkedIn CTA should fit on the first desktop screen"
                    expect(page.locator(".site-sections [aria-current=page]")).to_contain_text("Zawodowo")
                    for language in ("pl", "en"):
                        page.locator(f'[data-lang="{language}"]').click()
                        page.locator(".site-sections [data-hobby-link]").click()
                        expect(page.locator("html")).to_have_attribute("lang", language)
                        expect(page.locator("#hobbies-title")).to_be_visible()
                        expect(page.locator("#ridePlanner")).to_have_attribute("data-state", "go")
                        for theme in ("dark", "light"):
                            light = page.locator("html").evaluate("e=>e.classList.contains('light')")
                            if light != (theme == "light"):
                                page.locator("#storyTheme").click()
                            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                            if args.screenshots and language == "pl":
                                page.screenshot(path=str(args.screenshots / f"hobby-{width}-{theme}.png"), full_page=True)
                        page.locator("#rideDuration").select_option("30")
                        expect(page.locator("#rideTimeline")).to_be_visible()
                        for control in ("#storyTheme", "#storyLanguage"):
                            assert page.locator(control).bounding_box()["height"] >= 44
                        page.locator("#storyLanguage").click()
                        other_language = "en" if language == "pl" else "pl"
                        expect(page.locator("html")).to_have_attribute("lang", other_language)
                        page.locator(".brand").click()
                        expect(page).to_have_url(base + f"/index.html?lang={other_language}")
                        page.wait_for_load_state("domcontentloaded")
                        expect(page.locator("#projectTools")).to_be_visible(timeout=15000)
                        expect(page.locator("html")).to_have_attribute("lang", other_language)
                    # A failed export must not leave a positive ride recommendation.
                    page.locator('[data-lang="en"]').click()
                    page.route("**/data.json", lambda route: route.fulfill(status=503, body="Unavailable"))
                    page.locator(".site-sections [data-hobby-link]").click()
                    expect(page.locator("#ridePlanner")).to_have_attribute("data-state", "unknown")
                    expect(page.locator("#hobbyDataStatus")).to_contain_text("could not")
                    assert not external, external
                    assert not errors, errors
                    context.close()
                    print(f"Professional / hobbies / LinkedIn journey OK: {width}px / PL+EN")
                context = browser.new_context(java_script_enabled=False)
                page = context.new_page()
                page.goto(base + "/hobby.html")
                expect(page.locator("#hobbies-title")).to_be_visible()
                expect(page.locator("#rideDuration")).to_be_disabled()
                expect(page.locator("#storyLanguage")).to_be_hidden()
                context.close()
                print("After-hours no-JS fallback OK")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    run()
