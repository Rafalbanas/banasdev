#!/usr/bin/env python3
"""Pobiera pogodę i jakość powietrza dla paczkomatu KAT04BAPP."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


API_URL = "https://inpost.pl/shipx-point-data/60742/KAT04BAPP/air_index_level"
REFERER = "https://inpost.pl/paczkomat-katowice-kat04bapp-brzozowa-paczkomaty-slaskie"
OUTPUT_PATH = Path(__file__).resolve().with_name("data.json")
DATABASE_PATH = Path(__file__).resolve().with_name("weather_history.db")
HISTORY_PATH = Path(__file__).resolve().with_name("history.json")
LOCAL_TIMEZONE = ZoneInfo("Europe/Warsaw")
SENSOR_UNITS = {
    "TEMPERATURE": "°C",
    "HUMIDITY": "%",
    "PRESSURE": "hPa",
    "PM25": "µg/m³",
    "PM10": "µg/m³",
}


def fetch_payload() -> dict[str, Any]:
    request = Request(
        API_URL,
        headers={
            "x-requested-with": "XMLHttpRequest",
            "referer": REFERER,
            "user-agent": "banas.dev weather widget/1.0",
            "accept": "application/json",
        },
    )
    with urlopen(request, timeout=20) as response:
        return json.load(response)


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


def build_output(payload: dict[str, Any]) -> dict[str, Any]:
    sensors = parse_sensors(payload)
    required = {"TEMPERATURE", "HUMIDITY", "PRESSURE", "PM25", "PM10"}
    missing = sorted(required - sensors.keys())
    if missing:
        raise ValueError(f"Brak wymaganych czujników w odpowiedzi API: {', '.join(missing)}")

    return {
        "location": "Katowice (Kato)",
        "station": "KAT04BAPP",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        ),
        "air_index_level": payload.get("air_index_level", "UNKNOWN"),
        "temperature": sensors["TEMPERATURE"],
        "humidity": sensors["HUMIDITY"],
        "pressure": sensors["PRESSURE"],
        "pm25": sensors["PM25"],
        "pm10": sensors["PM10"],
        "source": "InPost",
    }


def write_json_atomically(data: dict[str, Any], output_path: Path) -> None:
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=output_path.parent,
        prefix=f".{output_path.stem}-",
        suffix=".json",
        text=True,
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
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


def save_reading(output: dict[str, Any]) -> None:
    fetched_at = datetime.fromisoformat(output["fetched_at"].replace("Z", "+00:00"))
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)

    utc_timestamp = fetched_at.astimezone(timezone.utc)
    local_timestamp = utc_timestamp.astimezone(LOCAL_TIMEZONE)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS readings (
                timestamp TEXT PRIMARY KEY,
                timestamp_local TEXT NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                pressure REAL NOT NULL,
                pm25 REAL NOT NULL,
                pm10 REAL NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings(timestamp)"
        )
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
        connection.execute(
            "DELETE FROM readings WHERE timestamp < datetime('now', '-90 days')"
        )


def utc_timestamp_for_json(raw_timestamp: str) -> str:
    """Zwraca jednoznaczny znacznik ISO 8601 UTC dla pliku publicznego."""
    parsed = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def build_history() -> dict[str, Any]:
    hourly_readings: dict[tuple[str, str], dict[str, Any]] = {}
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT timestamp, timestamp_local, temperature, humidity, pressure, pm25, pm10
            FROM readings
            WHERE timestamp >= datetime('now', '-90 days')
            ORDER BY timestamp
            """
        ).fetchall()

    for row in rows:
        local_time = datetime.fromisoformat(row["timestamp_local"])
        date_key = local_time.date().isoformat()
        hour = local_time.strftime("%H:00")
        hourly_readings[(date_key, hour)] = {
            "hour": hour,
            "timestamp_utc": utc_timestamp_for_json(row["timestamp"]),
            "timestamp_local": row["timestamp_local"],
            "temperature": row["temperature"],
            "humidity": row["humidity"],
            "pressure": row["pressure"],
            "pm25": row["pm25"],
            "pm10": row["pm10"],
        }

    days: dict[str, list[dict[str, Any]]] = {}
    for (date_key, _), reading in sorted(hourly_readings.items()):
        days.setdefault(date_key, []).append(reading)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
        "timezone": str(LOCAL_TIMEZONE),
        "range_days": 90,
        "days": days,
    }


def main() -> None:
    output = build_output(fetch_payload())
    write_json_atomically(output, OUTPUT_PATH)
    save_reading(output)
    write_json_atomically(build_history(), HISTORY_PATH)
    print(f"Zapisano aktualne dane w {OUTPUT_PATH}")
    print(f"Zaktualizowano historię w {DATABASE_PATH} i {HISTORY_PATH}")


if __name__ == "__main__":
    main()
