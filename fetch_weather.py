#!/usr/bin/env python3
"""Pobiera godzinowe dane jakości powietrza GIOŚ dla Katowic."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

API_BASE = "https://api.gios.gov.pl/pjp-api/v1/rest"
OUTPUT_PATH = Path(__file__).resolve().with_name("data.json")
DATABASE_PATH = Path(__file__).resolve().with_name("weather_history.db")
HISTORY_PATH = Path(__file__).resolve().with_name("history.json")
LOCAL_TIMEZONE = ZoneInfo("Europe/Warsaw")
REFRESH_INTERVAL_SECONDS = 3600
STATIONS = (
    {"id": 814, "slug": "kossutha", "code": "SlKatoKossut", "name": "Katowice, ul. Kossutha"},
    {"id": 17318, "slug": "dudy-gracza", "code": "SlKatoDudyGr", "name": "Katowice, ul. Dudy-Gracza"},
)
PARAMETERS = {"PM2.5": "pm25", "PM10": "pm10"}
INDEX_LEVELS = {0: "VERY_GOOD", 1: "GOOD", 2: "MODERATE", 3: "SUFFICIENT", 4: "BAD", 5: "VERY_BAD"}


def round_one(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={
        "accept": "application/ld+json, application/json",
        "user-agent": "banas.dev air quality widget/2.0",
    })
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def parse_local_measurement_time(raw_timestamp: str) -> datetime:
    return datetime.strptime(raw_timestamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=LOCAL_TIMEZONE)


def station_sensor_ids(station_id: int) -> dict[str, list[int]]:
    payload = fetch_json(f"{API_BASE}/station/sensors/{station_id}")
    sensors = payload.get("Lista stanowisk pomiarowych dla podanej stacji", [])
    result = {parameter: [] for parameter in PARAMETERS}
    for sensor in sensors:
        parameter = sensor.get("Wskaźnik - kod")
        if parameter in result:
            result[parameter].append(int(sensor["Identyfikator stanowiska"]))
    missing = [parameter for parameter, ids in result.items() if not ids]
    if missing:
        raise ValueError(f"Stacja {station_id}: brak stanowisk dla {', '.join(missing)}")
    return result


def sensor_series(candidate_ids: list[int]) -> dict[str, float]:
    """Zwraca dane pierwszego automatycznego stanowiska z listy kandydatów."""
    for sensor_id in candidate_ids:
        payload = fetch_json(f"{API_BASE}/data/getData/{sensor_id}?page=0&size=100")
        raw_values = payload.get("Lista danych pomiarowych")
        if not isinstance(raw_values, list):
            continue
        values = {
            item["Data"]: float(item["Wartość"])
            for item in raw_values
            if item.get("Data") and item.get("Wartość") is not None
        }
        if values:
            return values
    raise ValueError("Brak bieżących danych z automatycznego stanowiska GIOŚ")


def station_index(station_id: int) -> tuple[int | None, str]:
    payload = fetch_json(f"{API_BASE}/aqindex/getIndex/{station_id}")
    index = payload.get("AqIndex", {}).get("Wartość indeksu")
    if index is None:
        return None, "UNKNOWN"
    numeric_index = int(index)
    return numeric_index, INDEX_LEVELS.get(numeric_index, "UNKNOWN")


def fetch_gios_data() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    series: dict[str, dict[str, dict[str, float]]] = {}
    station_indexes: dict[str, tuple[int | None, str]] = {}
    for station in STATIONS:
        sensor_ids = station_sensor_ids(station["id"])
        series[station["slug"]] = {
            field: sensor_series(sensor_ids[parameter])
            for parameter, field in PARAMETERS.items()
        }
        station_indexes[station["slug"]] = station_index(station["id"])

    all_series = [values for station_series in series.values() for values in station_series.values()]
    common_timestamps = set(all_series[0])
    for values in all_series[1:]:
        common_timestamps.intersection_update(values)
    if not common_timestamps:
        raise ValueError("Brak wspólnej godziny pomiaru dla obu stacji GIOŚ")

    readings: list[dict[str, Any]] = []
    for raw_timestamp in sorted(common_timestamps):
        local_time = parse_local_measurement_time(raw_timestamp)
        station_values = {
            station["slug"]: {
                field: round_one(series[station["slug"]][field][raw_timestamp])
                for field in PARAMETERS.values()
            }
            for station in STATIONS
        }
        readings.append({
            "timestamp": local_time.astimezone(timezone.utc),
            "timestamp_local": local_time,
            "pm25": round_one(sum(item["pm25"] for item in station_values.values()) / len(station_values)),
            "pm10": round_one(sum(item["pm10"] for item in station_values.values()) / len(station_values)),
            "stations": station_values,
        })

    latest = readings[-1]
    current_stations = []
    for station in STATIONS:
        _, level = station_indexes[station["slug"]]
        values = latest["stations"][station["slug"]]
        current_stations.append({
            **station,
            "air_index_level": level,
            "pm25": {"value": values["pm25"], "unit": "µg/m³"},
            "pm10": {"value": values["pm10"], "unit": "µg/m³"},
        })

    known_indexes = [index for index, _ in station_indexes.values() if index is not None]
    overall_level = INDEX_LEVELS.get(max(known_indexes), "UNKNOWN") if known_indexes else "UNKNOWN"
    output = {
        "location": "Katowice",
        "measured_at": latest["timestamp"].isoformat(timespec="seconds").replace("+00:00", "Z"),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "refresh_interval_seconds": REFRESH_INTERVAL_SECONDS,
        "air_index_level": overall_level,
        "pm25": {"value": latest["pm25"], "unit": "µg/m³"},
        "pm10": {"value": latest["pm10"], "unit": "µg/m³"},
        "stations": current_stations,
        "source": "Główny Inspektorat Ochrony Środowiska (GIOŚ)",
    }
    return output, readings


def write_json_atomically(data: dict[str, Any], output_path: Path) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output_path.parent, prefix=f".{output_path.stem}-", suffix=".json", text=True
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


def save_readings(readings: list[dict[str, Any]]) -> None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS air_readings (
                timestamp TEXT PRIMARY KEY,
                timestamp_local TEXT NOT NULL,
                pm25 REAL NOT NULL,
                pm10 REAL NOT NULL,
                kossutha_pm25 REAL NOT NULL,
                kossutha_pm10 REAL NOT NULL,
                dudy_gracza_pm25 REAL NOT NULL,
                dudy_gracza_pm10 REAL NOT NULL
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_air_readings_timestamp ON air_readings(timestamp)")
        for reading in readings:
            connection.execute("""
                INSERT INTO air_readings (
                    timestamp, timestamp_local, pm25, pm10,
                    kossutha_pm25, kossutha_pm10, dudy_gracza_pm25, dudy_gracza_pm10
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(timestamp) DO UPDATE SET
                    timestamp_local = excluded.timestamp_local,
                    pm25 = excluded.pm25,
                    pm10 = excluded.pm10,
                    kossutha_pm25 = excluded.kossutha_pm25,
                    kossutha_pm10 = excluded.kossutha_pm10,
                    dudy_gracza_pm25 = excluded.dudy_gracza_pm25,
                    dudy_gracza_pm10 = excluded.dudy_gracza_pm10
            """, (
                reading["timestamp"].isoformat(timespec="seconds"),
                reading["timestamp_local"].isoformat(timespec="seconds"),
                reading["pm25"], reading["pm10"],
                reading["stations"]["kossutha"]["pm25"],
                reading["stations"]["kossutha"]["pm10"],
                reading["stations"]["dudy-gracza"]["pm25"],
                reading["stations"]["dudy-gracza"]["pm10"],
            ))
        connection.execute("DELETE FROM air_readings WHERE timestamp < datetime('now', '-90 days')")


def build_history() -> dict[str, Any]:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("""
            SELECT timestamp, timestamp_local, pm25, pm10,
                   kossutha_pm25, kossutha_pm10, dudy_gracza_pm25, dudy_gracza_pm10
            FROM air_readings
            WHERE timestamp >= datetime('now', '-90 days')
            ORDER BY timestamp
        """).fetchall()

    days: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        local_time = datetime.fromisoformat(row["timestamp_local"])
        reading = {
            "hour": local_time.strftime("%H:00"),
            "timestamp_utc": datetime.fromisoformat(row["timestamp"]).astimezone(timezone.utc)
                .isoformat(timespec="seconds").replace("+00:00", "Z"),
            "timestamp_local": row["timestamp_local"],
            "pm25": row["pm25"],
            "pm10": row["pm10"],
            "kossutha_pm25": row["kossutha_pm25"],
            "kossutha_pm10": row["kossutha_pm10"],
            "dudy_gracza_pm25": row["dudy_gracza_pm25"],
            "dudy_gracza_pm10": row["dudy_gracza_pm10"],
        }
        days.setdefault(local_time.date().isoformat(), []).append(reading)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "timezone": str(LOCAL_TIMEZONE),
        "range_days": 90,
        "days": days,
    }


def main() -> None:
    output, readings = fetch_gios_data()
    write_json_atomically(output, OUTPUT_PATH)
    save_readings(readings)
    write_json_atomically(build_history(), HISTORY_PATH)
    print(f"Zapisano aktualne dane GIOŚ w {OUTPUT_PATH}")
    print(f"Zaktualizowano historię w {DATABASE_PATH} i {HISTORY_PATH}")


if __name__ == "__main__":
    main()
