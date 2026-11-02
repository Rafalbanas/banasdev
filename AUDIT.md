# Audyt i odświeżenie portfolio

Zakres: kod lokalny, semantyka HTML, zachowanie w Chromium i pojedynczy odczyt
nagłówków HTTPS `banas.dev` (30.10.2026). Nie obejmuje pełnego audytu
produkcyjnego serwera, zewnętrznych profili ani pełnej zgodności WCAG.

## Wnioski i zmiany

- **Hierarchia treści:** portfolio konkurowało z dużym modułem pogodowym.
  Doświadczenie i projekty są teraz przed pogodą; nawigacja odzwierciedla kolejność.
- **Wygląd:** spokojniejsza grafitowa paleta z zielonym akcentem, bardziej wyrazista
  typografia, większe odstępy i mniej obramowań w nawigacji. Zachowane jasny/ciemny
  motyw, PL/EN i istniejące treści zawodowe. Bez nowych fontów i bibliotek.
- **Pierwszy ekran:** krótszy opis i wyraźne hasło, główna akcja prowadzi do projektów.
- **Responsywność:** dekoracyjna poświata wychodziła poza ekran na pośrednich
  szerokościach; ograniczona do kontenera zamiast maskowania błędu przez overflow.
- **Klawiatura:** zdjęcie jest teraz natywnym przyciskiem z nazwą dostępną i wskazówką;
  Escape zamyka mobilne menu i oddaje fokus jego przyciskowi. Skip-link jest ponad
  nagłówkiem i ma tłumaczenie. Menu pozostaje dostępne także bez JavaScript.
- **Odporność:** zablokowane localStorage nie zatrzymuje inicjalizacji strony;
  nieprawidłowy zapisany język wraca do PL. Dodany canonical URL.
- **Wydajność pogody:** historia zawiera tysiące pomiarów. Tworzenie osobnego
  formattera dat dla każdego pomiaru powodowało blokowanie interakcji. Formattery
  warszawskiej daty i godziny są współdzielone między przeliczeniami.
- **Drugi etap — wykresy na żądanie:** Chart.js 4.4.7 jest teraz lokalnie razem
  z licencją MIT w `assets/vendor/`. Biblioteka ładuje się dopiero 300 px przed
  historią pogody; przeliczanie historii również czeka do tego momentu. Błąd lub
  timeout nie blokuje portfolio: użytkownik widzi komunikat PL/EN i przycisk
  ponowienia. Brak IntersectionObserver uruchamia bezpieczny wariant bez opóźniania.
  Kod repozytorium nie wymaga zewnętrznych żądań podczas odwiedzin.
  Test produkcji wykazał jednak skrypt Cloudflare Web Analytics dołączany
  przez infrastrukturę, niezależnie od HTML w repozytorium. Usunięto więc
  nieprawdziwą deklarację „bez analityki i trackerów” ze stopki PL/EN.
  Ustawień analityki Cloudflare nie zmieniano.
- **Trzeci etap — przeglądanie projektów:** wyszukiwarka po nazwach, opisach
  i technologiach oraz łączone z nią filtry „Dane i AI”, „Automatyzacja i IT”,
  „Web i backend”. Wyszukiwanie ignoruje wielkość liter, nadmiarowe spacje
  i polskie znaki (w tym ł). Indeks obejmuje obie wersje językowe, więc zmiana
  PL/EN nie usuwa zapytania ani wyników. Licznik ogłasza wyniki czytnikom ekranu,
  a reset klawiaturą przywraca wszystkie karty i fokus pola wyszukiwania.
  Puste grupy są ukrywane, brak wyników ma osobny komunikat. Bez JavaScript
  narzędzia są ukryte, a wszystkie projekty pozostają dostępne.
  Zapytania nie są wysyłane na serwer ani utrwalane w localStorage lub adresie URL.

## Pochodzenie biblioteki

Pliki pobrano z `https://cdn.jsdelivr.net/npm/chart.js@4.4.7/`:
`dist/chart.umd.min.js` i `LICENSE.md`. Porównanie bajtowe z upstream wykonano
ponownie po integracji. SHA-256 lokalnego JS:
`206b6e8bb00fc7bba2c7ee80ca41db3e9e05ba7be0aa35abeba9cfd5357f5d0e`.

## Sprawdzenia

```bash
python3 -m unittest discover -s tests -v
python3 scripts/browser_smoke.py
```

Drugi test wymaga pakietu Python `playwright` i zainstalowanego Chromium
(`python3 -m playwright install chromium`). Uruchamia własny lokalny serwer na
wolnym porcie. Sprawdza PL/EN, oba motywy, szerokości 320/375/768/1024/1440,
menu, klawiaturę, zakresy pogody, brak dostępu do zapisu, awarię lokalnej biblioteki,
ponowienie ładowania i stronę bez JS. Weryfikuje też opóźnione ładowanie wykresów
i brak zewnętrznych żądań. Test pakowania sprawdza bibliotekę oraz licencję.
Przeglądarka sprawdza też kategorie i wyszukiwarkę projektów: łączenie filtrów,
znaki diakrytyczne, zachowanie PL/EN, brak wyników, reset klawiaturą i brak
interpretowania zapytania jako HTML. Osobne testy statyczne pilnują semantyki
etykiet, przycisków i progresywnego ulepszania.
Testy nie pobierają nowych danych pogodowych ani nie wdrażają strony.

Końcowy wynik drugiego etapu: 15 testów jednostkowych/integracyjnych OK;
test przeglądarkowy OK (w tym wariant bez IntersectionObserver); walidacja HTML,
kotwic, składni JavaScript i `git diff --check` OK.

Końcowy wynik trzeciego etapu: 20 testów jednostkowych/integracyjnych OK;
rozszerzony test przeglądarkowy filtrów i wyszukiwarki OK; walidacja HTML,
kotwic, składni JavaScript i `git diff --check` OK.

## Wymagania odbiornika wdrożeń

Paczka ma dwa nowe pliki. Jawne listy dozwolonych plików w `scripts/package.py`
i `deploy/deploy.py` zostały rozszerzone bez luzowania walidacji archiwum.
**Przed wysłaniem nowej paczki należy zaktualizować zainstalowany na VPS odbiornik
`deploy.py` zgodnie z procedurą administracyjną projektu.** Stary odbiornik
odrzuci nowe pliki jako nieoczekiwane. Aktualizacja odbiornika wymaga kopii
poprzedniego pliku i zachowania uprawnień root:root 755. Nie wymaga zmiany
konfiguracji Nginx, Cloudflare, bazy ani harmonogramu kolektora.

## Przygotowanie wydania produkcyjnego — 30 października 2026

Przed wydaniem porównano lokalną bazę z działającą produkcją. Produkcja zawierała
już nowszy profil i projekty z `origin/main` (`5b2acb8`). Zachowano ukończone
studia, Tier 2 WAVE PTX, działające Plates, aktualny zakres CVTailor i Banas Chat,
publiczny e-mail oraz ograniczenia interpretacji wyników Cycling. Połączono je
z nową stylistyką, lokalnymi wykresami i filtrami; testy treści z upstream
pozostały zachowane. Dane pogodowe nie wchodzą do paczki.

Walidacja po integracji: 25 testów OK oraz testy przeglądarkowe PL/EN, motywów,
pięciu szerokości, filtrów, klawiatury i ładowania wykresów OK. Poprawiono
niestabilny timestamp wpisu `revision.txt` w ZIP, który mógł zmieniać digest
identycznego źródła i zakłócać wskazanie poprzedniej wersji; dodano test regresji.

### Walidacja na produkcji

Wdrożenie wykonano lokalnym odbiornikiem na VPS, po aktualizacji jego jawnej
listy plików i zapisaniu kopii poprzedniej wersji w `/var/backups/banasdev/`.
Przełączenie `current` jest atomowe; dane pogodowe i SQLite pozostały w `/cytrus`.
Publiczny HTTPS zwrócił poprawne revision.txt, bibliotekę i licencję zgodne bajtowo
ze źródłem oraz trzy poprawne pliki JSON. Chromium przez publiczne Cloudflare
potwierdziło PL/EN, oba motywy, pięć szerokości ekranu, filtry, klawiaturę,
publiczny e-mail, opóźnione ładowanie Chart.js i wszystkie zakresy wykresów,
bez błędów JavaScript ani nieudanych żądań.
Konfiguracji Nginx i Cloudflare nie zmieniano. Kod zapisano na lokalnej gałęzi
`feat/portfolio-modernization-2026` z zachowaniem historii bieżącej produkcji;
nie wykonywano push na GitHub. Przed następnym wdrożeniem z GitHub Actions
należy włączyć tę historię do `main` (ochrona ancestry odrzuci starszą gałąź).

## Dalsze rekomendacje

- HTTP prawidłowo przekierowywał 301 do HTTPS. Publiczny HTTPS odpowiadał 200,
  ale nagłówek HSTS miał `max-age=0` (wyłączony).
  W odczytanej odpowiedzi nie było też CSP, `X-Content-Type-Options` ani
  `Referrer-Policy`. Warto przejrzeć je osobno w konfiguracji serwera/Cloudflare.
  Nie włączać HSTS dla subdomen bez sprawdzenia ich HTTPS; CSP musi uwzględniać
  obecne skrypty i style inline oraz lokalną bibliotekę wykresów.
  W tym zadaniu nagłówków nie zmieniano.
- W kolejnym etapie wydzielić CSS oraz logikę portfolio i pogody z dużego HTML;
  wymaga to także aktualizacji listy plików w paczce wdrożeniowej.
- Wykonać Lighthouse na produkcji i ręczne testy czytnikiem ekranu oraz w Safari
  i Firefox. Lokalne testy Chromium nie zastępują tych pomiarów.
- Zdjęcie Open Graph jest małe (400 × 300); warto przygotować osobną grafikę
  udostępniania 1200 × 630 zamiast rozciągać zdjęcie profilowe.

Zmiany wdrożeniowe zastane w `deploy/` pozostawiono bez ingerencji.
