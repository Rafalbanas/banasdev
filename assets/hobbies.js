/* This page reuses the same public exports and pure ride evaluator as the portfolio. */
(() => {
    "use strict";
    const duration = document.getElementById("rideDuration");
    if (!duration || !window.RidePlanner) return;
    let location = null;
    let air = null;
    let failed = false;
    let loading = false;
    let lastAttempt = 0;
    const status = document.getElementById("hobbyDataStatus");
    function render() {
        window.RidePlanner.render(location, air, failed);
        if (!status) return;
        const english = document.documentElement.lang === "en";
        status.textContent = loading
            ? (english ? "Loading the public weather exports…" : "Wczytywanie publicznych danych pogodowych…")
            : failed
                ? (english ? "Data could not be refreshed. No recommendation until the next successful refresh." : "Nie udało się odświeżyć danych. Ocena wróci po udanym pobraniu.")
                : (english ? "Open-Meteo + GIOŚ · automatic refresh every 15 minutes." : "Open-Meteo + GIOŚ · automatyczne odświeżanie co 15 minut.");
    }
    async function refresh() {
        if (loading) return;
        loading = true;
        lastAttempt = Date.now();
        render();
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 10000);
        try {
            const payloads = await Promise.all(["weather.json", "data.json"].map(async url => {
                const response = await fetch(url, { cache: "no-cache", signal: controller.signal });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return response.json();
            }));
            const next = payloads[0]?.locations?.kat04bapp;
            if (!next?.current || !Array.isArray(next?.forecast?.intervals) || !Array.isArray(payloads[1]?.stations)) {
                throw new Error("Incomplete public data");
            }
            location = next;
            air = payloads[1];
            failed = false;
        } catch {
            failed = true;
        } finally {
            clearTimeout(timer);
            controller.abort(); // Also cancel the other export if one failed early.
            loading = false;
            render();
        }
    }
    duration.disabled = false;
    duration.addEventListener("change", render);
    document.addEventListener("portfolio:language", render);
    setInterval(() => { if (!document.hidden) render(); }, 60000);
    setInterval(() => { if (!document.hidden) refresh(); }, 15 * 60000);
    document.addEventListener("visibilitychange", () => {
        if (!document.hidden && Date.now() - lastAttempt >= 15 * 60000) refresh();
        else if (!document.hidden) render();
    });
    refresh();
})();
