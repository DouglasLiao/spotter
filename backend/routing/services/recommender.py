import logging

logger = logging.getLogger(__name__)


def recommend_best_route(routes: list[dict]) -> tuple[dict, list[dict]]:
    """
    Selects the best route based on the assessment's strict preference rules:
      1. Fewest Severe miles (including No Travel)
      2. Fewest High miles
      3. Lowest average risk
      4. Shortest travel times

    Marks the chosen route with `is_recommended: True` and attaches a clear explanation.
    Returns:
      (recommended_route, routes_list_with_recommendation_flags)
    """
    if not routes:
        raise ValueError("No routes provided for recommendation.")

    def _sort_key(route: dict):
        risk_summary = route.get("risk_summary", {})
        severe_miles = float(risk_summary.get("severe_miles", 0.0))
        high_miles = float(risk_summary.get("high_miles", 0.0))
        avg_risk = float(risk_summary.get("average_risk_score", 1.0))
        duration_sec = float(route.get("duration_seconds", 0.0))
        return (severe_miles, high_miles, avg_risk, duration_sec)

    # Sort routes based on the 4 tiered criteria
    sorted_routes = sorted(routes, key=_sort_key)
    best_route = sorted_routes[0]

    # Annotate routes with recommendation flags and explanations
    for route in routes:
        if route["id"] == best_route["id"]:
            route["is_recommended"] = True
            severe_m = route["risk_summary"]["severe_miles"]
            high_m = route["risk_summary"]["high_miles"]
            avg_score = route["risk_summary"]["average_risk_score"]
            dur_hrs = route["duration_hours"]

            reasons = []
            if severe_m == 0:
                reasons.append("Zero exposure to Severe weather")
            else:
                reasons.append(f"Lowest Severe exposure ({severe_m} mi)")

            reasons.append(f"{high_m} mi in High risk")
            reasons.append(f"average risk score of {avg_score}")
            reasons.append(f"travel time of {dur_hrs}h")

            route["recommendation_reason"] = (
                f"Recommended based on safest path: {', '.join(reasons)}."
            )
        else:
            route["is_recommended"] = False
            route["recommendation_reason"] = "Alternative route."

    logger.info(
        "Recommended route selected: %s (%s) - Severe: %.1f mi, High: %.1f mi, Avg: %.2f",
        best_route["id"],
        best_route["name"],
        best_route["risk_summary"]["severe_miles"],
        best_route["risk_summary"]["high_miles"],
        best_route["risk_summary"]["average_risk_score"],
    )

    return best_route, routes
