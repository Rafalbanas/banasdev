"""Optional browser checks: python3 scripts/browser_smoke.py (requires Playwright Chromium)."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def check_project_filters(page):
    cards = page.locator("#projects .project-card")
    visible = page.locator("#projects .project-card:visible")
    total = cards.count()
    search = page.locator("#projectSearch")
    assert page.locator("#projectTools").is_visible()
    assert visible.count() == total
    for category in ("data", "automation", "web"):
        page.locator(f'[data-project-filter="{category}"]').click()
        expected = page.locator(f'#projects .project-card[data-project-categories~="{category}"]').count()
        assert visible.count() == expected
        assert page.locator('[data-project-filter][aria-pressed="true"]').count() == 1
        assert visible.evaluate_all("(cards, category) => cards.every(c => c.dataset.projectCategories.split(' ').includes(category))", category)
    search.fill("BM25")
    assert visible.count() == 1
    assert visible.locator("h3").inner_text() == "CVTailor · AI Resume Tailoring"
    page.locator('[data-lang="en"]').click()
    assert page.locator('[data-project-filter="web"]').get_attribute("aria-pressed") == "true"
    assert visible.count() == 1
    page.locator('[data-lang="pl"]').click()
    page.locator('[data-project-filter="all"]').click()
    search.fill("BM25")
    assert visible.count() == 1
    page.locator('[data-project-filter="automation"]').click()
    assert visible.count() == 1
    search.fill("FastALPR")
    assert visible.count() == 0
    assert page.locator("#projectEmpty").is_visible()
    assert page.locator("#projectMoreTitle").is_hidden()
    assert page.locator("#projectFeatured").is_hidden()
    assert page.locator("#projectMore").is_hidden()
    page.locator("#projectReset").focus()
    page.keyboard.press("Enter")
    assert visible.count() == total
    assert search.input_value() == ""
    assert search.evaluate("e => e === document.activeElement")
    search.fill("   ")
    assert visible.count() == total
    search.fill("wlasna")
    assert visible.count() == 1
    assert visible.locator("h3").inner_text() == "Banas.dev"
    search.fill("  WLASNA   subdomeny  ")
    assert visible.count() == 1
    assert visible.locator("h3").inner_text() == "Banas.dev"
    assert page.locator("#projectMoreTitle").is_visible()
    page.locator('[data-lang="en"]').click()
    assert visible.count() == 1
    assert search.input_value() == "  WLASNA   subdomeny  "
    assert page.locator("#projectResults").inner_text() == f"Projects: 1 of {total}"
    assert search.get_attribute("placeholder").startswith("e.g.")
    search.fill("python fastapi")
    assert visible.count() == 1
    assert visible.locator("h3").inner_text() == "Lanari Candle"
    search.fill("<script>alert(1)</script>")
    assert visible.count() == 0
    assert page.locator("#projectEmpty").is_visible()
    assert page.locator("#projectEmpty script").count() == 0
    page.locator("#projectReset").click()
    page.locator('[data-lang="pl"]').click()
    assert visible.count() == total
    assert page.locator("#projectMoreTitle").is_visible()
    assert page.locator("#projectEmpty").is_hidden()


def check():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(timeout=20000)
            page = browser.new_page(reduced_motion="reduce")
            page.set_default_timeout(10000)
            errors = []
            chart_requests = []
            external_requests = []
            page.on("request", lambda request: chart_requests.append(request.url)
                    if request.url.endswith("/assets/vendor/chart.umd.min.js") else None)
            page.on("request", lambda request: external_requests.append(request.url)
                    if not request.url.startswith(url + "/") else None)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script("window.cspViolations = []; document.addEventListener('securitypolicyviolation', e => window.cspViolations.push(e.violatedDirective))")
            page.goto(url, wait_until="networkidle")
            # Repository fixtures may intentionally be old; old data must not look current.
            try:
                page.locator('#weatherWidget[data-state="ready"], #weatherWidget[data-state="stale"]').wait_for(state="attached")
            except Exception:
                print("Initial page diagnostics:", {"errors": errors, "csp": page.evaluate("window.cspViolations"),
                                                     "weather": page.locator("#weatherWidget").get_attribute("data-state")}, flush=True)
                raise
            assert not chart_requests, "Charts must not load on the first screen"
            assert page.evaluate("typeof Chart") == "undefined"
            for lang in ("en", "pl"):
                page.locator(f'[data-lang="{lang}"]').click()
                assert page.locator("html").get_attribute("lang") == lang
                assert page.locator(".hero-role").inner_text() == (
                    "Systems. Data. Less manual work." if lang == "en"
                    else "Systemy. Dane. Mniej ręcznej pracy."
                )
                for light in (True, False):
                    page.locator("#themeToggle").click()
                    assert page.locator("body").evaluate("e => e.classList.contains('light')") == light
                    for width in (320, 375, 768, 1024, 1440):
                        page.set_viewport_size({"width": width, "height": 900})
                        # Chart.js resizes its canvases asynchronously.
                        page.wait_for_function("() => document.documentElement.scrollWidth <= innerWidth", timeout=3000)
            page.set_viewport_size({"width": 375, "height": 900})
            page.locator("#mobileMenuToggle").click()
            assert page.locator("#mobileMenuToggle").get_attribute("aria-expanded") == "true"
            page.keyboard.press("Escape")
            assert page.locator("#mobileMenuToggle").get_attribute("aria-expanded") == "false"
            assert page.locator("#mobileMenuToggle").evaluate("e => e === document.activeElement")
            page.locator("#mobileMenuToggle").click()
            page.locator('.nav-links a[href="#projects"]').click()
            assert page.locator("#mobileMenuToggle").get_attribute("aria-expanded") == "false"
            assert page.locator("#projects-title").evaluate("e => e === document.activeElement")
            page.keyboard.press("Tab")
            assert page.locator("#projectSearch").evaluate("e => e === document.activeElement")
            check_project_filters(page)
            photo = page.locator("#profilePhoto").get_attribute("src")
            page.locator("#photoSwitch").focus()
            page.keyboard.press("Enter")
            page.wait_for_timeout(100)
            assert page.locator("#profilePhoto").get_attribute("src") != photo
            page.locator("#weatherHistoryPanel").scroll_into_view_if_needed()
            page.locator('#weatherHistoryPanel[data-chart-state="ready"]').wait_for(state="attached")
            assert page.evaluate("Chart.version") == "4.4.7"
            assert page.evaluate("!!Chart.getChart('weatherHistoryChart') && !!Chart.getChart('weatherPrecipitationChart')")
            for period in ("24h", "7d", "30d", "day"):
                page.locator(f'[data-weather-range="{period}"]').click()
                assert "is-active" in page.locator(f'[data-weather-range="{period}"]').get_attribute("class")
            page.locator("#weatherDataDetails summary").click()
            expect(page.locator("#weatherTableBody tr")).to_have_count(96)
            assert page.locator("#weatherDataTable thead th").count() == 9
            assert page.locator("#weatherTableBody tr").first.locator("th[scope=row]").count() == 1
            page.locator('[data-weather-range="30d"]').click()
            expect(page.locator("#weatherTableBody tr")).to_have_count(30)
            page.locator('[data-lang="en"]').click()
            assert page.locator("nav").get_attribute("aria-label") == "Main navigation"
            assert "Warsaw time" in page.locator("#weatherTableCaption").inner_text()
            page.locator('[data-lang="pl"]').click()
            assert not page.evaluate("window.cspViolations"), page.evaluate("window.cspViolations")
            for width in (320, 375, 768, 1024, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_function("() => document.documentElement.scrollWidth <= innerWidth", timeout=3000)
            assert len(chart_requests) == 1, chart_requests
            assert not external_requests, external_requests
            page.evaluate("localStorage.setItem('banas_lang', 'invalid')")
            page.reload(wait_until="networkidle")
            assert page.locator("html").get_attribute("lang") == "pl"
            assert not errors, errors
            page.close()

            # A failed chart asset and unavailable storage must not disable the portfolio.
            context = browser.new_context(reduced_motion="reduce")
            context.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw new Error('Blocked storage')}})")
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            chart_route = "**/assets/vendor/chart.umd.min.js"
            page.route(chart_route, lambda route: route.abort())
            page.goto(url, wait_until="networkidle")
            page.locator("#weatherHistoryPanel").scroll_into_view_if_needed()
            page.locator('#weatherHistoryPanel[data-chart-state="error"]').wait_for(state="attached")
            assert page.locator("#chartLibraryRetry").is_visible()
            page.locator("#weatherDataDetails summary").click()
            expect(page.locator("#weatherTableBody tr")).to_have_count(96)
            assert "Nie udało" in page.locator("#chartLibraryStatus").inner_text()
            page.locator('[data-lang="en"]').click()
            page.locator("#themeToggle").click()
            assert page.locator("html").get_attribute("lang") == "en"
            assert page.locator("body").evaluate("e => e.classList.contains('light')")
            assert "could not be loaded" in page.locator("#chartLibraryStatus").inner_text()
            page.unroute(chart_route)
            page.locator("#chartLibraryRetry").click()
            page.locator('#weatherHistoryPanel[data-chart-state="ready"]').wait_for(state="attached")
            assert page.locator("#chartLibraryNotice").is_hidden()
            assert page.evaluate("!!Chart.getChart('weatherHistoryChart')")
            assert not errors, errors
            context.close()

            # Older browsers load charts immediately instead of failing initialization.
            context = browser.new_context()
            context.add_init_script("delete window.IntersectionObserver")
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url, wait_until="networkidle")
            page.locator('#weatherHistoryPanel[data-chart-state="ready"]').wait_for(state="attached")
            assert page.evaluate("!!Chart.getChart('weatherHistoryChart')")
            assert not errors, errors
            context.close()

            context = browser.new_context()
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url, wait_until="networkidle")
            page.locator("#projects .card").first.scroll_into_view_if_needed()
            page.wait_for_function("() => document.querySelector('#projects .card').classList.contains('is-visible')")
            page.locator('[data-project-filter="web"]').click()
            page.locator("#projects .project-card:not([hidden])").first.scroll_into_view_if_needed()
            page.wait_for_function("() => document.querySelector('#projects .project-card:not([hidden])').classList.contains('is-visible')")
            assert not errors, errors
            context.close()

            context = browser.new_context(java_script_enabled=False, viewport={"width": 375, "height": 900})
            page = context.new_page()
            page.goto(url)
            assert page.locator('.nav-links a[href="#projects"]').is_visible()
            assert page.locator("#hero-title").is_visible()
            assert page.locator("#projectTools").is_hidden()
            assert page.locator("#projects .project-card:visible").count() == page.locator("#projects .project-card").count()
            context.close()
            browser.close()
        print("Browser OK: PL/EN, themes, 5 widths, project search/filters, keyboard, lazy local charts, retry, no external requests, storage failure, no JS")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    check()
