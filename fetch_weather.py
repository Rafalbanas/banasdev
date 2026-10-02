#!/usr/bin/env python3
"""Zbiera odczyty InPost oraz pogodę modelową Open-Meteo dla Katowic."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


INPOST_API_URL = "https://inpost.pl/shipx-point-data/60742/KAT04BAPP/air_index_level"
INPOST_REFERER = "https://inpost.pl/paczkomat-katowice-kat04bapp-brzozowa-paczkomaty-slaskie"
OPEN_METEO_API_URL = "https://api.open-meteo.com/v1/forecast"
OUTPUT_PATH = Path(__file__).resolve().with_name("data.json")
DATABASE_PATH = Path(__file__).resolve().with_name("weather_history.db")
HISTORY_PATH = Path(__file__).resolve().with_name("history.json")
WEATHER_PATH = Path(__file__).resolve().with_name("weather.json")
LOCAL_TIMEZONE = ZoneInfo("Europe/Warsaw")
WEATHER_RETENTION_DAYS = 30
INPOST_RETENTION_DAYS = 90

LOCATIONS = (
    {
        "id": "kat04bapp",
        "station": "KAT04BAPP",
        "name": "Katowice · Brzozowa",
        "latitude": 50.26,
        "longitude": 19.02,
    },
)

SENSOR_UNITS = {
    "TEMPERATURE": "°C",
    "HUMIDITY": "%",
    "PRESSURE": "hPa",
    "PM25": "µg/m³",
    "PM10": "µg/m³",
}

CURRENT_VARIABLES = (
    "temperature_2m",
    "precipitation",
    "rain",
    "showers",
    "snowfall",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
)
MINUTELY_VARIABLES = (
    "temperature_2m",
    "precipitation",
    "rain",
    "snowfall",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
)
HOURLY_VARIABLES = ("precipitation_probability",)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def datetime_from_unix(value: int | float) -> datetime:
    return datetime.fromtimestamp(value, tz=timezone.utc)


def number_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def integer_or_none(value: Any) -> int | None:
    number = number_or_none(value)
    return int(number) if number is not None else None


def fetch_json(url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request_headers = {
        "user-agent": "banas.dev weather collector/2.0",
        "accept": "application/json",
    }
    if headers:
        request_headers.update(headers)
    request = Request(url, headers=request_headers)
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def fetch_inpost_payload() -> dict[str, Any]:
    return fetch_json(
        INPOST_API_URL,
        headers={"x-requested-with": "XMLHttpRequest", "referer": INPOST_REFERER},
    )


def open_meteo_url(location: dict[str, Any], *, past_days: int = 0) -> str:
    parameters: dict[str, Any] = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "current": ",".join(CURRENT_VARIABLES),
        "minutely_15": ",".join(MINUTELY_VARIABLES),
        "hourly": ",".join(HOURLY_VARIABLES),
        "forecast_days": 2,
        "timezone": "UTC",
        "timeformat": "unixtime",
    }
    if past_days:
        parameters["past_days"] = past_days
    return f"{OPEN_METEO_API_URL}?{urlencode(parameters)}"


def fetch_open_meteo(location: dict[str, Any], *, past_days: int = 0) -> dict[str, Any]:
    return fetch_json(open_meteo_url(location, past_days=past_days))


def parse_sensors(payload: dict[str, Any]) -> dict[str, dict[str, float | str | None]]:
    parsed: dict[str, dict[str, float | str | None]] = {}
    for raw_sensor in payload.get("air_sensors", []):
        parts = str(raw_sensor).split(":")
        if len(parts) < 2 or not parts[1]:
            continue
        name = parts[0].upper()
        if name not in SENSOR_UNITS:
            continue
        norm_percent = float(parts[2]) if len(parts) > 2 and parts[2] else None
        value = float(parts[1])
        sensor: dict[str, float | str | None] = {
            "value": round(value, 1),
            "unit": SENSOR_UNITS[name],
        }
        if name in {"PM25", "PM10"}:
            sensor["norm_percent"] = round(norm_percent, 1) if norm_percent is not None else None
            sensor["norm_value"] = (
                round(value * 100 / norm_percent, 1) if norm_percent not in (None, 0) else None
            )
        parsed[name] = sensor
    return parsed


def build_inpost_output(payload: dict[str, Any]) -> dict[str, Any]:
    sensors = parse_sensors(payload)
    required = {"TEMPERATURE", "HUMIDITY", "PRESSURE", "PM25", "PM10"}
    missing = sorted(required - sensors.keys())
    if missing:
        raise ValueError(f"Brak wymaganych czujników w odpowiedzi API: {', '.join(missing)}")
    return {
        "location": "Katowice (Kato)",
        "station": "KAT04BAPP",
        "fetched_at": utc_now().isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "air_index_level": payload.get("air_index_level", "UNKNOWN"),
        "temperature": sensors["TEMPERATURE"],
        "humidity": sensors["HUMIDITY"],
        "pressure": sensors["PRESSURE"],
        "pm25": sensors["PM25"],
        "pm10": sensors["PM10"],
        "source": "InPost",
    }


def write_json_atomically(data: dict[str, Any], output_path: Path) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output_path.parent,
        prefix=f".{output_path.stem}-",
        suffix=".json",
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
            json.dump(data, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
        os.chmod(temporary_name, 0o644)
        os.replace(temporary_name, output_path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS readings (
            timestamp TEXT PRIMARY KEY,
            timestamp_local TEXT NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            pressure REAL NOT NULL,
            pm25 REAL NOT NULL,
            pm10 REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings(timestamp);

        CREATE TABLE IF NOT EXISTS locations (
            id TEXT PRIMARY KEY,
            station TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS weather_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id TEXT NOT NULL REFERENCES locations(id),
            data_time_utc TEXT NOT NULL,
            interval_start_utc TEXT NOT NULL,
            interval_end_utc TEXT NOT NULL,
            fetched_at_utc TEXT NOT NULL,
            temperature REAL,
            precipitation REAL,
            rain REAL,
            showers REAL,
            snowfall REAL,
            weather_code INTEGER,
            wind_speed REAL,
            wind_direction REAL,
            source TEXT NOT NULL,
            source_kind TEXT NOT NULL CHECK(source_kind IN ('collected_model', 'backfill_model')),
            UNIQUE(location_id, data_time_utc, source_kind)
        );
        CREATE INDEX IF NOT EXISTS idx_weather_observations_location_time
            ON weather_observations(location_id, data_time_utc);
        CREATE INDEX IF NOT EXISTS idx_weather_observations_interval
            ON weather_observations(location_id, interval_start_utc, interval_end_utc);

        CREATE TABLE IF NOT EXISTS weather_forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id TEXT NOT NULL REFERENCES locations(id),
            forecast_time_utc TEXT NOT NULL,
            interval_start_utc TEXT NOT NULL,
            interval_end_utc TEXT NOT NULL,
            issued_at_utc TEXT NOT NULL,
            temperature REAL,
            precipitation REAL,
            rain REAL,
            snowfall REAL,
            weather_code INTEGER,
            wind_speed REAL,
            wind_direction REAL,
            precipitation_probability REAL,
            probability_interval_start_utc TEXT,
            probability_interval_end_utc TEXT,
            source TEXT NOT NULL,
            source_kind TEXT NOT NULL CHECK(source_kind = 'forecast_model'),
            UNIQUE(location_id, forecast_time_utc, issued_at_utc)
        );
        CREATE INDEX IF NOT EXISTS idx_weather_forecasts_location_issue
            ON weather_forecasts(location_id, issued_at_utc);

        CREATE TABLE IF NOT EXISTS collector_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    for location in LOCATIONS:
        connection.execute(
            """
            INSERT INTO locations (id, station, name, latitude, longitude)
            VALUES (:id, :station, :name, :latitude, :longitude)
            ON CONFLICT(id) DO UPDATE SET
                station = excluded.station,
                name = excluded.name,
                latitude = excluded.latitude,
                longitude = excluded.longitude
            """,
            location,
        )


def save_inpost_reading(connection: sqlite3.Connection, output: dict[str, Any]) -> None:
    fetched_at = datetime.fromisoformat(output["fetched_at"].replace("Z", "+00:00"))
    utc_timestamp = fetched_at.astimezone(timezone.utc)
    local_timestamp = utc_timestamp.astimezone(LOCAL_TIMEZONE)
    connection.execute(
        """
        INSERT INTO readings (
            timestamp, timestamp_local, temperature, humidity, pressure, pm25, pm10
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(timestamp) DO UPDATE SET
            timestamp_local = excluded.timestamp_local,
            temperature = excluded.temperature,
            humidity = excluded.humidity,
            pressure = excluded.pressure,
            pm25 = excluded.pm25,
            pm10 = excluded.pm10
        """,
        (
            utc_timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"),
            local_timestamp.isoformat(timespec="microseconds"),
            output["temperature"]["value"],
            output["humidity"]["value"],
            output["pressure"]["value"],
            output["pm25"]["value"],
            output["pm10"]["value"],
        ),
    )


def series_value(series: dict[str, list[Any]], key: str, index: int) -> Any:
    values = series.get(key)
    return values[index] if values and index < len(values) else None


def hourly_probability(payload: dict[str, Any]) -> dict[int, float | None]:
    hourly = payload.get("hourly") or {}
    result: dict[int, float | None] = {}
    for index, raw_time in enumerate(hourly.get("time") or []):
        result[int(raw_time)] = number_or_none(series_value(hourly, "precipitation_probability", index))
    return result


def save_current_weather(
    connection: sqlite3.Connection,
    location: dict[str, Any],
    payload: dict[str, Any],
    fetched_at: datetime,
) -> None:
    current = payload.get("current") or {}
    if not isinstance(current.get("time"), (int, float)):
        raise ValueError("Open-Meteo nie zwróciło czasu danych bieżących")
    data_time = datetime_from_unix(current["time"])
    interval_seconds = int(current.get("interval") or 900)
    interval_start = data_time - timedelta(seconds=interval_seconds)
    connection.execute(
        """
        INSERT OR IGNORE INTO weather_observations (
            location_id, data_time_utc, interval_start_utc, interval_end_utc,
            fetched_at_utc, temperature, precipitation, rain, showers, snowfall,
            weather_code, wind_speed, wind_direction, source, source_kind
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'collected_model')
        """,
        (
            location["id"],
            iso_utc(data_time),
            iso_utc(interval_start),
            iso_utc(data_time),
            iso_utc(fetched_at),
            number_or_none(current.get("temperature_2m")),
            number_or_none(current.get("precipitation")),
            number_or_none(current.get("rain")),
            number_or_none(current.get("showers")),
            number_or_none(current.get("snowfall")),
            integer_or_none(current.get("weather_code")),
            number_or_none(current.get("wind_speed_10m")),
            number_or_none(current.get("wind_direction_10m")),
            "Open-Meteo Forecast API",
        ),
    )


def save_backfill(
    connection: sqlite3.Connection,
    location: dict[str, Any],
    payload: dict[str, Any],
    fetched_at: datetime,
) -> int:
    minutely = payload.get("minutely_15") or {}
    current_time = int((payload.get("current") or {}).get("time") or utc_now().timestamp())
    cutoff = int((utc_now() - timedelta(days=WEATHER_RETENTION_DAYS)).timestamp())
    inserted = 0
    for index, raw_time in enumerate(minutely.get("time") or []):
        unix_time = int(raw_time)
        if unix_time < cutoff or unix_time >= current_time:
            continue
        data_time = datetime_from_unix(unix_time)
        interval_start = data_time - timedelta(minutes=15)
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO weather_observations (
                location_id, data_time_utc, interval_start_utc, interval_end_utc,
                fetched_at_utc, temperature, precipitation, rain, showers, snowfall,
                weather_code, wind_speed, wind_direction, source, source_kind
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'backfill_model')
            """,
            (
                location["id"],
                iso_utc(data_time),
                iso_utc(interval_start),
                iso_utc(data_time),
                iso_utc(fetched_at),
                number_or_none(series_value(minutely, "temperature_2m", index)),
                number_or_none(series_value(minutely, "precipitation", index)),
                number_or_none(series_value(minutely, "rain", index)),
                None,
                number_or_none(series_value(minutely, "snowfall", index)),
                integer_or_none(series_value(minutely, "weather_code", index)),
                number_or_none(series_value(minutely, "wind_speed_10m", index)),
                number_or_none(series_value(minutely, "wind_direction_10m", index)),
                "Open-Meteo Forecast API (past_days)",
            ),
        )
        inserted += cursor.rowcount
    connection.execute(
        "INSERT OR REPLACE INTO collector_meta (key, value) VALUES (?, ?)",
        (f"weather_backfill_{location['id']}", iso_utc(fetched_at)),
    )
    return inserted


def save_forecast(
    connection: sqlite3.Connection,
    location: dict[str, Any],
    payload: dict[str, Any],
    fetched_at: datetime,
) -> int:
    minutely = payload.get("minutely_15") or {}
    current_time = int((payload.get("current") or {}).get("time") or utc_now().timestamp())
    forecast_end = current_time + 2 * 60 * 60
    probabilities = hourly_probability(payload)
    inserted = 0
    for index, raw_time in enumerate(minutely.get("time") or []):
        unix_time = int(raw_time)
        if unix_time <= current_time or unix_time > forecast_end:
            continue
        forecast_time = datetime_from_unix(unix_time)
        interval_start = forecast_time - timedelta(minutes=15)
        probability_hour = unix_time - unix_time % 3600
        probability = probabilities.get(probability_hour)
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO weather_forecasts (
                location_id, forecast_time_utc, interval_start_utc, interval_end_utc,
                issued_at_utc, temperature, precipitation, rain, snowfall, weather_code,
                wind_speed, wind_direction, precipitation_probability,
                probability_interval_start_utc, probability_interval_end_utc,
                source, source_kind
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'forecast_model')
            """,
            (
                location["id"],
                iso_utc(forecast_time),
                iso_utc(interval_start),
                iso_utc(forecast_time),
                iso_utc(fetched_at),
                number_or_none(series_value(minutely, "temperature_2m", index)),
                number_or_none(series_value(minutely, "precipitation", index)),
                number_or_none(series_value(minutely, "rain", index)),
                number_or_none(series_value(minutely, "snowfall", index)),
                integer_or_none(series_value(minutely, "weather_code", index)),
                number_or_none(series_value(minutely, "wind_speed_10m", index)),
                number_or_none(series_value(minutely, "wind_direction_10m", index)),
                probability,
                iso_utc(datetime_from_unix(probability_hour)) if probability is not None else None,
                iso_utc(datetime_from_unix(probability_hour + 3600)) if probability is not None else None,
                "Open-Meteo Forecast API",
            ),
        )
        inserted += cursor.rowcount
    return inserted


def needs_backfill(connection: sqlite3.Connection, location_id: str) -> bool:
    row = connection.execute(
        "SELECT value FROM collector_meta WHERE key = ?",
        (f"weather_backfill_{location_id}",),
    ).fetchone()
    return row is None


def prune_database(connection: sqlite3.Connection) -> None:
    connection.execute(
        f"DELETE FROM readings WHERE timestamp < datetime('now', '-{INPOST_RETENTION_DAYS} days')"
    )
    connection.execute(
        f"DELETE FROM weather_observations WHERE datetime(data_time_utc) < datetime('now', '-{WEATHER_RETENTION_DAYS} days')"
    )
    connection.execute(
        f"DELETE FROM weather_forecasts WHERE datetime(issued_at_utc) < datetime('now', '-{WEATHER_RETENTION_DAYS} days')"
    )


def utc_timestamp_for_json(raw_timestamp: str) -> str:
    parsed = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def build_inpost_history(connection: sqlite3.Connection) -> dict[str, Any]:
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT timestamp, timestamp_local, temperature, humidity, pressure, pm25, pm10
        FROM readings
        WHERE timestamp >= datetime('now', '-90 days')
        ORDER BY timestamp
        """
    ).fetchall()
    hourly: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        local_time = datetime.fromisoformat(row["timestamp_local"])
        date_key = local_time.date().isoformat()
        hour = local_time.strftime("%H:00")
        hourly[(date_key, hour)] = {
            "hour": hour,
            "timestamp_utc": utc_timestamp_for_json(row["timestamp"]),
            "timestamp_local": row["timestamp_local"],
            "temperature": row["temperature"],
            "humidity": row["humidity"],
            "pressure": row["pressure"],
            "pm25": row["pm25"],
            "pm10": row["pm10"],
            "source": "InPost KAT04BAPP",
            "source_kind": "sensor_measurement",
        }
    days: dict[str, list[dict[str, Any]]] = {}
    for (date_key, _), reading in sorted(hourly.items()):
        days.setdefault(date_key, []).append(reading)
    return {
        "generated_at": iso_utc(utc_now()),
        "timezone": str(LOCAL_TIMEZONE),
        "range_days": INPOST_RETENTION_DAYS,
        "days": days,
    }


def row_to_weather(row: sqlite3.Row) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "data_time_utc",
            "interval_start_utc",
            "interval_end_utc",
            "fetched_at_utc",
            "temperature",
            "precipitation",
            "rain",
            "showers",
            "snowfall",
            "weather_code",
            "wind_speed",
            "wind_direction",
            "source",
            "source_kind",
        )
    }


def row_to_forecast(row: sqlite3.Row) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "forecast_time_utc",
            "interval_start_utc",
            "interval_end_utc",
            "issued_at_utc",
            "temperature",
            "precipitation",
            "rain",
            "snowfall",
            "weather_code",
            "wind_speed",
            "wind_direction",
            "precipitation_probability",
            "probability_interval_start_utc",
            "probability_interval_end_utc",
            "source",
            "source_kind",
        )
    }


def compact_weather_observation(observation: dict[str, Any]) -> dict[str, Any]:
    """Public history only needs chart fields; current conditions stay fully detailed."""
    return {
        key: observation[key]
        for key in (
            "interval_start_utc",
            "interval_end_utc",
            "temperature",
            "precipitation",
            "source_kind",
        )
    }


def build_weather_export(connection: sqlite3.Connection) -> dict[str, Any]:
    connection.row_factory = sqlite3.Row
    locations: dict[str, Any] = {}
    for location in LOCATIONS:
        rows = connection.execute(
            """
            SELECT * FROM weather_observations
            WHERE location_id = ?
              AND datetime(data_time_utc) >= datetime('now', '-30 days')
            ORDER BY data_time_utc,
                     CASE source_kind WHEN 'backfill_model' THEN 0 ELSE 1 END
            """,
            (location["id"],),
        ).fetchall()
        deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            deduplicated[(row["interval_start_utc"], row["interval_end_utc"])] = row_to_weather(row)
        observations = list(deduplicated.values())
        public_observations = [compact_weather_observation(item) for item in observations]

        latest_issue = connection.execute(
            "SELECT MAX(issued_at_utc) FROM weather_forecasts WHERE location_id = ?",
            (location["id"],),
        ).fetchone()[0]
        forecast_rows: Iterable[sqlite3.Row] = []
        if latest_issue:
            forecast_rows = connection.execute(
                """
                SELECT * FROM weather_forecasts
                WHERE location_id = ? AND issued_at_utc = ?
                ORDER BY forecast_time_utc
                """,
                (location["id"], latest_issue),
            ).fetchall()

        collected_start = connection.execute(
            """
            SELECT MIN(data_time_utc) FROM weather_observations
            WHERE location_id = ? AND source_kind = 'collected_model'
            """,
            (location["id"],),
        ).fetchone()[0]
        backfilled_start = connection.execute(
            """
            SELECT MIN(data_time_utc) FROM weather_observations
            WHERE location_id = ? AND source_kind = 'backfill_model'
            """,
            (location["id"],),
        ).fetchone()[0]

        locations[location["id"]] = {
            "station": location["station"],
            "name": location["name"],
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "timezone": str(LOCAL_TIMEZONE),
            "history_days": WEATHER_RETENTION_DAYS,
            "available_from": observations[0]["data_time_utc"] if observations else None,
            "collection_started_at": collected_start,
            "backfilled_from": backfilled_start,
            "current": observations[-1] if observations else None,
            "observations": public_observations,
            "forecast": {
                "issued_at_utc": latest_issue,
                "intervals": [row_to_forecast(row) for row in forecast_rows],
            },
        }
    return {
        "generated_at": iso_utc(utc_now()),
        "source": "Open-Meteo",
        "source_url": "https://open-meteo.com/",
        "locations": locations,
    }


def collect_inpost(connection: sqlite3.Connection) -> bool:
    try:
        output = build_inpost_output(fetch_inpost_payload())
        save_inpost_reading(connection, output)
        write_json_atomically(output, OUTPUT_PATH)
        print(f"Zapisano bieżące dane InPost w {OUTPUT_PATH}")
        return True
    except Exception as error:
        print(f"Błąd danych InPost: {error}", file=sys.stderr)
        return False


def collect_weather(connection: sqlite3.Connection) -> bool:
    success = True
    fetched_at = utc_now()
    grouped_locations: dict[tuple[float, float], list[dict[str, Any]]] = {}
    for location in LOCATIONS:
        grouped_locations.setdefault((location["latitude"], location["longitude"]), []).append(location)

    for locations in grouped_locations.values():
        request_location = locations[0]
        try:
            backfill = any(needs_backfill(connection, location["id"]) for location in locations)
            payload = fetch_open_meteo(
                request_location,
                past_days=WEATHER_RETENTION_DAYS if backfill else 0,
            )
            for location in locations:
                if needs_backfill(connection, location["id"]):
                    inserted = save_backfill(connection, location, payload, fetched_at)
                    print(f"Uzupełniono {inserted} historycznych przedziałów dla {location['station']}")
                save_current_weather(connection, location, payload, fetched_at)
                forecast_count = save_forecast(connection, location, payload, fetched_at)
                print(f"Zapisano pogodę i {forecast_count} przedziałów prognozy dla {location['station']}")
        except Exception as error:
            success = False
            stations = ", ".join(location["station"] for location in locations)
            print(f"Błąd Open-Meteo dla {stations}: {error}", file=sys.stderr)
    return success


def main() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as connection:
        initialize_database(connection)
        inpost_ok = collect_inpost(connection)
        weather_ok = collect_weather(connection)
        prune_database(connection)
        connection.commit()
        write_json_atomically(build_inpost_history(connection), HISTORY_PATH)
        write_json_atomically(build_weather_export(connection), WEATHER_PATH)

    print(f"Zaktualizowano bazę {DATABASE_PATH}")
    print(f"Zaktualizowano eksporty {HISTORY_PATH} i {WEATHER_PATH}")
    if not inpost_ok and not weather_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
