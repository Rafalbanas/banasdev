/* Transparent comfort heuristic, not a safety forecast. No I/O in evaluate(). */
(function (root) {
    "use strict";
    const MINUTE = 60000;
    const levels = ["VERY_GOOD", "GOOD", "MODERATE", "SUFFICIENT", "BAD", "VERY_BAD"];
    const finite = value => typeof value === "number" && Number.isFinite(value);
    const fresh = (time, now, minutes) => {
        const age = now - Date.parse(time);
        return Number.isFinite(age) && age >= -5 * MINUTE && age <= minutes * MINUTE;
    };
    function conditions(point, forecast) {
        if (!point || !["temperature", "wind_speed", "precipitation", "weather_code"].every(k => finite(point[k])) ||
            point.temperature < -80 || point.temperature > 60 || point.wind_speed < 0 || point.wind_speed > 250 ||
            point.precipitation < 0 || !Number.isInteger(point.weather_code) ||
            ![0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99].includes(point.weather_code) ||
            (forecast && (!finite(point.precipitation_probability) || point.precipitation_probability < 0 || point.precipitation_probability > 100))) return null;
        const reasons = [];
        let severity = 0;
        const add = (key, score) => { reasons.push(key); severity = Math.max(severity, score); };
        if ([48, 56, 57, 66, 67, 71, 73, 75, 77, 85, 86, 95, 96, 99].includes(point.weather_code) || point.snowfall > 0) add("hazard", 2);
        if (point.weather_code === 45) add("fog", 1);
        if (point.temperature <= 2 || point.temperature >= 32) add("extremeTemp", 2);
        else if (point.temperature < 10 || point.temperature > 26) add("temperature", 1);
        if (point.wind_speed >= 35) add("strongWind", 2);
        else if (point.wind_speed > 20) add("wind", 1);
        if (point.precipitation >= 0.5 || point.precipitation_probability >= 70) add("rain", 2);
        else if (point.precipitation >= 0.1 || point.precipitation_probability >= 40 ||
                 [51, 53, 55, 61, 63, 65, 80, 81, 82].includes(point.weather_code)) add("possibleRain", 1);
        return { severity, reasons };
    }
    function evaluate(location, air, now = Date.now(), duration = 60, failed = false) {
        const unknown = { state: "unknown", reasons: ["missing"] };
        if (![30, 60, 90].includes(duration) || !finite(now) || failed ||
            !fresh(location?.current?.data_time_utc, now, 30) ||
            !fresh(location?.current?.fetched_at_utc, now, 30) ||
            !fresh(location?.forecast?.issued_at_utc, now, 30) ||
            !fresh(air?.measured_at, now, 180)) return unknown;
        if (![air.pm25?.value, air.pm10?.value].every(v => finite(v) && v >= 0)) return unknown;
        if (!Array.isArray(air.stations) || !air.stations.length || air.stations.some(s => !s)) return unknown;
        const airLevels = [air.air_index_level, ...air.stations.map(s => s.air_index_level)];
        if (!airLevels.length || airLevels.some(level => !levels.includes(level))) return unknown;
        const airRank = Math.max(...airLevels.map(level => levels.indexOf(level)));
        const current = conditions(location.current, false);
        if (!current || !Array.isArray(location.forecast.intervals) || location.forecast.intervals.some(p => !p)) return unknown;
        const intervals = location.forecast.intervals.map(point => ({
            start: Date.parse(point.interval_start_utc), end: Date.parse(point.interval_end_utc),
            point, result: conditions(point, true)
        })).filter(p => p.end > now && p.start < now + 120 * MINUTE)
            .sort((a, b) => a.start - b.start);
        const starts = [now, ...intervals.map(p => p.start).filter(t => t > now)];
        const windows = [];
        for (const start of [...new Set(starts)]) {
            const end = start + duration * MINUTE;
            if (end > now + 120 * MINUTE) continue;
            const parts = intervals.filter(p => p.start < end && p.end > start);
            let cursor = start;
            let valid = true;
            for (const [index, part] of parts.entries()) {
                if (!part.result || part.start > cursor || part.end <= part.start ||
                    part.end - part.start !== 15 * MINUTE || (index > 0 && part.start !== cursor)) {
                    valid = false; break;
                }
                cursor = part.end;
            }
            if (!valid || cursor < end || !parts.length) continue;
            const results = parts.map(p => p.result);
            if (start === now) results.push(current);
            const severity = Math.max(airRank >= 3 ? 2 : airRank >= 2 ? 1 : 0, ...results.map(p => p.severity));
            const reasons = [...new Set(results.flatMap(p => p.reasons))];
            const points = parts.map(p => p.point);
            if (start === now) points.push(location.current);
            if (airRank >= 2) reasons.push("air");
            windows.push({
                start, end, severity, reasons,
                minTemp: Math.min(...points.map(p => p.temperature)),
                maxTemp: Math.max(...points.map(p => p.temperature)),
                wind: Math.max(...points.map(p => p.wind_speed)),
                probability: Math.max(...parts.map(p => p.point.precipitation_probability))
            });
        }
        // A gap at "now" must not be silently converted into a later recommendation.
        if (!windows.length || windows[0].start !== now) return unknown;
        const best = windows.find(w => w.severity === 0);
        const chosen = best || windows[0];
        return {
            ...chosen,
            state: best ? (best.start === now ? "go" : "wait") : chosen.severity === 2 ? "avoid" : "caution",
            reasons: chosen.reasons.length ? chosen.reasons : ["comfortable"],
            earlierReasons: best && best.start > now ? windows[0].reasons : [],
            weatherAt: location.current.data_time_utc, airAt: air.measured_at
        };
    }
    // Keep the timeline on the same thresholds and freshness gates as the verdict.
    // Fixed UTC quarter-hours expose missing slots instead of joining across gaps.
    function timeline(location, air, now = Date.now(), failed = false) {
        if (evaluate(location, air, now, 30, failed).state === "unknown") return [];
        const rank = Math.max(...[air.air_index_level, ...air.stations.map(s => s.air_index_level)]
            .map(level => levels.indexOf(level)));
        const first = Math.floor(now / (15 * MINUTE)) * 15 * MINUTE;
        const points = [];
        for (let start = first; start < now + 120 * MINUTE; start += 15 * MINUTE) {
            const end = start + 15 * MINUTE;
            const matches = location.forecast.intervals.filter(p =>
                Date.parse(p.interval_start_utc) === start && Date.parse(p.interval_end_utc) === end);
            const condition = matches.length === 1 ? conditions(matches[0], true) : null;
            const severity = condition ? Math.max(condition.severity, rank >= 3 ? 2 : rank >= 2 ? 1 : 0) : null;
            points.push({
                start: Math.max(start, now), end: Math.min(end, now + 120 * MINUTE),
                state: severity === null ? "unknown" : severity === 2 ? "avoid" : severity === 1 ? "caution" : "go"
            });
        }
        return points;
    }
    const copy = {
        pl: {
            go: "Wygląda na dobre okno. Wskakujesz? ↗", wait: "Warto poczekać na lepsze okno.",
            avoid: "Na razie lepiej odpuścić.", caution: "Da się rozważyć, ale z zastrzeżeniami.",
            unknown: "Bez świeżych danych nie zgaduję.",
            missing: "Brakuje kompletnych, aktualnych danych pogody, prognozy lub jakości powietrza.",
            comfortable: "W tym oknie prognoza mieści się w przyjętych progach komfortu.",
            hazard: "Model wskazuje burzę, śnieg lub ryzyko oblodzenia.",
            fog: "Model wskazuje mgłę — widoczność może być ograniczona.",
            extremeTemp: "Temperatura ≤2°C lub ≥32°C.", temperature: "Chłodno lub ciepło: poza komfortowym zakresem 10–26°C.",
            strongWind: "Wiatr co najmniej 35 km/h.", wind: "Wiatr powyżej 20 km/h.",
            rain: "Opady ≥0,5 mm / 15 min lub prawdopodobieństwo ≥70%.",
            possibleRain: "Możliwe opady: kod opadów, ≥0,1 mm / 15 min lub prawdopodobieństwo ≥40%.",
            air: "Co najmniej jedna stacja lub indeks zbiorczy GIOŚ jest poniżej poziomu dobrego.",
            window: "Okno", windLabel: "maks. wiatr", chance: "maks. szansa opadów / godz.",
            earlier: "Dlaczego nie teraz: ",
            slotGo: "W progach komfortu", slotCaution: "Zastrzeżenia", slotAvoid: "Niesprzyjające", slotUnknown: "Brak danych",
            selected: "Wybrane okno", timelineUnavailable: "Oś prognozy pojawi się po otrzymaniu kompletnych, świeżych danych.",
            times: "Czas w Katowicach", weather: "Pogoda", airLabel: "Powietrze",
            noWindow: "Nie znalazłem komfortowego okna tej długości w dostępnych najbliższych 2 godzinach."
        },
        en: {
            go: "Looks like a good window. Fancy a ride? ↗", wait: "A better window is worth waiting for.",
            avoid: "Better skip it for now.", caution: "Worth considering, with caveats.",
            unknown: "No fresh data? No guessing.",
            missing: "Complete, fresh weather, forecast or air-quality data is missing.",
            comfortable: "The forecast in this window meets the chosen comfort thresholds.",
            hazard: "The model indicates a storm, snow or icing risk.",
            fog: "The model indicates fog — visibility may be limited.",
            extremeTemp: "Temperature ≤2°C or ≥32°C.", temperature: "Cool or warm: outside the comfortable 10–26°C range.",
            strongWind: "Wind at least 35 km/h.", wind: "Wind above 20 km/h.",
            rain: "Precipitation ≥0.5 mm / 15 min or probability ≥70%.",
            possibleRain: "Possible precipitation: weather code, ≥0.1 mm / 15 min or probability ≥40%.",
            air: "At least one station or the aggregate GIOŚ index is below good.",
            window: "Window", windLabel: "max. wind", chance: "max. hourly precipitation chance",
            earlier: "Why not now: ",
            slotGo: "Within comfort thresholds", slotCaution: "Caveats", slotAvoid: "Unfavourable", slotUnknown: "No data",
            selected: "Selected window", timelineUnavailable: "The forecast timeline needs complete, fresh data.",
            times: "Katowice local time", weather: "Weather", airLabel: "Air",
            noWindow: "No comfortable window of this length found in the available next 2 hours."
        }
    };
    function render(location, air, failed = false) {
        const panel = document.getElementById("ridePlanner");
        if (!panel) return;
        const lang = document.documentElement.lang === "en" ? "en" : "pl";
        const text = copy[lang];
        const result = evaluate(location, air, Date.now(), Number(document.getElementById("rideDuration").value), failed);
        panel.dataset.state = result.state;
        document.getElementById("rideVerdict").textContent = text[result.state];
        const list = document.getElementById("rideReasons");
        list.replaceChildren();
        result.reasons.forEach(key => {
            const item = document.createElement("li");
            item.textContent = text[key];
            list.append(item);
        });
        if (result.earlierReasons?.length) {
            const item = document.createElement("li");
            item.textContent = text.earlier + result.earlierReasons.map(key => text[key]).join(" ");
            list.append(item);
        }
        const details = document.getElementById("rideWindow");
        const updated = document.getElementById("rideUpdated");
        const time = value => new Intl.DateTimeFormat(lang === "pl" ? "pl-PL" : "en-GB", {
            timeZone: "Europe/Warsaw", hour: "2-digit", minute: "2-digit"
        }).format(new Date(value));
        const strip = document.getElementById("rideTimeline");
        const timelineStatus = document.getElementById("rideTimelineStatus");
        if (strip) {
            strip.replaceChildren();
            const points = timeline(location, air, Date.now(), failed);
            points.forEach(point => {
                const item = document.createElement("li");
                item.className = "ride-slot";
                item.dataset.state = point.state;
                const selected = result.state !== "unknown" && point.start < result.end && point.end > result.start;
                if (selected) item.classList.add("is-selected");
                const clock = document.createElement("time");
                clock.dateTime = new Date(point.start).toISOString();
                clock.textContent = time(point.start);
                const label = document.createElement("span");
                label.textContent = text[`slot${point.state[0].toUpperCase()}${point.state.slice(1)}`];
                item.setAttribute("aria-label", `${time(point.start)}–${time(point.end)}: ${label.textContent}${selected ? ` · ${text.selected}` : ""}`);
                item.append(clock, label);
                strip.append(item);
            });
            strip.hidden = !points.length;
            if (timelineStatus) {
                timelineStatus.hidden = !!points.length;
                timelineStatus.textContent = points.length ? "" : text.timelineUnavailable;
            }
        }
        if (result.state === "unknown") { details.textContent = ""; updated.textContent = ""; return; }
        const stamp = value => new Intl.DateTimeFormat(lang === "pl" ? "pl-PL" : "en-GB", {
            timeZone: "Europe/Warsaw", dateStyle: "short", timeStyle: "short"
        }).format(new Date(value));
        details.textContent = `${text.window}: ${time(result.start)}–${time(result.end)} · ${result.minTemp.toFixed(1)}–${result.maxTemp.toFixed(1)}°C · ${text.windLabel}: ${result.wind.toFixed(0)} km/h · ${text.chance}: ${result.probability.toFixed(0)}%`;
        if (["avoid", "caution"].includes(result.state)) {
            const item = document.createElement("li"); item.textContent = text.noWindow; list.append(item);
        }
        updated.textContent = `${text.times} · ${text.weather}: ${stamp(result.weatherAt)} · ${text.airLabel}: ${stamp(result.airAt)}`;
    }
    const api = { evaluate, timeline, render };
    if (typeof module === "object" && module.exports) module.exports = api;
    else root.RidePlanner = api;
})(typeof window === "object" ? window : globalThis);
