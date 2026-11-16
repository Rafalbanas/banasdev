# Publiczne dane banas.dev / Public data

Ten statyczny serwis udostępnia istniejące pliki JSON tylko do odczytu.
Nie jest to API kont, logowania, sterowania homelabem ani usług projektów.

This static site exposes existing read-only JSON files. It is not an account,
authentication, homelab-control or project-service API.

## Zasoby / Resources

- [OpenAPI 3.1](https://banas.dev/openapi.json)
- [Katalog RFC 9727](https://banas.dev/.well-known/api-catalog)
- `GET https://banas.dev/data.json` — aktualny eksport GIOŚ: PM2.5, PM10,
  indeks i stacje / latest collected air-quality export, index and stations.
- `GET https://banas.dev/history.json` — zebrana historia pyłów /
  collected particulate history.
- `GET https://banas.dev/weather.json` — model Open-Meteo, historia i prognoza /
  Open-Meteo model, history and forecast.

## Świeżość i ograniczenia / Freshness and limitations

HTTP 200 oznacza dostępność pliku, nie świeżość pomiaru. Sprawdzaj `measured_at`
i `fetched_at` w danych GIOŚ oraz `current.data_time_utc`, `fetched_at_utc`
i `forecast.issued_at_utc` w `locations.kat04bapp` eksportu pogody.
Wartości mogą być niepełne lub nieaktualne. Braki nie oznaczają zera.

HTTP 200 means the file is available, not that its readings are fresh.
Inspect the timestamps above. Missing values are not zero. Model weather
is not a direct local sensor observation. These exports are not a medical
or safety recommendation, a service health endpoint or a real-time SLA.

Źródła / Sources: [Open-Meteo](https://open-meteo.com/) and
[GIOŚ](https://powietrze.gios.gov.pl/). Attribution and upstream usage terms
continue to apply. No authentication is required for these three public files.
Please avoid aggressive polling; weather collection runs every 15 minutes,
and air-quality collection hourly.

## Negocjacja treści / Content negotiation

For `/`, `/index.html`, `/projekty.html` and `/hobby.html`, send
`Accept: text/markdown` to receive generated Polish Markdown instead of HTML.
Browsers receive HTML by default. Markdown omits interactive controls and
never embeds a live cycling verdict. Responses vary by Accept and are
marked `Cache-Control: no-store` to prevent cross-format cache contamination.
