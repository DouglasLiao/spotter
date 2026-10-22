from datetime import UTC, datetime

from rest_framework import serializers


class RoutePlanRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Origin city name, address, or lat,lon coordinate pair (e.g. 'Chicago, IL')",
    )
    destination = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Destination city name, address, or lat,lon coordinate pair (e.g. 'Denver, CO')",
    )
    departure_time = serializers.DateTimeField(
        required=False,
        default=lambda: datetime.now(UTC),
        help_text="Departure date and time in ISO 8601 format (defaults to current UTC time)",
    )
    load_weight = serializers.FloatField(
        required=True,
        min_value=0.0,
        help_text="Truck load weight in pounds (lbs), e.g. 42000",
    )
    sample_interval_miles = serializers.FloatField(
        default=25.0,
        required=False,
        help_text="Checkpoint sampling interval along the route in miles (10, 25, or 50)",
    )

    def validate_sample_interval_miles(self, value):
        if value not in (10, 25, 50, 10.0, 25.0, 50.0):
            raise serializers.ValidationError(
                "Sample interval must be 10, 25, or 50 miles."
            )
        return float(value)

    def validate(self, data):
        origin = data.get("origin", "").strip()
        destination = data.get("destination", "").strip()

        if not origin:
            raise serializers.ValidationError(
                {"origin": "Origin location cannot be empty."}
            )
        if not destination:
            raise serializers.ValidationError(
                {"destination": "Destination location cannot be empty."}
            )
        if origin.lower() == destination.lower():
            raise serializers.ValidationError(
                {"destination": "Origin and destination must be different locations."}
            )

        data["origin"] = origin
        data["destination"] = destination
        return data
