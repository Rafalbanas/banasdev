"""Browser checks for ride advice and the new project page. Requires Playwright."""
import argparse
from datetime import datetime, timedelta, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Browser navigation can cancel an in-flight history response.


def fixtures():
    now = datetime.now(timezone.utc)
    iso = lambda value: value.isoformat().replace("+00:00", "Z")
    start = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0)
    point = {"temperature": 18, "wind_speed": 10, "precipitation": 0,
             "rain": 0, "snowfall": 0, "showers": 0, "weather_code": 0,
             "precipitation_probability": 0}
    location = {"current": dict(point, data_time_utc=iso(now), fetched_at_utc=iso(now)),
                "observations": [], "forecast": {"issued_at_utc": iso(now), "intervals": [
                    dict(point, interval_start_utc=iso(start + timedelta(minutes=i * 15)),
                         interval_end_utc=iso(start + timedelta(minutes=(i + 1) * 15)),
                         forecast_time_utc=iso(start + timedelta(minutes=(i + 1) * 15)))
                    for i in range(9)]}}
    air = json.loads((ROOT / "data.json").read_text())
    air.update(measured_at=iso(now), air_index_level="GOOD")
    return location, air


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
                    errors = []
                    page = context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    location, air = fixtures()
                    page.route("**/weather.json", lambda route: route.fulfill(
                        json={"locations": {"kat04bapp": location}}))
                    page.route("**/data.json", lambda route: route.fulfill(json=air))
                    page.goto(base, wait_until="networkidle")
                    page.locator("#weatherArchive > summary").click()
                    expect(page.locator("#ridePlanner")).to_have_attribute("data-state", "go")
                    expect(page.locator("#rideTimeline")).to_be_visible()
                    assert 8 <= page.locator(".ride-slot").count() <= 9
                    expect(page.locator(".ride-slot.is-selected").first).to_be_attached()
                    page.locator("#rideDuration").select_option("90")
                    expect(page.locator("#ridePlanner")).to_have_attribute("data-state", "go")
                    page.locator('[data-lang="en"]').click()
                    expect(page.locator("#rideVerdict")).to_contain_text("good window")
                    page.locator("#rideDuration").select_option("60")
                    page.evaluate("""([location, air]) => {
                        location.current.precipitation = 0.6;
                        location.forecast.intervals.slice(0, 2).forEach(p => p.precipitation = 0.6);
                        window.RidePlanner.render(location, air);
                    }""", [location, air])
                    expect(page.locator("#ridePlanner")).to_have_attribute("data-state", "wait")
                    expect(page.locator("#rideReasons")).to_contain_text("Why not now")
                    page.evaluate("""([location, air]) => {
                        location.current.wind_speed = 40;
                        location.forecast.intervals.forEach(p => p.wind_speed = 40);
                        window.RidePlanner.render(location, air);
                    }""", [location, air])
                    expect(page.locator("#ridePlanner")).to_have_attribute("data-state", "avoid")
                    page.evaluate("""([location, air]) => {
                        air.measured_at = '2020-01-01T00:00:00Z';
                        window.RidePlanner.render(location, air);
                    }""", [location, air])
                    expect(page.locator("#ridePlanner")).to_have_attribute("data-state", "unknown")
                    page.evaluate("() => window.RidePlanner.render(null, null)")
                    expect(page.locator("#ridePlanner")).to_have_attribute("data-state", "unknown")
                    expect(page.locator("#rideTimeline")).to_be_hidden()
                    expect(page.locator("#rideTimelineStatus")).to_be_visible()
                    page.locator("#rideDuration").select_option("60")
                    expect(page.locator("#ridePlanner")).to_have_attribute("data-state", "go")
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    if args.screenshots:
                        page.locator("#ridePlanner").screenshot(path=str(args.screenshots / f"ride-{width}.png"))
                    page.locator("[data-story-link]").first.click()
                    expect(page).to_have_url(base + "/projekty.html?lang=en")
                    expect(page.locator("html")).to_have_attribute("lang", "en")
                    for language in ("pl", "en"):
                        if page.locator("html").get_attribute("lang") != language:
                            page.locator("#storyLanguage").click()
                        for theme in ("dark", "light"):
                            if page.locator("html").evaluate("e => e.classList.contains('light')") != (theme == "light"):
                                page.locator("#storyTheme").click()
                            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                            expect(page.locator("#stories-title")).to_be_visible()
                            expect(page.locator(".case-story")).to_have_count(3)
                            # The other language must be absent from the accessibility/layout tree.
                            hidden = ".lang-en" if language == "pl" else ".lang-pl"
                            assert page.locator(hidden).evaluate_all(
                                "items => items.every(e => getComputedStyle(e).display === 'none')")
                            if args.screenshots and language == "pl" and theme == "dark":
                                page.screenshot(path=str(args.screenshots / f"stories-{width}.png"), full_page=True)
                    page.locator('.story-footer a').click()
                    expect(page.locator("html")).to_have_attribute("lang", "en")
                    assert not errors, errors
                    context.close()
                    print(f"Ride + project stories OK: {width}px / PL+EN / dark+light")
                context = browser.new_context(java_script_enabled=False, viewport={"width": 360, "height": 900})
                page = context.new_page()
                page.goto(base)
                expect(page.locator("#rideVerdict")).to_have_text("Bez świeżych danych nie zgaduję.")
                expect(page.locator("#rideDuration")).to_be_disabled()
                page.goto(base + "/projekty.html")
                expect(page.locator("#stories-title")).to_be_visible()
                expect(page.locator("#storyLanguage")).to_be_hidden()
                expect(page.locator(".case-story")).to_have_count(3)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                context.close()
                print("No-JS fallback OK")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    run()
