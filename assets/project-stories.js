/* Same preferences as the portfolio; no network requests or tracking. */
(() => {
    const root = document.documentElement;
    const language = document.getElementById("storyLanguage");
    const theme = document.getElementById("storyTheme");
    const internalLinks = [...document.querySelectorAll('a[href^="index.html"], a[href^="projekty.html"], a[href^="hobby.html"]')];
    const read = key => { try { return localStorage.getItem(key); } catch { return null; } };
    const write = (key, value) => { try { localStorage.setItem(key, value); } catch { /* optional */ } };
    function render(lang, light) {
        root.lang = lang === "en" ? "en" : "pl";
        root.classList.toggle("light", light);
        language.textContent = root.lang === "pl" ? "EN" : "PL";
        language.setAttribute("aria-label", root.lang === "pl" ? "Switch to English" : "Przełącz na polski");
        theme.setAttribute("aria-pressed", String(light));
        theme.setAttribute("aria-label", root.lang === "pl" ? "Jasny motyw" : "Light theme");
        document.querySelectorAll(".case-next").forEach(nav => {
            nav.setAttribute("aria-label", root.lang === "pl" ? "Nawigacja projektów" : "Project navigation");
        });
        const hobby = document.body.dataset.page === "hobbies";
        document.title = hobby
            ? (root.lang === "pl" ? "Po godzinach — Rafał Banaś" : "After hours — Rafał Banaś")
            : (root.lang === "pl" ? "Wybrane projekty — Rafał Banaś" : "Selected work — Rafał Banaś");
        internalLinks.forEach(link => {
            const url = new URL(link.href);
            url.searchParams.set("lang", root.lang);
            link.href = url.pathname + url.search + url.hash;
        });
        document.dispatchEvent(new Event("portfolio:language"));
    }
    const requested = new URLSearchParams(location.search).get("lang");
    render(requested || read("banas_lang"), read("banas_theme") === "light");
    language.hidden = theme.hidden = false;
    language.addEventListener("click", () => {
        render(root.lang === "pl" ? "en" : "pl", root.classList.contains("light"));
        write("banas_lang", root.lang);
    });
    theme.addEventListener("click", () => {
        render(root.lang, !root.classList.contains("light"));
        write("banas_theme", root.classList.contains("light") ? "light" : "dark");
    });
})();
