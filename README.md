# Portfolio Rafała Banasia

Responsywne portfolio dostępne pod adresem `banas.dev`. Strona prezentuje doświadczenie, projekty i umiejętności, obsługuje język polski i angielski oraz jasny i ciemny motyw. Moduł „Pogoda” łączy rzeczywiste odczyty jakości powietrza ze stacji InPost w Katowicach z danymi modelowymi Open-Meteo.

## Architektura

Projekt nie wymaga frameworka ani zewnętrznych pakietów Pythona:

- `index.html` — HTML, CSS i JavaScript strony oraz wykresy Chart.js ładowane z CDN;
- `fetch_weather.py` — serwerowy kolektor, walidacja, retencja i generowanie eksportów;
- `data.json` — ostatni poprawny odczyt InPost;
- `history.json` — godzinowa historia InPost do wykresu;
- `weather.json` — współdzielony przez wszystkich odwiedzających cache historii i prognozy Open-Meteo;
- `weather_history.db` — lokalna baza SQLite, niewersjonowana w Git.

Skrypt zapisuje pliki JSON atomowo: najpierw tworzy plik tymczasowy, a następnie podmienia wersję publiczną. Awaria jednego źródła nie blokuje drugiego. Przy błędzie API istniejąca baza pozostaje źródłem ostatnich danych, które interfejs oznacza jako nieaktualne.

## Źródła i model danych

### InPost KAT04BAPP

Stacja przy ul. Brzozowej dostarcza temperaturę, wilgotność, ciśnienie, PM2.5 i PM10. Każdy odczyt trafia do tabeli `readings` ze znacznikiem UTC i czasem lokalnym `Europe/Warsaw`. Retencja wynosi 90 dni:

```sql
DELETE FROM readings WHERE timestamp < datetime('now', '-90 days');
```

`history.json` grupuje najnowszy odczyt z każdej godziny według lokalnego dnia. Odczyty na wykresie są punktami i nie są łączone ani interpolowane, ponieważ nie znamy wartości między pomiarami.

### Open-Meteo

Kolektor pobiera bez klucza API dane dla Katowic (`50.26`, `19.02`) z Forecast API. Dla każdego niepokrywającego się przedziału 15-minutowego zapisuje w UTC:

- temperaturę;
- sumę opadu oraz osobno deszcz i śnieg;
- kod pogodowy WMO;
- prędkość i kierunek wiatru;
- czas danych, początek i koniec przedziału, czas pobrania, współrzędne i źródło.

Tabela `weather_observations` przechowuje historię modelową przez 30 dni. Pierwsze uruchomienie wykonuje dostępny bezpłatnie backfill przez `past_days=30`; rekordy mają wtedy typ `backfill_model`, aby nie udawały pomiarów zebranych przez ten serwer. Nowe rekordy mają typ `collected_model`. Unikalny klucz czasu i typu oraz atomowa transakcja chronią przed dublowaniem przy ponownym uruchomieniu.

Prognozy są zapisywane osobno w `weather_forecasts` jako kolejne snapshoty `forecast_model`; nie nadpisują historii. Eksport `weather.json` publikuje ostatni snapshot na 2 godziny do przodu w ośmiu przedziałach po 15 minut. Godzinowe prawdopodobieństwo opadu jest opisane jako godzinowe i nie jest sztucznie przeliczane na kwadranse.

Tabela `locations` pozwala rozszerzyć kolektor o następne miejsca. Lokalizacje o tych samych współrzędnych korzystają z jednego zapytania Open-Meteo w danym przebiegu.

Open-Meteo wymaga oznaczenia źródła. Integracja korzysta z bezpłatnego API na warunkach użycia niekomercyjnego i z atrybucją CC BY 4.0. Portfolio nie zawiera płatnej usługi ani reklam; przed komercjalizacją należy przejść na odpowiednią licencję. Limity i warunki mogą się zmienić, dlatego źródłem nadrzędnym są [dokumentacja API](https://open-meteo.com/en/docs) i [warunki Open-Meteo](https://open-meteo.com/en/terms).

## Interfejs pogodowy

Po otwarciu strony przeglądarka pobiera wyłącznie lokalne eksporty JSON, a nie odpytuje Open-Meteo osobno dla każdego użytkownika. `weather.json` jest sprawdzany co 5 minut, natomiast jego zawartość aktualizuje wspólny kolektor co 15 minut. Ogranicza to ruch i zachowuje działanie modułu także wtedy, gdy nikt nie ma otwartej strony.

Interfejs zawiera:

- bieżący status „Bez opadów”, deszcz, opady przelotne, śnieg, deszcz ze śniegiem, marznący deszcz lub burzę;
- informację, że wynik jest szacunkiem modelu, czas danych i oznaczenie Open-Meteo;
- prognozę najbliższych 2 godzin z temperaturą, sumą opadu na 15 minut i godzinowym prawdopodobieństwem;
- widoki: wybrany dzień, ostatnie 24 godziny, 7 dni i 30 dni;
- osobny wykres temperatury/PM oraz słupkowy wykres sum opadów;
- legendę Chart.js, która pozwala włączać i wyłączać serie, oraz tooltipy z jednostką i źródłem.

Temperatura InPost i PM są pokazane jako niepołączone punkty. Dane modelowe także nie są prezentowane jako rzekomy ciągły pomiar. Prognoza temperatury ma odróżniający ją styl przerywany, a prognozowany opad osobny kolor słupków. Stała oś temperatury obejmuje co najmniej `−20–40°C`, więc przełączanie dni nie powoduje mylącego skakania skali, a wartości ujemne mieszczą się na wykresie.

## Uruchomienie i Cron

Projekt wymaga Pythona 3.10 lub nowszego:

```bash
python3 fetch_weather.py
python3 -m http.server 8000
```

Strona będzie dostępna pod `http://localhost:8000`. Do automatycznego zbierania danych co 15 minut należy dodać:

```cron
*/15 * * * * /usr/bin/python3 /ścieżka/do/portfolio/fetch_weather.py >> /ścieżka/do/portfolio/weather.log 2>&1
```

`weather_history.db`, jego pliki pomocnicze, `*.log` i cache Pythona są wykluczone przez `.gitignore`.

## Kontrola danych

```bash
python3 fetch_weather.py
python3 -m json.tool data.json >/dev/null
python3 -m json.tool history.json >/dev/null
python3 -m json.tool weather.json >/dev/null
sqlite3 weather_history.db "PRAGMA integrity_check;"
sqlite3 weather_history.db "SELECT source_kind, COUNT(*) FROM weather_observations GROUP BY source_kind;"
sqlite3 weather_history.db "SELECT COUNT(*) FROM weather_forecasts;"
```

Przed wdrożeniem warto również sprawdzić przełączanie języka i motywu, cztery zakresy wykresów oraz szerokości desktopową i mobilną. Brak sieci nie może zostać przedstawiony jako „Bez opadów”: bez danych wyświetlany jest komunikat o niedostępności, a zachowany wynik jest jawnie oznaczony jako nieaktualny.
