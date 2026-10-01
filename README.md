# banas.dev — portfolio inżynierskie

[banas.dev](https://banas.dev) to dwujęzyczne portfolio Rafała Banasia i jednocześnie osobiste laboratorium inżynierskie. Strona przedstawia doświadczenie w IT, projekty, umiejętności i wykształcenie, a także zawiera moduł „Kato na żywo” prezentujący aktualną temperaturę oraz jakość powietrza w Katowicach.

Dane pogodowe i pomiary pyłów PM2.5 oraz PM10 pochodzą ze stacji InPost **KAT04BAPP** przy ul. Brzozowej. Są cyklicznie pobierane po stronie serwera i udostępniane frontendowi jako statyczny plik JSON.

## Zawartość portfolio

Strona jest pojedynczą, responsywną aplikacją statyczną. Obejmuje:

- profil zawodowy i informacje o doświadczeniu w IT, Application Support, administracji oraz automatyce;
- projekty: Cycling, automatyzacje n8n, Plates, Lanari Candle oraz banas.dev;
- opis pracy magisterskiej dotyczącej predykcji formy kolarskiej na podstawie telemetrii i uczenia maszynowego;
- zestawienie kompetencji z zakresu systemów, automatyzacji, danych, backendu i infrastruktury;
- wykształcenie oraz odnośniki kontaktowe;
- moduł aktualnej pogody i jakości powietrza dla Katowic;
- polską i angielską wersję treści;
- jasny i ciemny motyw zapamiętywany lokalnie w przeglądarce;
- responsywną nawigację, animacje sekcji i obsługę preferencji `prefers-reduced-motion`.

Strona nie korzysta z analityki ani trackerów. Wybrany język i motyw są przechowywane wyłącznie w `localStorage` użytkownika.

## Stos technologiczny

### Frontend

- **HTML5** — semantyczna struktura całego portfolio;
- **CSS3** — responsywny układ, motyw jasny/ciemny, animacje i komponent widgetu;
- **Vanilla JavaScript** — bez frameworków i procesu budowania;
- własny system **i18n PL/EN** wraz z tłumaczeniami treści, atrybutów dostępności i komunikatów pogodowych;
- Fetch API, `Intl.NumberFormat` i `Intl.DateTimeFormat` do pobierania oraz lokalnego formatowania odczytów.

### Backend i automatyzacja

- **Python 3** — pobieranie, walidacja i przetwarzanie danych z API InPost;
- **Cron** — automatyczne odświeżanie danych co godzinę;
- **Nginx** — serwowanie statycznej strony i pliku `data.json`;
- wyłącznie standardowa biblioteka Pythona — projekt nie wymaga instalowania dodatkowych pakietów.

## Struktura projektu

```text
.
├── index.html        # struktura, style, tłumaczenia i logika interfejsu
├── fetch_weather.py  # pobieranie oraz zapis danych pogodowych
├── data.json         # ostatni poprawny zestaw odczytów dla widgetu
├── favicon.png       # ikona strony
├── cv_photo*.jpg     # zdjęcia profilowe w formacie źródłowym
├── cv_photo*.webp    # zoptymalizowane zdjęcia używane przez stronę
└── README.md
```

Pliki robocze, kopie zapasowe strony, log crona i cache Pythona są pomijane przez `.gitignore`.

## Moduł pogodowy „Kato na żywo”

Moduł rozdziela pobieranie danych od ich prezentacji. Przeglądarka nie łączy się bezpośrednio z API InPost — odczytuje przygotowany wcześniej `data.json` z tego samego serwera co strona.

```text
API InPost (KAT04BAPP)
          │
          ▼
  fetch_weather.py ── walidacja i przeliczenie norm
          │
          ▼
     data.json ────── atomowa podmiana pliku
          │
          ▼
  Nginx / Fetch API ─ widget w index.html
```

### Skrypt `fetch_weather.py`

Skrypt:

1. wysyła żądanie do endpointu InPost dla stacji `KAT04BAPP` z limitem czasu 20 sekund;
2. odczytuje temperaturę, wilgotność, ciśnienie, PM2.5 i PM10;
3. sprawdza obecność wszystkich wymaganych czujników — niepełna odpowiedź kończy się błędem zamiast opublikowania niekompletnych danych;
4. dla PM2.5 i PM10 zapisuje bieżące stężenie, procent normy oraz wyliczoną wartość normy:

   ```text
   wartość normy = zmierzone stężenie × 100 / procent normy
   ```

5. dodaje poziom jakości powietrza, identyfikator stacji, źródło i czas pobrania w UTC;
6. zapisuje wynik atomowo: najpierw tworzy plik tymczasowy w katalogu docelowym, nadaje mu uprawnienia `0644`, a następnie podmienia `data.json` przez `os.replace()`.

Atomowy zapis chroni frontend przed odczytaniem częściowo zapisanego lub uszkodzonego JSON-a. Gdy pobranie albo walidacja się nie powiedzie, poprzedni poprawny `data.json` pozostaje dostępny.

Przykładowy fragment danych:

```json
{
  "station": "KAT04BAPP",
  "fetched_at": "2026-10-01T09:00:03+00:00",
  "air_index_level": "GOOD",
  "temperature": { "value": 18.1, "unit": "°C" },
  "pm25": {
    "value": 18.3,
    "unit": "µg/m³",
    "norm_percent": 73.4,
    "norm_value": 25.0
  }
}
```

### Widget w JavaScript

Po załadowaniu strony funkcja `loadWeather()` pobiera `data.json` z opcją `cache: "no-store"`. Widget:

- rozpoczyna pracę w stanie ładowania;
- sprawdza kod odpowiedzi HTTP i obecność wymaganych pól;
- prezentuje temperaturę, wilgotność, ciśnienie, PM2.5 i PM10;
- pokazuje procent wykorzystania norm PM2.5/PM10 także w postaci pasków;
- tłumaczy poziom jakości powietrza na czytelny komunikat;
- formatuje liczby i datę odpowiednio dla `pl-PL` lub `en-GB`, a czas wyświetla w strefie `Europe/Warsaw`;
- ponownie renderuje dane po zmianie języka;
- w razie błędu przełącza się na czytelny, przetłumaczony stan niedostępności danych.

Komunikaty widgetu należą do tego samego systemu i18n co pozostała część portfolio, dlatego zmiana języka PL/EN obejmuje również stan ładowania, opis norm, datę aktualizacji, komunikaty błędów i ocenę jakości powietrza.

## Automatyczne odświeżanie przez Cron

Na serwerze pliki projektu znajdują się w katalogu `/cytrus`. Aby edytować harmonogram użytkownika uruchamiającego skrypt:

```bash
crontab -e
```

Następnie należy dodać wpis:

```cron
0 * * * * /usr/bin/python3 /cytrus/fetch_weather.py >> /cytrus/weather.log 2>&1
```

Zadanie uruchamia skrypt o pełnej godzinie, zapisując standardowe wyjście i błędy do `/cytrus/weather.log`. Użytkownik crona musi mieć prawo zapisu do `/cytrus/data.json`, katalogu `/cytrus` (na potrzeby pliku tymczasowego) i pliku logu.

Weryfikacja wpisu oraz ostatnich komunikatów:

```bash
crontab -l
tail -n 50 /cytrus/weather.log
```

## Uruchomienie i testy

### 1. Ręczne pobranie danych

W katalogu projektu uruchom:

```bash
python3 fetch_weather.py
```

Poprawne wykonanie kończy się komunikatem wskazującym zapis do `data.json`. Skrypt wymaga dostępu sieciowego do API InPost.

### 2. Walidacja skryptu i pliku JSON

```bash
python3 -m py_compile fetch_weather.py
python3 -m json.tool data.json >/dev/null
```

Można też sprawdzić kluczowe pola bez instalowania dodatkowych narzędzi:

```bash
python3 - <<'PY'
import json

with open("data.json", encoding="utf-8") as file:
    data = json.load(file)

required = {"station", "fetched_at", "temperature", "pm25", "pm10"}
missing = required - data.keys()
assert not missing, f"Brak pól: {sorted(missing)}"
assert data["station"] == "KAT04BAPP"
print("Dane pogodowe są poprawne.")
PY
```

### 3. Lokalne serwowanie strony

Pliku `index.html` nie należy otwierać bezpośrednio przez `file://`, ponieważ przeglądarka może zablokować żądanie do `data.json`. W katalogu projektu uruchom prosty serwer HTTP:

```bash
python3 -m http.server 8000
```

Następnie otwórz [http://localhost:8000](http://localhost:8000). Sam plik z danymi można sprawdzić poleceniem:

```bash
curl -fsS http://127.0.0.1:8000/data.json | python3 -m json.tool
```

W przeglądarce warto zweryfikować oba języki, zmianę motywu, widok mobilny oraz zachowanie widgetu po czasowym usunięciu lub zmianie nazwy `data.json`.

## Wdrożenie

Produkcja korzysta z Nginx, który serwuje katalog projektu jako statyczny dokument root. Po wdrożeniu należy upewnić się, że:

- `index.html` i zasoby są dostępne przez HTTPS;
- `data.json` jest serwowany jako JSON i nie jest agresywnie cache'owany przez reverse proxy;
- proces crona może atomowo zastępować `data.json`;
- ręczne uruchomienie `fetch_weather.py` kończy się powodzeniem;
- `/cytrus/weather.log` nie jest publicznie dostępny.

## Źródło danych

Dane środowiskowe pochodzą z czujnika InPost Air Sensor przy paczkomacie **KAT04BAPP** w Katowicach. Odczyty mają charakter informacyjny i zależą od dostępności oraz formatu zewnętrznego API InPost.
