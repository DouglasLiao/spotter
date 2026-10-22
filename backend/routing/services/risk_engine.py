import logging
from enum import IntEnum

logger = logging.getLogger(__name__)


class RiskLevel(IntEnum):
    LOW = 1
    MODERATE = 2
    HIGH = 3
    SEVERE = 4
    NO_TRAVEL = 5

    @property
    def label(self) -> str:
        labels = {
            RiskLevel.LOW: "Low",
            RiskLevel.MODERATE: "Moderate",
            RiskLevel.HIGH: "High",
            RiskLevel.SEVERE: "Severe",
            RiskLevel.NO_TRAVEL: "No Travel",
        }
        return labels[self]

    @classmethod
    def from_score(cls, score: float) -> "RiskLevel":
        """Maps a continuous score (1.0 to 5.0) to the nearest discrete RiskLevel."""
        if score < 1.5:
            return cls.LOW
        elif score < 2.5:
            return cls.MODERATE
        elif score < 3.5:
            return cls.HIGH
        elif score < 4.5:
            return cls.SEVERE
        return cls.NO_TRAVEL


def classify_wind(wind_mph: float) -> RiskLevel:
    """
    Wind risk classification:
      Low: <25 mph
      Moderate: 25–34 mph
      High: 35–44 mph
      Severe: 45–54 mph
      No Travel: >=55 mph
    """
    if wind_mph >= 55.0:
        return RiskLevel.NO_TRAVEL
    elif wind_mph >= 45.0:
        return RiskLevel.SEVERE
    elif wind_mph >= 35.0:
        return RiskLevel.HIGH
    elif wind_mph >= 25.0:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def classify_rain(rain_in_hr: float) -> RiskLevel:
    """
    Rain risk classification:
      Low: <0.10 in/hr
      Moderate: 0.10–0.25 in/hr
      High: 0.25–0.50 in/hr
      Severe: 0.50–1.00 in/hr
      No Travel: >1.00 in/hr
    """
    if rain_in_hr > 1.00:
        return RiskLevel.NO_TRAVEL
    elif rain_in_hr >= 0.50:
        return RiskLevel.SEVERE
    elif rain_in_hr >= 0.25:
        return RiskLevel.HIGH
    elif rain_in_hr >= 0.10:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def classify_snow(snow_in_hr: float) -> RiskLevel:
    """
    Snow risk classification:
      Low: <0.5 in/hr
      Moderate: 0.5–1.0 in/hr
      High: 1.0–2.0 in/hr
      Severe: 2.0–3.0 in/hr
      No Travel: >3.0 in/hr
    """
    if snow_in_hr > 3.0:
        return RiskLevel.NO_TRAVEL
    elif snow_in_hr >= 2.0:
        return RiskLevel.SEVERE
    elif snow_in_hr >= 1.0:
        return RiskLevel.HIGH
    elif snow_in_hr >= 0.5:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def apply_load_rules(
    wind_mph: float, load_weight_lbs: float
) -> tuple[RiskLevel, bool, str]:
    """
    Applies truck load weight rules for wind risk:
      - >=55 mph -> No Travel for any load
      - 45–54 mph + >30,000 lb -> No Travel
      - 35–44 mph + >40,000 lb -> Severe

    Returns:
      (adjusted_wind_risk, load_penalty_applied, reason_message)
    """
    base_wind_risk = classify_wind(wind_mph)
    penalty_applied = False
    reason = ""

    # Rule 1: >=55 mph -> No Travel for any load
    if wind_mph >= 55.0:
        return (
            RiskLevel.NO_TRAVEL,
            False,
            "Wind >= 55 mph: No Travel for any load weight.",
        )

    # Rule 2: 45–54 mph + >30,000 lb -> No Travel
    if 45.0 <= wind_mph <= 54.0 and load_weight_lbs > 30000.0:
        penalty_applied = True
        reason = f"High wind ({wind_mph:.1f} mph) with heavy load ({load_weight_lbs:,.0f} lb > 30,000 lb) escalated to No Travel."
        return RiskLevel.NO_TRAVEL, penalty_applied, reason

    # Rule 3: 35–44 mph + >40,000 lb -> Severe
    if 35.0 <= wind_mph <= 44.0 and load_weight_lbs > 40000.0:
        penalty_applied = True
        reason = f"Moderate/High wind ({wind_mph:.1f} mph) with heavy load ({load_weight_lbs:,.0f} lb > 40,000 lb) escalated to Severe."
        return RiskLevel.SEVERE, penalty_applied, reason

    return base_wind_risk, penalty_applied, reason


def evaluate_checkpoint_risk(weather: dict, load_weight_lbs: float) -> dict:
    """
    Evaluates weather risk for an individual checkpoint considering wind, rain, snow,
    and load weight constraints.
    """
    wind_mph = float(weather.get("wind_mph", 0.0))
    rain_in_hr = float(weather.get("rain_in_hr", 0.0))
    snow_in_hr = float(weather.get("snow_in_hr", 0.0))

    rain_risk = classify_rain(rain_in_hr)
    snow_risk = classify_snow(snow_in_hr)
    adjusted_wind_risk, load_penalty_applied, load_reason = apply_load_rules(
        wind_mph, load_weight_lbs
    )

    # Checkpoint risk is the maximum among wind (adjusted), rain, and snow
    overall_risk = max(adjusted_wind_risk, rain_risk, snow_risk)

    return {
        "overall_risk_level": overall_risk.value,
        "overall_risk_label": overall_risk.label,
        "wind_risk_level": adjusted_wind_risk.value,
        "wind_risk_label": adjusted_wind_risk.label,
        "rain_risk_level": rain_risk.value,
        "rain_risk_label": rain_risk.label,
        "snow_risk_level": snow_risk.value,
        "snow_risk_label": snow_risk.label,
        "load_penalty_applied": load_penalty_applied,
        "load_reason": load_reason,
    }


def calculate_route_risk_metrics(checkpoints: list[dict]) -> dict:
    """
    Aggregates risk metrics across all checkpoints along a route:
      - Miles in each risk category (Severe, High, Moderate, Low, No Travel)
      - Distance-weighted average risk score (1.0 to 5.0)
      - Peak risk level
    """
    if not checkpoints:
        return {
            "average_risk_score": 1.0,
            "average_risk_label": "Low",
            "max_risk_level": "Low",
            "severe_miles": 0.0,
            "high_miles": 0.0,
            "moderate_miles": 0.0,
            "low_miles": 0.0,
            "no_travel_miles": 0.0,
        }

    total_miles = sum(cp.get("segment_miles", 0.0) for cp in checkpoints)
    if total_miles <= 0:
        total_miles = 1.0

    severe_miles = 0.0
    no_travel_miles = 0.0
    high_miles = 0.0
    moderate_miles = 0.0
    low_miles = 0.0
    weighted_score_sum = 0.0
    max_risk = RiskLevel.LOW

    for cp in checkpoints:
        seg_miles = float(cp.get("segment_miles", 0.0))
        risk_val = cp.get("risk", {}).get("overall_risk_level", RiskLevel.LOW.value)
        risk_level = RiskLevel(risk_val)

        max_risk = max(max_risk, risk_level)

        weighted_score_sum += risk_level.value * seg_miles

        if risk_level == RiskLevel.NO_TRAVEL:
            no_travel_miles += seg_miles
            severe_miles += (
                seg_miles  # No Travel counts in the Severe miles tier for preference
            )
        elif risk_level == RiskLevel.SEVERE:
            severe_miles += seg_miles
        elif risk_level == RiskLevel.HIGH:
            high_miles += seg_miles
        elif risk_level == RiskLevel.MODERATE:
            moderate_miles += seg_miles
        else:
            low_miles += seg_miles

    avg_score = round(weighted_score_sum / total_miles, 2)
    avg_label = RiskLevel.from_score(avg_score).label

    return {
        "average_risk_score": avg_score,
        "average_risk_label": avg_label,
        "max_risk_level": max_risk.label,
        "severe_miles": round(severe_miles, 1),
        "high_miles": round(high_miles, 1),
        "moderate_miles": round(moderate_miles, 1),
        "low_miles": round(low_miles, 1),
        "no_travel_miles": round(no_travel_miles, 1),
    }
