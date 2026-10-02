# Portfolio Rafała Banasia

Statyczne, responsywne portfolio dostępne pod adresem `banas.dev`. Strona prezentuje doświadczenie zawodowe, projekty i umiejętności, obsługuje język polski i angielski, jasny oraz ciemny motyw, a także zawiera moduł aktualnej pogody i jakości powietrza dla Katowic.

## Struktura projektu

- `index.html` — kompletna warstwa prezentacji: HTML, CSS i JavaScript portfolio.
- `fetch_weather.py` — pobieranie, walidacja i zapis danych pogodowych.
- `data.json` — ostatni poprawny odczyt wyświetlany przez widget.
- `history.json` — publiczne dane godzinowe używane przez wykres.
- `weather_history.db` — lokalna baza SQLite z pełną historią; plik nie jest wersjonowany.

## Moduł pogodowy

Skrypt korzysta z danych czujnika InPost Air Sensor stacji `KAT04BAPP` przy ulicy Brzozowej w Katowicach. Każde uruchomienie wykonuje następujące operacje:

1. pobiera dane temperatury, wilgotności, ciśnienia, PM2.5 i PM10;
2. sprawdza obecność wszystkich wymaganych czujników;
3. zapisuje bieżący odczyt do `data.json`;
4. dopisuje pomiar do tabeli `readings` w `weather_history.db` z dokładnym znacznikiem ISO 8601 w UTC;
5. usuwa wpisy starsze niż 90 dni poleceniem:

   ```sql
   DELETE FROM readings WHERE timestamp < datetime('now', '-90 days');
   ```

6. generuje atomowo `history.json`, grupując dane według lokalnego dnia i godziny w strefie `Europe/Warsaw`.

Pełne pomiary pozostają w SQLite. Jeżeli skrypt zostanie wywołany kilka razy w ciągu godziny, plik przeznaczony dla wykresu zawiera najnowszy pomiar z tej godziny. Pliki JSON są zapisywane przez plik tymczasowy i atomową podmianę, więc strona nie zobaczy częściowo zapisanego dokumentu.

Tabela `readings` zawiera kolumny: `timestamp`, `timestamp_local`, `temperature`, `humidity`, `pressure`, `pm25` i `pm10`. Indeks znacznika czasu przyspiesza retencję i generowanie historii.

## Status opadów Open-Meteo

Po otwarciu strony frontend sprawdza aktualne opady dla Katowic (`50.26`, `19.02`) w darmowym API Open-Meteo. Zapytanie obejmuje deszcz, opady przelotne, śnieg i kod pogodowy WMO, dzięki czemu interfejs rozróżnia deszcz, przelotne opady, śnieg, deszcz ze śniegiem, marznący deszcz i burzę.

Dane są odświeżane co 5 minut. Odpowiedź oraz czas jej pobrania trafiają do `localStorage`, co zapobiega ponownemu zapytaniu po szybkim przeładowaniu strony i pozwala współdzielić świeży wynik między kartami. Żądanie ma limit czasu 10 sekund. Przy błędzie ostatni zapisany wynik jest wyświetlany jako nieaktualny; bez danych historycznych interfejs pokazuje „Pogoda niedostępna”, nigdy domyślne „Bez opadów”.

Status jest szacunkiem z modelu pogodowego, a nie pomiarem lokalnego czujnika. Interfejs zawiera wymagane oznaczenie i odnośnik do Open-Meteo. Darmowy endpoint bez klucza może być używany wyłącznie niekomercyjnie, z atrybucją CC BY 4.0 i w granicach limitów Open-Meteo. Jeśli portfolio zostanie skomercjalizowane, integracja wymaga odpowiedniej licencji lub zmiany źródła danych.

## Wykres historii 24h

Pod bieżącymi odczytami znajduje się responsywny wykres punktowy Chart.js ładowany z CDN. Oś czasu obejmuje godziny `00:00–23:00`, lewa oś przedstawia temperaturę w °C, a prawa stężenia PM2.5 i PM10 w µg/m³. Przyciski „Poprzedni dzień”, „Dzisiaj” i „Następny dzień” pozwalają poruszać się po maksymalnie 90 dniach historii. Teksty, etykiety i nawigacja są dostępne po polsku i angielsku.

## Uruchomienie

Projekt wymaga Pythona 3.10 lub nowszego i nie korzysta z zewnętrznych pakietów Pythona:

```bash
python3 fetch_weather.py
python3 -m http.server 8000
```

Następnie stronę można otworzyć pod adresem `http://localhost:8000`. Serwer HTTP jest potrzebny, ponieważ przeglądarka pobiera `data.json` i `history.json` przez `fetch()`.

## Automatyzacja przez Cron

Aby aktualizować dane na początku każdej godziny, należy otworzyć crontab poleceniem `crontab -e` i dodać wpis (ścieżkę trzeba dostosować do miejsca wdrożenia):

```cron
0 * * * * cd /ścieżka/do/portfolio && /usr/bin/python3 fetch_weather.py >> weather.log 2>&1
```

Pliki `weather_history.db`, `*.log` oraz cache Pythona są wykluczone w `.gitignore`. `data.json` i `history.json` powinny być dostępne dla serwera WWW; można je wersjonować lub generować wyłącznie w środowisku docelowym.

## Test podstawowy

Po uruchomieniu skryptu można sprawdzić artefakty i bazę:

```bash
python3 fetch_weather.py
python3 -m json.tool data.json >/dev/null
python3 -m json.tool history.json >/dev/null
sqlite3 weather_history.db "SELECT timestamp, temperature, pm25, pm10 FROM readings ORDER BY timestamp DESC LIMIT 5;"
```
