# Portfolio Rafała Banasia

Statyczne portfolio dostępne pod adresem \`banas.dev\`. Sekcja „Kato na żywo” łączy pogodę z Open-Meteo i jakość powietrza z GIOŚ.

## Źródła danych

- Open-Meteo — temperatura, bieżący status opadów, prognoza na dwie godziny oraz historia temperatury i opadów.
- GIOŚ — godzinowe PM2,5, PM10 i Polski indeks jakości powietrza ze stacji:
  - Katowice, ul. Kossutha — \`814\`;
  - Katowice, ul. Dudy-Gracza — \`17318\`.

Temperatura ani opady nie są pobierane z GIOŚ lub InPost. Dane pyłowe nie są pobierane z Open-Meteo.

## Pliki

- \`index.html\` — strona, widżet oraz wykresy.
- \`fetch_weather.py\` — kolektor GIOŚ i Open-Meteo.
- \`data.json\` — aktualne dane jakości powietrza.
- \`history.json\` — historia średnich PM2,5 i PM10.
- \`weather.json\` — temperatura, opady i prognoza Open-Meteo.
- \`weather_history.db\` — lokalna baza historii, niewersjonowana.

## Harmonogram

Pogoda jest pobierana co 15 minut, a GIOŚ raz na godzinę, pięć minut po pełnej godzinie:

\`\`\`cron
*/15 * * * * cd /cytrus && /usr/bin/python3 fetch_weather.py --weather-only >> weather.log 2>&1
5 * * * * cd /cytrus && /usr/bin/python3 fetch_weather.py --air-only >> weather.log 2>&1
\`\`\`

## Uruchomienie

\`\`\`bash
python3 fetch_weather.py
python3 -m http.server 8000
\`\`\`

Wykres temperatury i pyłów pokazuje oddzielne punkty bez linii między pomiarami. Opady są prezentowane na osobnym wykresie słupkowym.
