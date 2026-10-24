import logging
import math

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from routing.serializers import RoutePlanRequestSerializer
from routing.services.corridor import build_corridor_grid
from routing.services.geocoding import geocode, search_cities
from routing.services.recommender import recommend_best_route
from routing.services.risk_engine import (
    calculate_route_risk_metrics,
    evaluate_checkpoint_risk,
)
from routing.services.route_provider import get_route_options
from routing.services.sampler import sample_route_checkpoints
from routing.services.weather_client import get_weather_for_checkpoints

logger = logging.getLogger(__name__)


class RoutePlanView(APIView):
    """
    POST /api/routes/plan/
    Plans and analyzes 3 weather-aware truck routes between origin and destination,
    samples checkpoints at requested interval, evaluates load-adjusted weather risk,
    and returns routes ranked with the safest option recommended.
    """

    def post(self, request, *args, **kwargs):
        serializer = RoutePlanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        origin_str = data["origin"]
        dest_str = data["destination"]
        departure_time = data["departure_time"]
        load_weight = float(data["load_weight"])
        sample_interval = float(data.get("sample_interval_miles", 25.0))

        logger.info(
            "New route planning request: '%s' -> '%s' (Load: %.0f lbs, Interval: %.0f mi, Dep: %s)",
            origin_str,
            dest_str,
            load_weight,
            sample_interval,
            departure_time.isoformat(),
        )

        # 1. Geocode origin and destination
        try:
            origin_geo = data.get("origin_location") or geocode(origin_str)
            dest_geo = data.get("destination_location") or geocode(dest_str)
        except ValueError as e:
            logger.warning("Geocoding failed: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Unexpected geocoding error: %s", e, exc_info=True)
            return Response(
                {
                    "error": "Failed to resolve route locations. Please check the provided addresses."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 2. Fetch 3 route options
        try:
            routes = get_route_options(origin_geo, dest_geo)
        except Exception as e:
            logger.error("Routing provider error: %s", e, exc_info=True)
            return Response(
                {
                    "error": "Failed to retrieve routes from routing engine. Please verify the locations and try again."
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Fetch all route checkpoints and the corridor in one deduplicated weather pass.
        try:
            for route in routes:
                route["checkpoints"] = sample_route_checkpoints(
                    route["coordinates"], route["distance_miles"],
                    route["duration_seconds"], departure_time,
                    interval_miles=sample_interval,
                )
            corridor = build_corridor_grid(routes, departure_time)
            points = [cp for route in routes for cp in route["checkpoints"]] + corridor["points"]
            get_weather_for_checkpoints(
                points, forecast_start=departure_time,
                forecast_hours=min(384, max(48, math.ceil(max(route["duration_seconds"] for route in routes) / 3600))),
            )
            for point in points:
                point["risk"] = evaluate_checkpoint_risk(point["weather"], load_weight)
                for forecast in point["hourly_forecast"]:
                    risk = evaluate_checkpoint_risk(forecast, load_weight)
                    forecast.update(
                        risk_level=risk["overall_risk_level"],
                        risk_label=risk["overall_risk_label"],
                        load_penalty_applied=risk["load_penalty_applied"],
                    )
            for route in routes:
                route["risk_summary"] = calculate_route_risk_metrics(route["checkpoints"])
                # The map uses corridor forecasts; checkpoints display ETA weather only.
                for checkpoint in route["checkpoints"]:
                    checkpoint.pop("hourly_forecast", None)
            best_route, processed_routes = recommend_best_route(routes)
            # Corridor needs only the time series, not duplicated ETA weather/risk.
            corridor["points"] = [
                {key: point[key] for key in ("lat", "lon", "hourly_forecast")}
                for point in corridor["points"]
            ]

        except Exception as e:
            logger.error("Error during risk analysis: %s", e, exc_info=True)
            return Response(
                {
                    "error": "An internal error occurred during weather and risk evaluation."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        warnings = []
        if len(routes) < 3:
            warnings.append(f"Only {len(routes)} distinct route option(s) are available from the routing provider.")
        if any(not route["risk_summary"]["weather_complete"] for route in routes):
            warnings.append("Some checkpoint weather is unavailable. Routes with incomplete weather are excluded from recommendations.")
        if best_route is None:
            warnings.append("No recommendation is available because checkpoint weather is incomplete for every route.")
        elif best_route["risk_summary"]["no_travel_miles"] > 0:
            warnings.append("The best available route still contains No Travel conditions. The recommendation is a comparison, not travel clearance.")

        response_payload = {
            "origin": origin_geo,
            "destination": dest_geo,
            "departure_time": departure_time.isoformat(),
            "load_weight": load_weight,
            "sample_interval_miles": sample_interval,
            "recommended_route_id": best_route["id"] if best_route else None,
            "warnings": warnings,
            "corridor": corridor,
            "routes": processed_routes,
        }

        return Response(response_payload, status=status.HTTP_200_OK)


class CitySearchView(APIView):
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 3:
            return Response({"results": []})
        if len(query) > 255:
            return Response({"error": "Search must be at most 255 characters."}, status=400)
        try:
            return Response({"results": search_cities(query)})
        except Exception:
            logger.warning("City search provider unavailable", exc_info=True)
            return Response({"error": "City suggestions are unavailable. You can still enter a city, address, or coordinates."}, status=503)
