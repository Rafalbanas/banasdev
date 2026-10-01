#!/usr/bin/env python3
"""Pobiera pogodę i jakość powietrza dla paczkomatu KAT04BAPP."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


API_URL = "https://inpost.pl/shipx-point-data/60742/KAT04BAPP/air_index_level"
REFERER = "https://inpost.pl/paczkomat-katowice-kat04bapp-brzozowa-paczkomaty-slaskie"
OUTPUT_PATH = Path(__file__).resolve().with_name("data.json")
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
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "air_index_level": payload.get("air_index_level", "UNKNOWN"),
        "temperature": sensors["TEMPERATURE"],
        "humidity": sensors["HUMIDITY"],
        "pressure": sensors["PRESSURE"],
        "pm25": sensors["PM25"],
        "pm10": sensors["PM10"],
        "source": "InPost",
    }


def write_atomically(data: dict[str, Any]) -> None:
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=OUTPUT_PATH.parent,
        prefix=".data-",
        suffix=".json",
        text=True,
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
            json.dump(data, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
        os.chmod(temporary_name, 0o644)
        os.replace(temporary_name, OUTPUT_PATH)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def main() -> None:
    output = build_output(fetch_payload())
    write_atomically(output)
    print(f"Zapisano dane pogodowe w {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
