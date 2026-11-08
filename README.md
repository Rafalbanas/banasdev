# Portfolio Rafała Banasia

Statyczne portfolio dostępne pod adresem `banas.dev`. Sekcja „Kato na żywo” łączy pogodę z Open-Meteo i jakość powietrza z GIOŚ.

## Aktualizacja portfolio — 28 października 2026

Treści PL/EN obejmują aktualne wsparcie Tier 2 WAVE PTX, ukończone studia
magisterskie oraz projekty CVTailor, Cycling, Plates i Banas Chat.
Informacje zawodowe zweryfikowano z profilem CV właściciela; prywatny profil,
telefon i szczegóły umowy nie są publikowane w tym repozytorium.

Publiczne źródła opisów i ograniczeń projektów:

- [CVTailor — opis kanoniczny](https://github.com/Rafalbanas/ai-resume-tailoring-platform/blob/main/docs/project-description.md)
  i [README](https://github.com/Rafalbanas/ai-resume-tailoring-platform): kod lokalnego RAG/BM25
  nie jest sam w sobie potwierdzeniem wdrożenia tej funkcji. Aplikacja wymaga logowania.
- [Cycling](https://github.com/Rafalbanas/Cycling): wyniki pracy magisterskiej;
  kalkulator heurystyczny nie wykonuje inferencji ML ani pomiaru progu fizjologicznego.
- [Plates](https://github.com/Rafalbanas/automatic_plate_number_recognition):
  publiczne demo ALPR z gotowymi modelami i osobnym pipeline treningowym.
- [Banas Chat](https://github.com/Rafalbanas/chat): prywatne wdrożenie Open WebUI,
  z zachowaniem autorstwa komponentów upstream.

Walidacja lokalna (Python 3 i Node.js w `PATH`):

```bash
python3 scripts/check_site.py
python3 -m unittest discover -s tests -v
```

Testy portfolio kontrolują zgodność polskiej treści bez JavaScript ze słownikiem,
kompletność tłumaczeń PL/EN, aktualny profil i linki projektowe.

## Nowe funkcje

**Przycisk "Powrót na górę"**
Dodano przycisk „Powrót na górę” (Back to Top), który pojawia się podczas przewijania jednego ekranu, obsługuje PL/EN, klawiaturę, preferencję ograniczenia animacji, bez JS ukryty.

Opcjonalna walidacja (wymaga Playwright i Chromium):
```bash
python3 scripts/check_back_to_top.py
```

## CI/CD

GitHub Actions sprawdza każdy push i PR. Po udanych testach push do `main`
automatycznie wdraża sprawdzoną paczkę na VPS przez ograniczone SSH.
Można też uruchomić workflow ręcznie na `main`. Wdrożenie przełącza wersję
atomowo, sprawdza stronę i przy błędzie przywraca poprzednią wersję.
Dane pogodowe i baza SQLite pozostają na serwerze.

Szczegóły konfiguracji, sekretów i odzyskiwania: [deploy/README.md](deploy/README.md).

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

## Przeglądanie projektów

Sekcja projektów ma lokalną wyszukiwarkę i filtry obszarów. Karty oznacza się
atrybutem `data-project-categories` (`data`, `automation`, `web`; możliwe jest
kilka wartości rozdzielonych spacją). Wyszukiwanie obejmuje tytuł, opis i tagi
w obu językach, nie rozróżnia wielkości liter ani polskich znaków. Zapytanie
nie trafia na serwer ani do localStorage. Bez JavaScript wszystkie karty
pozostają widoczne. Teksty interfejsu są w `translations.pl/en` w grupach
`projects`, `explorer`, `cases` i `headless`.

Każda z dziewięciu kart ma rozwijane case study: cel i wkład, przepływ oraz
weryfikację i ograniczenia. JavaScript dodaje zakładki obsługiwane strzałkami,
Home/End, klikalne technologie i przełącznik karty/lista. Bez JS wszystkie
trzy części są dostępne przez natywne `<details>`. Wybór technologii czyści
filtr obszaru i wpisuje widoczną nazwę w wyszukiwarkę; widok listy nie zmienia
wyników ani nie zapisuje dodatkowych preferencji.

Nowa karta **Homelab** opisuje Ubuntu, Ryzen 5 5500 (6 rdzeni / 12 wątków),
30,7 GiB RAM raportowanej przez system, lokalne AI, Home Assistant na KVM/libvirt
i zarządzanie sesją graficzną. Dokumentacja pozostaje prywatna. Daty przeglądu,
przypięte publiczne źródła oraz granice opisów: [PROJECT_SOURCES.md](PROJECT_SOURCES.md).
Przegląd projektów nie wysyła zapytań do GitHuba ani danych wpisywanych w wyszukiwarkę.

W zakładce celu homelabu jest porównanie **headless / GUI na żądanie**.
Przełącznik zmienia opis i zapisany odczyt VRAM, a nie stan zdalnego komputera.
Właściciel dostarczył parę odczytów z tym samym modelem i pamięcią procesu
Ollama: 8899 MiB bez GUI oraz 9088 MiB z GUI (różnica 189 MiB). To przykład,
nie uniwersalny benchmark ani obietnica oszczędności energii.

Kalkulator przyjmuje dwa całkowite odczyty w zakresie 0–12288 MiB, obsługuje
spadek, wzrost, równość i błędne dane. Początkowo pola są puste; osobny przycisk
wstawia rzeczywisty przykład właściciela. Nie ma zapisu, wysyłania danych ani
uruchamiania poleceń. Bez JS oba opisy trybów i wyniki pomiarów są czytelne,
a nieaktywne kontrolki i kalkulator pozostają ukryte.
Ogólny schemat **Mac → VPS Mikrus → homelab** objaśnia rolę jumphosta i
wychodzącego reverse SSH, bez parametrów połączenia. Nie jest to publiczny
panel dostępu ani informacja o bieżącym stanie tunelu.
Właściciel potwierdził korzystanie z tej trasy podczas pracy z OpenCode.
Open WebUI opisano jako gotową warstwę interfejsu do modeli, z zachowaniem
autorstwa i licencji upstream; nie jest to autorski silnik czatu.

Opcjonalne sprawdzenie interakcji (wymaga Playwright i Chromium):

```bash
python3 scripts/check_project_explorer.py
python3 scripts/browser_smoke.py
```

## Harmonogram

Pogoda jest pobierana co 15 minut, a GIOŚ raz na godzinę, pięć minut po pełnej
godzinie. Docelowo przez `/etc/cron.d/banasdev-weather` na dedykowanym koncie
bez uprawnień roota, z danymi w `/var/lib/banasdev-weather`:

```cron
*/15 * * * * banasdev-weather BANASDEV_DATA_DIR=/var/lib/banasdev-weather /usr/bin/python3 /var/lib/banasdev/current/fetch_weather.py --weather-only >> /var/lib/banasdev-weather/weather.log 2>&1
5 * * * * banasdev-weather BANASDEV_DATA_DIR=/var/lib/banasdev-weather /usr/bin/python3 /var/lib/banasdev/current/fetch_weather.py --air-only >> /var/lib/banasdev-weather/weather.log 2>&1
```

Nie wklejać tego formatu do crontaba użytkownika. Migracja istniejącej bazy,
uprawnień i symlinków wymaga operatora; procedura w [deploy/README.md](deploy/README.md).

## Uruchomienie

Wyniki przeglądu UX i technicznego oraz polecenia testów: [AUDIT.md](AUDIT.md).
Aktualny audyt i status poprawek: [UX_SECURITY_AUDIT.md](UX_SECURITY_AUDIT.md).
Po zmianach skryptów lub stylów inline zaktualizuj hashe CSP przez
`python3 scripts/security_policy.py --write`; walidacja odrzuca nieaktualną politykę.

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
