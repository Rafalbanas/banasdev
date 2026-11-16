Wybrane realizacje / 01 — 03

# Od problemu do działającego narzędzia.

Nie tylko lista technologii. Trzy historie o danych, decyzjach i tym, gdzie kończą się możliwości rozwiązania.

01

CVTailor / Python · BM25 · AI

## Lepsze CV. Nie zmyślone CV.

Dopasowanie dokumentu do oferty, bez dopisywania doświadczenia, którego nie było.

FACTS → DOCUMENT

01 / CV + oferta / job

↓

02 / BM25 + fact IDs

↓

03 / Truth Lock → PDF / DOCX

Generowanie ≠ weryfikacja

### Problem → decyzja

Model językowy potrafi napisać przekonujący tekst — również wtedy, gdy nie ma racji. Dlatego wyszukiwanie BM25 wybiera fakty, a osobna warstwa Truth Lock kontroluje wynik.

### Co składa się na rozwiązanie

- Identyfikatory faktów zamiast swobodnego wymyślania historii.
- Edycja, historia oraz eksport PDF i DOCX.

Granice: wymagane logowanie i sprawdzenie dokumentu przez człowieka. Opcjonalne wyszukiwanie semantyczne w kodzie nie potwierdza jego aktywacji na produkcji.

[Otwórz aplikację · logowanie  ↗](https://cv.banas.dev/)[Kod i dokumentacja  ↗](https://github.com/Rafalbanas/ai-resume-tailoring-platform)

02

Cycling / Python · ML · SHAP

## Rower spotyka analizę danych.

Projekt z pracy magisterskiej: porównanie modeli i interpretacja wyników, nie tylko jedna liczba na ekranie.

DATA → UNDERSTANDING

01 / MMP20 + features

↓

02 / Models + validation

↓

03 / SHAP + results

Wynik potrzebuje kontekstu

### Problem → decyzja

Dobry wynik modelu nie wystarcza, jeśli dane przeciekają między treningiem a testem. Opis badań uwzględnia podział po zawodnikach i wariant kontrolujący wyciek etykiety.

### Co można obejrzeć

- Porównanie modeli oraz interpretację SHAP.
- Wyniki pracy i osobny kalkulator heurystyczny.

Granice: kalkulator nie uruchamia modelu ML ani nie mierzy progu fizjologicznego. Publiczne repozytorium nie zawiera całego warsztatu badawczego.

[Zobacz projekt  ↗](https://cycling.banas.dev/)[Kod i dokumentacja  ↗](https://github.com/Rafalbanas/Cycling)

03

Plates / Computer vision · ONNX · OCR

## Najpierw znajdź. Potem odczytaj.

Rozpoznawanie tablic rejestracyjnych jako przepływ dwóch różnych zadań: detekcji i OCR.

IMAGE → TEXT

01 / Image input

↓

02 / Plate detection

↓

03 / OCR → text

Detekcja ≠ dokładność OCR

### Problem → decyzja

Odnalezienie tablicy na zdjęciu nie oznacza jeszcze poprawnego odczytu znaków. Demo korzysta z gotowych modeli ONNX przez FastALPR; pipeline treningowy jest osobnym elementem projektu.

### Ważne rozróżnienie

- Przepływ obrazu przez detektor i odczyt tekstu.
- Jawna możliwość przełączenia detektora.

Granice: metryki detekcji nie opisują dokładności OCR. Nie potwierdzam tutaj, który detektor jest aktualnie aktywny na serwerze.

[Otwórz demo  ↗](https://plates.banas.dev)[Kod i dokumentacja  ↗](https://github.com/Rafalbanas/automatic_plate_number_recognition)

A co budujemy dalej?

## Widzisz miejsce dla mnie w swoim zespole?

Podeślij rolę i kilka zdań o zespole. Porozmawiajmy o wsparciu IT, automatyzacji lub integracji AI.

[Porozmawiajmy na LinkedIn  ↗](https://linkedin.com/in/rafał-banaś-251583152) [Inne formy kontaktu  ↗](https://banas.dev/index.html#contact)

---
Źródło: https://banas.dev/projekty.html
