# Portfolio Rafała Banasia

Statyczne, responsywne portfolio dostępne pod adresem \`banas.dev\`. Strona obsługuje język polski i angielski, jasny oraz ciemny motyw, a także zawiera moduł jakości powietrza dla Katowic.

## Struktura projektu

- \`index.html\` — kompletna warstwa prezentacji portfolio.
- \`fetch_weather.py\` — pobieranie, walidacja i zapis danych GIOŚ. Nazwa została zachowana ze względu na istniejącą automatyzację.
- \`data.json\` — ostatni wspólny odczyt obu stacji.
- \`history.json\` — publiczne dane godzinowe używane przez wykres.
- \`weather_history.db\` — lokalna baza SQLite z historią; plik nie jest wersjonowany.

## Dane jakości powietrza

Skrypt korzysta z oficjalnego API Głównego Inspektoratu Ochrony Środowiska:

- Katowice, ul. Kossutha — stacja \`814\`;
- Katowice, ul. Dudy-Gracza — stacja \`17318\`.

Przy każdym uruchomieniu skrypt:

1. pobiera listy stanowisk i automatycznie wybiera działające stanowiska PM2,5 oraz PM10;
2. pobiera godzinowe pomiary i indeks jakości powietrza obu stacji;
3. wybiera najnowszą wspólną godzinę pomiaru;
4. wylicza średnie miejskie PM2,5 i PM10;
5. zapisuje bieżący wynik do \`data.json\`;
6. zapisuje do tabeli \`air_readings\` średnie i wartości obu stacji;
7. generuje atomowo \`history.json\` i usuwa historię starszą niż 90 dni.

Wyniki GIOŚ są danymi jednogodzinnymi w czasie lokalnym. Strona i skrypt odświeżają dane raz na godzinę.

## Uruchomienie

Projekt wymaga Pythona 3.10 lub nowszego i nie korzysta z zewnętrznych pakietów:

\`\`\`bash
python3 fetch_weather.py
python3 -m http.server 8000
\`\`\`

Strona będzie dostępna pod adresem \`http://localhost:8000\`.

## Automatyzacja przez cron

\`\`\`cron
5 * * * * cd /ścieżka/do/portfolio && /usr/bin/python3 fetch_weather.py >> weather.log 2>&1
\`\`\`

Uruchomienie pięć minut po pełnej godzinie daje GIOŚ czas na opublikowanie nowego pomiaru. Interwał odpowiada godzinowej częstotliwości aktualizacji API.

## Test podstawowy

\`\`\`bash
python3 fetch_weather.py
python3 -m json.tool data.json >/dev/null
python3 -m json.tool history.json >/dev/null
sqlite3 weather_history.db "SELECT timestamp, pm25, pm10 FROM air_readings ORDER BY timestamp DESC LIMIT 5;"
\`\`\`
