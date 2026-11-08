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
dokumentacji: stacja Ubuntu, RTX 3060 z 12 GB VRAM, Ollama, Home Assistant OS
na KVM/libvirt oraz zarządzanie sesją graficzną i Steamem przez systemd.

Nie kopiowano dokumentów, inventory ani konfiguracji do tego repozytorium.
Nie publikujemy adresu prywatnego repozytorium, adresów IP, nazw hostów i kont,
portów, ścieżek maszyn, topologii sieci ani danych dostępowych. Brak odnośnika
„Kod” w tej karcie jest zamierzony. Nie przedstawiamy dokumentacji jako audytu
bieżącej ekspozycji sieciowej, pełnej gwarancji prywatności czy bezpieczeństwa.

Ważne rozróżnienia: zainstalowany model nie musi być załadowany; licznik
graficznej sesji obserwuje obecność wybranych procesów, nie fizyczną
bezczynność użytkownika; Home Assistant wymaga włączonego hosta.

## Aktualizacja opisów

1. Sprawdź najnowszy publiczny README i commit; oddziel opis kodu od stanu wdrożenia.
2. Popraw polski fallback i słowniki `translations.pl/en` w `index.html`.
3. Zaktualizuj datę przeglądu, przypięte odnośniki i ten dokument.
4. Uruchom `python3 scripts/security_policy.py --write`, `check_site.py`, testy
   jednostkowe i `scripts/check_project_explorer.py` (Playwright Chromium).
5. Nie dopisuj nowego prywatnego repozytorium ani szczegółów infrastruktury bez
   osobnej zgody właściciela.
