# Źródła opisów projektów — 8 listopada 2026

## Metoda i granice przeglądu

Opisy sekcji projektów uzupełniono na podstawie dokumentacji i struktury kodu
na GitHubie. To zapis przeglądu, nie automatyczny monitoring repozytoriów ani
audyt działających usług. Kod innych projektów nie był wykonywany, testy tych
projektów nie były uruchamiane. Testy opisane w README portfolio dotyczą tego
repozytorium.

Odnośniki „Kod i dokumentacja źródłowa” w kartach wskazują wersję przeglądaną
podczas tej aktualizacji. Przyciski „Kod” prowadzą do aktualnych repozytoriów.
Brak licznika gwiazdek, sztucznej „aktywności na żywo” i obietnic poprawy
wydajności. Przeglądanie portfolio nie kontaktuje się z GitHubem; użytkownik
otwiera zewnętrzny link dopiero własnym kliknięciem.

## Publiczne źródła

| Karta | Przejrzana wersja / źródło | Co potwierdza i czego nie dowodzi |
| --- | --- | --- |
| Cycling | [`71f094f`, README](https://github.com/Rafalbanas/Cycling/blob/71f094fca99aec60a8bc62f3ea2c19b4bedd9636/README.md), ostatni commit 29.10.2026 | Przegląd wyników, SHAP, porównanie modeli, czytnik pracy; kalkulator jest heurystyką, nie inferencją zapisanego modelu. Publiczny kod nie zawiera całego warsztatu badawczego. |
| Plates | [`4868be5`, README](https://github.com/Rafalbanas/automatic_plate_number_recognition/blob/4868be5ec3bb62cdb774fe83987dd1cf6257e18a/README.md), ostatni commit 29.10.2026 | Gotowe modele ONNX przez FastALPR, niezależny pipeline treningowy i możliwość jawnego przełączenia detektora. Nie sprawdzano, który detektor jest teraz aktywny. Metryki detekcji nie są dokładnością OCR. |
| CVTailor | [`e8db1ae`, opis kanoniczny](https://github.com/Rafalbanas/ai-resume-tailoring-platform/blob/e8db1aef4502d5d123f2abe61988e2089740e263/docs/project-description.md) i [README](https://github.com/Rafalbanas/ai-resume-tailoring-platform/blob/e8db1aef4502d5d123f2abe61988e2089740e263/README.md), ostatni commit 08.11.2026 | BM25, identyfikatory faktów, niezależny Truth Lock, PDF/DOCX, historia i edycja. README opisuje również opcjonalne, domyślnie wyłączone wyszukiwanie semantyczne; nie potwierdzano jego aktywacji na produkcji. Wymagane logowanie i przegląd wyniku przez człowieka. |
| Banas Chat | [`48ae3f4`, README](https://github.com/Rafalbanas/chat/blob/48ae3f44cdaa1772e258a7a0f0aac98af4973c7f/README.md), ostatni commit 24.10.2026 | Prywatne wdrożenie, konfiguracja i integracje. Open WebUI dostarcza silnik, interfejs, konta i MFA; dodatki powstały z pomocą Codex. Koordynacja GPU przez polling nie jest atomową blokadą. |
| Lanari Candle | [`59367c3`, drzewo kodu](https://github.com/Rafalbanas/lanari_candle/tree/59367c33e211115013f0627d20e0d15265517a82), ostatni commit 17.02.2026 | MVP FastAPI + HTML/JS; moduły produktów, koszyka, zamówień, schematy i migracje Alembic, `test_api_flow.py`. Brak głównego README. Nie potwierdzano działania publicznego sklepu ani prawdziwych płatności. Data aktualizacji metadanych repozytorium nie jest datą ostatniego commita. |
| Praca magisterska | Ten sam publiczny README Cycling | Perspektywa badawcza, nie osobny wdrożony produkt. Podział po zawodnikach i wariant kontrolujący wyciek etykiety. Bez publikowania surowych danych lub prywatnego PDF. |
| Administracja i automatyzacja IT | Dotychczasowy opis portfolio | Obszar praktyki i przykładowy tok pracy, nie nowy produkt ani nieistniejące repozytorium. Nie uzupełniano go danymi klientów. |
| Banas.dev | [`d70fc81`, README](https://github.com/Rafalbanas/banasdev/blob/d70fc81f4c8a68f29b68a4fb0a62258ade91e018/README.md) i lokalny kod | Statyczny interfejs, dwa źródła danych, kolektor, tabele i lokalne wykresy, testy oraz proces publikacji z rollbackiem. Nowy eksplorator jest sprawdzany lokalnie; ten dokument nie potwierdza jego wdrożenia. |

## Homelab — zakres celowo ograniczony

Na wyraźną prośbę właściciela dodano bezpieczne podsumowanie jego prywatnej
dokumentacji: stacja Ubuntu, Ryzen 5 5500 (6 rdzeni / 12 wątków), 30,7 GiB
całkowitej RAM raportowanej przez system, RTX 3060 z 12 GB VRAM, Ollama, Home Assistant OS
na KVM/libvirt oraz zarządzanie sesją graficzną i Steamem przez systemd.

Nie kopiowano dokumentów, inventory ani konfiguracji do tego repozytorium.
Nie publikujemy adresu prywatnego repozytorium, adresów IP, nazw hostów i kont,
portów, ścieżek maszyn, topologii sieci ani danych dostępowych. Brak odnośnika
„Kod” w tej karcie jest zamierzony. Nie przedstawiamy dokumentacji jako audytu
bieżącej ekspozycji sieciowej, pełnej gwarancji prywatności czy bezpieczeństwa.

Ważne rozróżnienia: zainstalowany model nie musi być załadowany; licznik
graficznej sesji obserwuje obecność wybranych procesów, nie fizyczną
bezczynność użytkownika; Home Assistant wymaga włączonego hosta.

Na osobną prośbę właściciela dodano ogólny schemat dostępu z Maca przez
jumphost VPS Mikrus. Prywatna dokumentacja usług potwierdza administracyjny
reverse SSH z punktem zwrotnym dostępnym wyłącznie lokalnie na VPS.
Rozróżniamy wychodzące zestawienie homelab → Mikrus oraz drogę klienta
Mac → Mikrus → homelab. Nie publikujemy adresów, portów, kont, kluczy,
parametrów połączenia ani szczegółowej topologii. Ten opis nie jest testem
aktualnej łączności i nie zakłada, że ten sam tunel udostępnia wszystkie API.
Zastosowanie właściciela: dostęp do lokalnego AI z Maca również poza domem,
bez wymogu stałego publicznego IP w domu, osobnego VPN lub przychodzącego
przekierowania portów na domowym routerze. To nie oznacza braku jakichkolwiek
otwartych portów: Mikrus potrzebuje osiągalnego SSH. Stacja, VPS i tunel muszą
działać. Nie deklarujemy konfiguracji Wake-on-LAN ani zdalnego włączania
wyłączonego hosta. „Bezprzewodowy” dostęp klienta nie dowodzi, że sama stacja
łączy się przez Wi-Fi.
Właściciel dodatkowo potwierdził, że trasa Mac → VPS → stacja jest już
skonfigurowana i używana w bieżącej pracy z OpenCode. To potwierdzenie
użytkownika, nie niezależny test SSH przeprowadzony w ramach zmian portfolio.
Nie wywodzimy z tego lokalizacji każdego procesu ani tego, że wszystkie
modele używane w OpenCode są lokalne; dostawcy chmurowi pozostają odrębną opcją.

Właściciel wskazał również Open WebUI jako interfejs do lokalnego AI. Opis
pokazuje wariant przeglądarka na Macu → Open WebUI → skonfigurowane Ollama,
bez zakładania lokalizacji instalacji frontendu/backendu czy nowej instalacji
Docker na stacji. Gotowe komponenty interfejsu, backendu, kont, MFA, historii,
Markdown i eksportu pochodzą z Open WebUI. Zachowano wskazane przez właściciela
autorstwo Open WebUI Inc., Timothy Jaeryang Baek i współtwórców oraz rozdział
licencji własnych dodatków i upstream. To nie jest deklaracja stworzenia
silnika czatu, licencji MIT dla Open WebUI ani audyt bieżącego wdrożenia.

## Odczyty VRAM dostarczone przez właściciela

W rozmowie 08.11.2026 właściciel przekazał odczyty `nvidia-smi` i `ollama ps`
oraz wskazał tryb bez GUI i po uruchomieniu GUI. Publikujemy wyłącznie liczby
i kontekst potrzebny do interpretacji, nie surowe logi, nazwy maszyn, ścieżki
ani identyfikatory procesów.

GPU: RTX 3060, 12288 MiB. W obu odczytach Gemma 4 12B Q4_K_M ma kontekst
65 536, a wskazany proces Ollama zajmuje 8858 MiB.

| Tryb zadeklarowany przez właściciela | Zajęte łącznie | Proces Ollama | Poza procesem Ollama | Wolne |
| --- | ---: | ---: | ---: | ---: |
| Headless | 8899 MiB | 8858 MiB | 41 MiB | 3389 MiB |
| GUI | 9088 MiB | 8858 MiB | 230 MiB | 3200 MiB |

Różnica wynosi **189 MiB**, około **2,08% odczytu z GUI**, nie 2,08% całej
pojemności karty. GNOME Shell raportuje 167 MiB, Xwayland 2 MiB (łącznie
169 MiB). Pozostałych 20 MiB różnicy te odczyty nie wyjaśniają. Nie zakładamy,
że lista procesów idealnie sumuje się do całego zużycia GPU.

Oddzielny odczyt podczas przetwarzania promptu: 8900 MiB, 91% GPU, 165 W.
Pamięć może pozostawać zaalokowana również przy GPU-Util 0%. Szybkość około
1200 tokenów/s w tym logu dotyczy **przetwarzania promptu**, nie dekodowania
odpowiedzi. Moc 165 W jest chwilowym odczytem GPU, nie poborem całego hosta.

Kolejny fragment logu generowania raportuje `tg` 63,09–64,27 tokenów/s,
96% GPU, 167 W i 8900 MiB. To obserwacja części jednego zadania, nie pomiar
średniej wydajności całych odpowiedzi ani kontrolowane porównanie trybów.

Nie traktujemy tej pary jako kontrolowanego benchmarku ani dowodu oszczędności
energii. Różnica VRAM zależy od aplikacji, modeli, kontekstu i ich stanu.
Przełącznik na stronie przegląda zapisane dane; kalkulator tylko liczy różnicę
wpisanych wartości, nie mierzy komputera i nie wywołuje poleceń.

`gui_on`, `gui_off` i `steam-tv` opisano na podstawie prywatnej dokumentacji
konfiguracji. To skrypty specyficzne dla homelabu, nie polecenia dostępne w
każdej dystrybucji. `gui_on` wymaga już zainstalowanego środowiska, dostępu
i uprawnień; nie jest instalatorem ani automatycznym logowaniem. `gui_off`
może zakończyć niezapisaną pracę. Samo RDP nie uruchamia zatrzymanego pulpitu.

## Aktualizacja opisów

1. Sprawdź najnowszy publiczny README i commit; oddziel opis kodu od stanu wdrożenia.
2. Popraw polski fallback i słowniki `translations.pl/en` w `index.html`.
3. Zaktualizuj datę przeglądu, przypięte odnośniki i ten dokument.
4. Uruchom `python3 scripts/security_policy.py --write`, `check_site.py`, testy
   jednostkowe i `scripts/check_project_explorer.py` (Playwright Chromium).
5. Nie dopisuj nowego prywatnego repozytorium ani szczegółów infrastruktury bez
   osobnej zgody właściciela.
