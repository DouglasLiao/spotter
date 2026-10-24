"""Hourly forecasts with explicit missing-data states and departure-relative windows."""

import logging
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import requests
from django.conf import settings

from routing.constants import WEATHER_BATCH_CHUNK_SIZE

logger = logging.getLogger(__name__)
FIELDS = {
    "wind_mph": ("wind_speed_10m",),
    "rain_in_hr": ("rain", "showers"),
    "snow_in_hr": ("snowfall",),
}


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _missing(target: datetime, reason: str) -> dict:
    return dict.fromkeys(FIELDS, None) | {
        "available": False,
        "forecast_time": None,
        "requested_time": as_utc(target).isoformat(),
        "unavailable_reason": reason,
    }


def _weather_at(item: dict | None, target: datetime) -> dict:
    if item is None:
        return _missing(target, "Weather provider unavailable or incomplete response.")
    hourly = item.get("hourly", {})
    times = hourly.get("time", [])
    if not isinstance(times, list):
        return _missing(target, "Weather provider returned invalid timestamps.")
    if "_hour_index" not in item:
        item["_hour_index"] = {}
        for index, value in enumerate(times):
            try:
                item["_hour_index"][as_utc(datetime.fromisoformat(value))] = index
            except (ValueError, TypeError):
                continue
    target_hour = as_utc(target).replace(minute=0, second=0, microsecond=0)
    index = item["_hour_index"].get(target_hour)
    if index is None:
        return _missing(target, "Requested hour is outside the available forecast.")
    values = {}
    for field, sources in FIELDS.items():
        values[field] = 0.0
        for source in sources:
            series = hourly.get(source, [])
            if not isinstance(series, list):
                return _missing(target, "Weather provider returned invalid measurements.")
            value = series[index] if index < len(series) else None
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                or value < 0
            ):
                return _missing(target, "Weather provider returned missing or invalid measurements.")
            # Rain includes large-scale rain and convective showers, excluding snow.
            # Keep precision for risk thresholds. Round only when displaying values.
            values[field] += float(value)
    return values | {
        "available": True,
        "forecast_time": as_utc(datetime.fromisoformat(times[index])).isoformat(),
        "requested_time": as_utc(target).isoformat(),
        "unavailable_reason": None,
    }


def _fetch_chunk(chunk: list[tuple[float, float]]) -> list[dict | None]:
    try:
        response = requests.get(
            settings.OPEN_METEO_BASE_URL,
            params={
                "latitude": ",".join(str(lat) for lat, _ in chunk),
                "longitude": ",".join(str(lon) for _, lon in chunk),
                "hourly": ",".join(
                    source for sources in FIELDS.values() for source in sources
                ),
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "forecast_days": 16,
                "timezone": "UTC",
            },
            headers={"User-Agent": settings.USER_AGENT},
            timeout=settings.EXTERNAL_API_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            data = [data]
        # A shortened list cannot safely be associated with the requested locations.
        if not isinstance(data, list) or len(data) != len(chunk):
            raise ValueError("Incomplete weather location response")
        return [
            item if isinstance(item, dict) and isinstance(item.get("hourly"), dict) else None
            for item in data
        ]
    except (requests.RequestException, ValueError, TypeError):
        logger.warning("Weather batch unavailable (%d locations)", len(chunk), exc_info=True)
        return [None] * len(chunk)


def get_weather_for_checkpoints(
    checkpoints: list[dict], forecast_start: datetime | None = None, forecast_hours: int = 48
) -> list[dict]:
    """Fetch each coordinate once; use ETA for risk and a bounded departure-relative window for the map."""
    if not checkpoints:
        return []
    forecast_start = as_utc(forecast_start or checkpoints[0]["eta"])
    coordinates = list(dict.fromkeys(
        (round(cp["lat"], 4), round(cp["lon"], 4)) for cp in checkpoints
    ))
    chunks = [
        coordinates[i:i + WEATHER_BATCH_CHUNK_SIZE]
        for i in range(0, len(coordinates), WEATHER_BATCH_CHUNK_SIZE)
    ]
    with ThreadPoolExecutor(max_workers=min(4, len(chunks))) as executor:
        items = [item for batch in executor.map(_fetch_chunk, chunks) for item in batch]
    by_coordinate = dict(zip(coordinates, items))
    for cp in checkpoints:
        item = by_coordinate[(round(cp["lat"], 4), round(cp["lon"], 4))]
        cp["weather"] = _weather_at(item, cp["eta"])
        cp["hourly_forecast"] = [
            {"hour": hour, "time": (forecast_start + timedelta(hours=hour)).isoformat(),
             **_weather_at(item, forecast_start + timedelta(hours=hour))}
            for hour in range(min(384, max(48, forecast_hours)) + 1)
        ]
    return checkpoints
