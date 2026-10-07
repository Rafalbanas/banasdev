# Portfolio Rafała Banasia

Statyczne portfolio dostępne pod adresem `banas.dev`. Sekcja „Kato na żywo” łączy pogodę z Open-Meteo i jakość powietrza z GIOŚ.

## Źródła danych

- Open-Meteo — temperatura, bieżący status opadów, prognoza na dwie godziny oraz historia temperatury i opadów.
- GIOŚ — godzinowe PM2,5, PM10 i Polski indeks jakości powietrza ze stacji:
  - Katowice, ul. Kossutha — `814`;
  - Katowice, ul. Dudy-Gracza — `17318`.

Temperatura ani opady nie są pobierane z GIOŚ lub InPost. Dane pyłowe nie są pobierane z Open-Meteo.

## Pliki

- `index.html` — strona, widżet oraz wykresy.
- `fetch_weather.py` — kolektor GIOŚ i Open-Meteo.
- `data.json` — aktualne dane jakości powietrza.
- `history.json` — historia średnich PM2,5 i PM10.
- `weather.json` — temperatura, opady i prognoza Open-Meteo.
- `weather_history.db` — lokalna baza historii, niewersjonowana.

## Harmonogram

Pogoda jest pobierana co 15 minut, a GIOŚ raz na godzinę, pięć minut po pełnej godzinie:

```cron
*/15 * * * * cd /cytrus && /usr/bin/python3 fetch_weather.py --weather-only >> weather.log 2>&1
5 * * * * cd /cytrus && /usr/bin/python3 fetch_weather.py --air-only >> weather.log 2>&1
```

## Uruchomienie

```bash
python3 fetch_weather.py
python3 -m http.server 8000
```

Wykres temperatury i pyłów pokazuje oddzielne punkty bez linii między pomiarami. Opady są prezentowane na osobnym wykresie słupkowym.

## Konsolidacja repozytoriów

Docelowym repozytorium jest `Rafalbanas/banasdev`. Oba projekty mają wspólnego
przodka `7bfb4b2785a06bb9d1974aa0d78e4fa0bf51e5ac`. Sprawdzono wersje
`banasdev:551176297d7665023a78ff0632c48bee317479bb` oraz
`cv-portfolio:6bac944eb8c06e9838e89e7aed91208b00e24da8`.
Aktualna wersja banasdev zawiera już priorytet ładowania zdjęcia i nowszy moduł
GIOŚ + Open-Meteo. Zdjęcia, favicon i .gitignore są identyczne.

Aby zachować wszystkie oryginalne commity cv-portfolio, wykonaj w lokalnym
checkout banasdev, po zatwierdzeniu lub odłożeniu własnych zmian:

```bash
git switch main
git pull --ff-only origin main
git switch -c merge-cv-portfolio-history
git fetch https://github.com/Rafalbanas/cv-portfolio.git main
# Przerwij, jeśli repo źródłowe zmieniło się od czasu porównania.
test "$(git rev-parse FETCH_HEAD)" = "6bac944eb8c06e9838e89e7aed91208b00e24da8" || exit 1
# Zachowuje commity źródła oraz bieżące pliki banasdev.
git merge --no-ff -s ours FETCH_HEAD -m "merge: preserve cv-portfolio history in banasdev"
git merge-base --is-ancestor 6bac944eb8c06e9838e89e7aed91208b00e24da8 HEAD
git push -u origin merge-cv-portfolio-history
```

Otwórz PR z tej gałęzi do main i scal go opcją **Create a merge commit**.
Nie używaj squash ani rebase, ponieważ celem jest zachowanie oryginalnej historii.
Strategia ours została dobrana do sprawdzonych wersji; po zmianach w cv-portfolio
potrzebne jest ponowne porównanie. Ten PR dokumentacyjny sam nie importuje historii.

Po scaleniu przełącz checkout serwera i Cron na banasdev. Zachowaj lokalną bazę
weather_history.db oraz konfigurację serwera. Sprawdź stronę i aktualizacje JSON,
zaktualizuj linki, a następnie zarchiwizuj cv-portfolio jako repo tylko do odczytu.
Scalenie nie zmienia DNS ani konfiguracji wdrożenia.
