import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from routing.serializers import RoutePlanRequestSerializer
from routing.services.geocoding import geocode
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
            origin_geo = geocode(origin_str)
            dest_geo = geocode(dest_str)
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

        # 3. Process each route: sample checkpoints, fetch weather, evaluate risk
        try:
            for route in routes:
                checkpoints = sample_route_checkpoints(
                    route["coordinates"],
                    route["distance_miles"],
                    route["duration_seconds"],
                    departure_time,
                    interval_miles=sample_interval,
                )

                # Fetch real-time hourly forecast matching the ETA of each checkpoint
                enriched_checkpoints = get_weather_for_checkpoints(checkpoints)

                # Evaluate risk at each checkpoint considering truck load weight
                for cp in enriched_checkpoints:
                    cp["risk"] = evaluate_checkpoint_risk(cp["weather"], load_weight)

                # Compute aggregated route-level risk summary
                route["risk_summary"] = calculate_route_risk_metrics(
                    enriched_checkpoints
                )
                route["checkpoints"] = enriched_checkpoints

            # 4. Recommend the safest route using strict 4-tier preference logic
            best_route, processed_routes = recommend_best_route(routes)

        except Exception as e:
            logger.error("Error during risk analysis: %s", e, exc_info=True)
            return Response(
                {
                    "error": "An internal error occurred during weather and risk evaluation."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_payload = {
            "origin": origin_geo,
            "destination": dest_geo,
            "departure_time": departure_time.isoformat(),
            "load_weight": load_weight,
            "sample_interval_miles": sample_interval,
            "recommended_route_id": best_route["id"],
            "routes": processed_routes,
        }

        return Response(response_payload, status=status.HTTP_200_OK)
