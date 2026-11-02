# Audyt UX i bezpieczeństwa — 31.10.2026

## Status po poprawkach

Poniższe ustalenia i numery linii dokumentują stan **sprzed poprawek**.

- U1: nawigacja menu, brand i CTA przenoszą fokus na nagłówek docelowej sekcji;
  skip-link zachowuje działanie natywne.
- U2: rozwijana tabela przedstawia wszystkie osiem serii z wykresów dla aktywnego
  zakresu, oddziela zebrane dane/backfill/prognozę i oznacza braki przez —.
  Działa niezależnie od powodzenia ładowania Chart.js. Poprawiono też agregację,
  która wcześniej mogła interpretować brak wartości jako zero.
- U3: dane GIOŚ starsze niż 3 godziny, błędnie datowane i nadmiernie przyszłe
  mają ostrzeżenie zamiast pozytywnej oceny; wiek jest sprawdzany również podczas
  pozostawienia otwartej strony. Pobieranie ma timeout i sprawdzanie struktury.
- U4: uzupełniono tłumaczenia nazw dostępnych nawigacji i grup technologii.
- Dodano kontakt na pierwszym ekranie oraz prostsze podsumowania trzech głównych
  projektów z rozwijanymi szczegółami i zachowaniem ograniczeń.
- B4: usunięto składanie prognozy przez innerHTML; dane trafiają do DOM jako tekst
  lub wartości atrybutów. Dodano regresję ze złośliwą wartością pola JSON.
- B3: HTML egzekwuje CSP opartą na hashach, bez dowolnych skryptów inline i eval.
  `scripts/security_policy.py --write` odświeża hashe, a CI sprawdza ich zgodność.
  Konfiguracja Nginx uzupełnia frame-ancestors, DENY, nosniff i referrer policy.
- B1/B2: w repozytorium przygotowano cron nieuprzywilejowanego konta, izolowany
  katalog danych i etapowe HSTS tylko dla hosta. **Aktywacja na VPS, migracja
  danych oraz usunięcie nadpisywania HSTS przez Cloudflare pozostają zadaniem
  operatora. Żadna z tych zmian nie została tu wdrożona.** Procedura i warunki
  rollbacku znajdują się w `deploy/README.md`.

Walidacja po poprawkach: **34 testy OK**, zgodność hashy CSP, zasobów, kotwic
i składni JS OK. Izolowana instancja Nginx potwierdziła składnię, nagłówki dla
stron/zasobów/404 oraz przekierowanie HTTP. Testy nie uruchamiały produkcyjnego
kolektora ani nie przeładowywały aktywnego Nginx.

Przed wydaniem ponownie wykonano pełny test Chromium — **OK**: PL/EN, motywy,
pięć szerokości, fokus klawiatury, tabela, filtry, lazy loading, awaria/retry,
brak zewnętrznych żądań i wariant bez JS. Usunięto z testu użycie eval w
wait_for_function (niezgodne z CSP) i dodano oczekiwanie na asynchroniczny toggle
tabeli. Nie zmieniano polityki bezpieczeństwa w celu przepuszczenia testów.
Wcześniejsze timeouty i restart opisane poniżej pozostają historią walidacji,
nie aktualnym wynikiem. Nie deklaruje się pełnej zgodności WCAG.
Brak Node.js rozwiązano przez istniejący runtime Playwright w lokalnym PATH;
nie instalowano globalnych pakietów. Wynik wdrożenia i kopie operatora są
rejestrowane oddzielnie od historycznych ustaleń audytu.

## Zakres i wiarygodność

Przegląd bieżącego repozytorium oraz pasywny odczyt publicznego HTML,
nagłówków HTTP/HTTPS i `data.json` z banas.dev. Bez skanowania infrastruktury,
testowania zewnętrznych aplikacji, wdrażania ani zmian w konfiguracji serwera.
Zastane zmiany w `deploy/` pozostawiono bez ingerencji.

Kryterium ukończenia: wskazanie sprawdzalnych problemów z dowodami,
priorytetem i zaleceniem; oddzielenie potwierdzonych ustaleń od ryzyk
warunkowych. Ten przegląd nie potwierdza pełnej zgodności WCAG ani odporności
produkcyjnej infrastruktury.

## UX i dostępność

### U1 — Średni: nawigacja przewija, ale nie przenosi fokusu

- `index.html:4325–4336`: obsługa linków menu anuluje natywne działanie,
  przewija do sekcji i zmienia URL, ale nie ustawia fokusu celu.
- W menu mobilnym dodatkowo zamyka kontener, w którym znajduje się wybrany
  klawiaturą link (`1460–1485`, `4209–4215`). Użytkownik nie dostaje jawnego
  przejścia fokusu do nowej treści. Dokładne zachowanie kolejnego Tab wymaga
  sprawdzenia w przeglądarce i czytniku.
- Zalecenie: po nawigacji ustawiać fokus na nagłówku docelowej sekcji lub
  sekcji z `tabindex="-1"`, bez dodatkowego przewijania. Sprawdzić mobilną
  klawiaturę, powiększenie oraz kolejność Tab po wyborze pozycji.

### U2 — Średni: wykresy nie udostępniają równoważnej historii tekstowo

- `index.html:2444–2455`: dwa canvas mają nazwy dostępne, ale nie mają
  równoważnej tabeli ani tekstowych wartości historycznych. Opis typu wykresu
  i bieżące odczyty nie zastępują danych z wybranego dnia/zakresu.
- Użytkownik czytnika może wybrać zakres, ale nie odczyta przedstawionego
  przebiegu temperatury, pyłów i opadów.
- Zalecenie: dodać rozwijaną tabelę danych dla aktywnego zakresu i krótkie
  podsumowanie (czas, min/max, braki danych), dostępne bez interakcji z canvas.

### U3 — Średni: stare dane jakości powietrza nadal wyglądają jak poprawny stan

- `index.html:3181–3236`: poprawnie sparsowany `data.json` zawsze daje stan
  `ready` i etykietę indeksu. Kod pokazuje datę pomiaru, ale nie sprawdza jego
  wieku. Dla opadów analogiczne ostrzeżenie istnieje (`3297–3304`, `3336`).
- Po zatrzymaniu kolektora można nadal zobaczyć pozytywną etykietę jakości
  powietrza bez wyraźnego ostrzeżenia. Lokalny JSON pochodzi z 5 października;
  publiczny JSON podczas audytu był z 31 października — nie stwierdzono obecnie
  wielodniowej awarii produkcji.
- Zalecenie: ustalić próg świeżości zgodny z opóźnieniami GIOŚ, wyświetlać
  „Dane nieaktualne” z czasem pomiaru; nie pokazywać starego indeksu jako
  aktualnej oceny. Dodać test ze starym timestampem.

### U4 — Niski: etykiety nawigacji pozostają po polsku w wersji EN

- `index.html:1876` ma stałe `aria-label="Główna nawigacja"` bez tłumaczenia;
  podobnie część etykiet technologii na kartach (`2138`, `2153`). `setLanguage`
  tłumaczy tylko elementy oznaczone odpowiednimi atrybutami (`4168–4192`).
- Zalecenie: objąć te nazwy słownikiem PL/EN. Bez zmiany poprawnych nazw
  własnych i bez dodawania zbędnych aria-label do zwykłych linków tekstowych.

### Rekomendacje produktowe do sprawdzenia z użytkownikami

- Pierwszy ekran ma CTA do projektów, GitHuba i LinkedIna (`1912–1916`),
  lecz brak bezpośredniego „Napisz do mnie”. Dla celu rekrutacyjnego warto
  przetestować kontakt jako drugą akcję obok projektów.
- Opisy głównych projektów zaczynają od specjalistycznych pojęć (FTP, SHAP,
  ALPR, BM25). Warto dodać jednozdaniowe „problem → rezultat → moja rola”,
  zachowując ograniczenia i szczegóły techniczne jako rozwinięcie.
- Nie są to wykazane błędy ani wyniki badania konwersji. Bez działającej
  walidacji wizualnej nie oceniano kontrastu, estetyki i łamania układu.

Poprawne elementy sprawdzone w kodzie: skip-link widoczny po fokusie,
etykieta pola wyszukiwania połączona przez `for`/`id`, `aria-pressed` dla
języków i filtrów, komunikat wyników live, obsługa reduced-motion i
fallback treści bez JS. Nie zgłasza się ich jako błędów.

## Bezpieczeństwo

### B1 — Wysoki, warunkowy: kod z paczki wdrożeniowej może działać jako root

- `deploy/deploy.py:18–23, 77–92` dopuszcza `fetch_weather.py`, sprawdza tylko
  jego składnię i przełącza aktywne wydanie. SHA-256 sprawdza spójność paczki,
  nie jej zaufane pochodzenie: nadawca sam podaje digest.
- `deploy/collector.cron:2–3` uruchamia kolektor z aktywnego wydania;
  `deploy/README.md:69` odwołuje się do crontaba roota.
- Jeśli te zadania faktycznie działają jako root, przejęcie klucza wdrożeniowego
  pozwala podmienić kolektor, a następnie wykonać kod z uprawnieniami roota przy
  kolejnym uruchomieniu cron. Forced command SSH nie ogranicza tego skutku.
  Kontrola ancestry jest po stronie workflow, nie odbiornika.
- Zalecenie: uruchamiać kolektor na dedykowanym nieuprzywilejowanym koncie,
  z zapisem wyłącznie do katalogu danych; oddzielić aktualizację kolektora od
  statycznego frontendu, jeśli klucz ma służyć tylko do publikacji strony.
- Nie sprawdzano aktywnego crontaba ani uprawnień VPS. Potwierdzony jest
  przepływ w kodzie i dokumentacji, nie możliwość wykorzystania na produkcji.

### B2 — Średni, potwierdzony na produkcji: HSTS wyłączony na publicznym brzegu

- HTTPS zwrócił `Strict-Transport-Security: max-age=0; includeSubDomains`.
  HTTP zwrócił prawidłowe 301 do HTTPS, lecz samo przekierowanie nie zapewnia
  ochrony zapamiętanego HSTS.
- Zastany `deploy/nginx-public.conf:34` deklaruje rok HSTS — odpowiedź publiczna
  różni się więc od tego pliku. Nie ustalono, która warstwa nadpisuje nagłówek.
- Zalecenie: sprawdzić efektywną konfigurację Nginx i Cloudflare, zacząć od
  krótkiego dodatniego max-age, potem wydłużać. `includeSubDomains` i preload
  dopiero po weryfikacji HTTPS wszystkich subdomen.

### B3 — Średni, potwierdzony brak warstw ochronnych: CSP i blokada ramek

- Publiczna odpowiedź nie zawiera CSP ani X-Frame-Options, nie ma też
  X-Content-Type-Options i Referrer-Policy.
- Brak tych nagłówków sam w sobie nie dowodzi XSS. Ułatwia jednak skutki
  ewentualnego wstrzyknięcia i nie ogranicza osadzania portfolio w obcej ramce.
- Zalecenie: wdrożyć CSP najpierw Report-Only (z osobno egzekwowanym zakazem
  ramek), potem politykę egzekwowaną z `frame-ancestors 'none'`, `object-src
  'none'` i ograniczonym `base-uri`; dodać `nosniff` i jawną Referrer-Policy.
  Skrypty i style inline wymagają hashy/nonce lub wydzielenia plików.
- Aktualny publiczny HTML zawiera Cloudflare Rocket Loader. Politykę trzeba
  sprawdzić na rzeczywistej odpowiedzi, nie tylko na lokalnym HTML; nie kopiować
  bezrefleksyjnie restrykcyjnej polityki blokującej obecny interfejs.

### B4 — Niski, warunkowy: surowy atrybut z JSON trafia do innerHTML

- `index.html:3417–3428`: `probability_interval_start_utc` trafia bez escaping
  do `title` w szablonie `point.innerHTML`.
- Podmieniony JSON może przerwać atrybut i dodać element z obsługą zdarzenia.
  Potwierdzono interpretację takiego ciągu parserem HTML, nie wykonanie JS
  w przeglądarce. Nie wykazano ścieżki zapisu tego pola przez anonimowego gościa.
- Kolektor normalnie generuje te daty przez `iso_utc`
  (`fetch_weather.py:587–635`), co istotnie ogranicza aktualną ekspozycję.
- Zalecenie: tworzyć elementy przez DOM, tekst przez `textContent`, a daty
  przypisywać przez `setAttribute`; dodatkowo walidować strukturę danych.

## Wykonane sprawdzenia i ograniczenia

- `python3 -m unittest discover -s tests -v`: 21 uruchomionych testów OK,
  ale całość FAILED: inicjalizacja `test_portfolio` wymaga niedostępnego `node`.
- `python3 scripts/check_site.py`: przerwane na walidacji JS z tego samego
  powodu. Nie uznaje się pełnej walidacji za zaliczoną.
- `python3 scripts/browser_smoke.py`: FAILED — timeout oczekiwania na gotowy
  widżet pogody. Kolejne próby diagnostyczne napotkały timeout startu Chromium.
  Nie ustalono przyczyny pierwszego timeoutu; nie przypisano go błędowi strony
  ani wyłącznie środowisku. Brak aktualnej walidacji wizualnej i interakcyjnej.
- `python3 -m compileall -q fetch_weather.py scripts deploy tests`: OK.
- `bash -n deploy/ssh-command.sh`: OK.
- `git diff --check`: OK przed dodaniem raportu.
- Publiczny HTTPS: 200; HTTP: 301 do HTTPS. Produkcyjny JSON jakości powietrza
  zawierał pomiar z 31.10.2026 10:00 UTC i pobranie z 11:05 UTC.

Mocne strony: jawna lista plików w paczce, limit rozmiaru, ochrona przed
path traversal, przypięte rewizje GitHub Actions, weryfikacja hosta SSH,
atomowe przełączenie i przetestowany rollback; linki nowych kart mają noopener.
To nie zastępuje sprawdzenia rzeczywistych uprawnień i konfiguracji serwera.
