import logging
from datetime import UTC, datetime

import requests
from django.conf import settings

from routing.constants import WEATHER_BATCH_CHUNK_SIZE

logger = logging.getLogger(__name__)


def _find_closest_time_index(time_list: list[str], target_dt: datetime) -> int:
    """Finds the index of the hourly forecast closest to the target datetime."""
    # Format target as ISO string matching Open-Meteo format: 'YYYY-MM-DDTHH:00'
    target_utc = target_dt.astimezone(UTC) if target_dt.tzinfo else target_dt
    target_str = target_utc.strftime("%Y-%m-%dT%H:00")

    # Fast direct match
    try:
        return time_list.index(target_str)
    except ValueError:
        pass

    # If not found directly, find the closest timestamp
    target_ts = target_utc.timestamp()
    best_idx = 0
    min_diff = float("inf")

    for idx, t_str in enumerate(time_list):
        try:
            dt = datetime.fromisoformat(t_str).replace(tzinfo=UTC)
            diff = abs(dt.timestamp() - target_ts)
            if diff < min_diff:
                min_diff = diff
                best_idx = idx
        except ValueError as e:
            logger.debug("Error parsing time string '%s': %s", t_str, e)
            continue

    return best_idx


def get_weather_for_checkpoints(checkpoints: list[dict]) -> list[dict]:
    """
    Fetches hourly weather forecast (wind speed, rain, snow) from Open-Meteo
    for each checkpoint at the truck's exact estimated arrival time (ETA).
    """
    if not checkpoints:
        return []

    base_url = settings.OPEN_METEO_BASE_URL
    user_agent = settings.USER_AGENT
    timeout = settings.EXTERNAL_API_TIMEOUT

    # Process in chunks to stay well within query string limits
    for start_idx in range(0, len(checkpoints), WEATHER_BATCH_CHUNK_SIZE):
        chunk = checkpoints[start_idx : start_idx + WEATHER_BATCH_CHUNK_SIZE]

        lats_str = ",".join(f"{cp['lat']:.4f}" for cp in chunk)
        lons_str = ",".join(f"{cp['lon']:.4f}" for cp in chunk)

        url = (
            f"{base_url}?"
            f"latitude={lats_str}&longitude={lons_str}"
            f"&hourly=wind_speed_10m,precipitation,snowfall"
            f"&wind_speed_unit=mph&precipitation_unit=inch"
            f"&forecast_days=16&timezone=UTC"
        )

        try:
            response = requests.get(
                url, headers={"User-Agent": user_agent}, timeout=timeout
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    data = [data]

                for i, item in enumerate(data):
                    cp = chunk[i]
                    hourly = item.get("hourly", {})
                    time_list = hourly.get("time", [])

                    if time_list:
                        time_idx = _find_closest_time_index(time_list, cp["eta"])

                        wind_speeds = hourly.get("wind_speed_10m", [])
                        precipitations = hourly.get("precipitation", [])
                        snowfalls = hourly.get("snowfall", [])

                        wind_mph = (
                            float(wind_speeds[time_idx])
                            if time_idx < len(wind_speeds)
                            and wind_speeds[time_idx] is not None
                            else 0.0
                        )
                        rain_in = (
                            float(precipitations[time_idx])
                            if time_idx < len(precipitations)
                            and precipitations[time_idx] is not None
                            else 0.0
                        )
                        snow_in = (
                            float(snowfalls[time_idx])
                            if time_idx < len(snowfalls)
                            and snowfalls[time_idx] is not None
                            else 0.0
                        )
                        forecast_time = time_list[time_idx]
                    else:
                        wind_mph, rain_in, snow_in, forecast_time = (
                            0.0,
                            0.0,
                            0.0,
                            cp["eta_iso"],
                        )

                    cp["weather"] = {
                        "wind_mph": round(wind_mph, 1),
                        "rain_in_hr": round(rain_in, 2),
                        "snow_in_hr": round(snow_in, 2),
                        "forecast_time": forecast_time,
                    }
                logger.debug(
                    "Fetched weather for checkpoints %d to %d",
                    start_idx,
                    min(start_idx + WEATHER_BATCH_CHUNK_SIZE, len(checkpoints)),
                )
            else:
                logger.warning(
                    "Open-Meteo API returned HTTP %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                for cp in chunk:
                    cp["weather"] = {
                        "wind_mph": 0.0,
                        "rain_in_hr": 0.0,
                        "snow_in_hr": 0.0,
                        "forecast_time": cp["eta_iso"],
                    }
        except Exception as e:
            logger.exception("Weather API error: %s", e)
            for cp in chunk:
                cp["weather"] = {
                    "wind_mph": 0.0,
                    "rain_in_hr": 0.0,
                    "snow_in_hr": 0.0,
                    "forecast_time": cp["eta_iso"],
                }

    logger.info(
        "Weather data successfully attached to %d checkpoints.", len(checkpoints)
    )
    return checkpoints
