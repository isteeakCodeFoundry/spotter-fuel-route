import unicodedata
from collections.abc import Mapping

from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            return super().to_internal_value(data)

        allowed_fields = set(self.fields)
        supplied_fields = set(data)
        unexpected_fields = supplied_fields - allowed_fields

        if unexpected_fields:
            raise serializers.ValidationError(
                {
                    field: ["Unexpected field."]
                    for field in sorted(unexpected_fields)
                }
            )

        return super().to_internal_value(data)


def normalize_location(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()

    if any(
            unicodedata.category(character).startswith("C")
            for character in normalized
    ):
        raise serializers.ValidationError(
            "Location must not contain control characters."
        )

    return " ".join(normalized.split())


class TripPlanRequestSerializer(StrictSerializer):
    start = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )
    finish = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )

    def validate_start(self, value: str) -> str:
        return normalize_location(value)

    def validate_finish(self, value: str) -> str:
        return normalize_location(value)


class LocationSerializer(serializers.Serializer):
    query = serializers.CharField()
    label = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()


class RouteSerializer(serializers.Serializer):
    distance_miles = serializers.FloatField()
    duration_seconds = serializers.FloatField()
    geometry = serializers.JSONField()


class VehicleSerializer(serializers.Serializer):
    maximum_range_miles = serializers.DecimalField(
        max_digits=8,
        decimal_places=3,
    )
    fuel_efficiency_mpg = serializers.DecimalField(
        max_digits=8,
        decimal_places=3,
    )
    tank_capacity_gallons = serializers.DecimalField(
        max_digits=8,
        decimal_places=3,
    )


class FuelStationResponseSerializer(serializers.Serializer):
    opis_id = serializers.IntegerField()
    name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    coordinate_quality = serializers.CharField()


class FuelStopSerializer(serializers.Serializer):
    route_mile = serializers.FloatField()
    distance_from_route_miles = serializers.FloatField()
    price_per_gallon = serializers.DecimalField(
        max_digits=10,
        decimal_places=8,
    )
    gallons_purchased = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
    )
    cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    station = FuelStationResponseSerializer()


class CompactFuelStopSerializer(serializers.Serializer):
    route_mile = serializers.FloatField()
    station = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()

    gallons_to_buy = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
    )
    price_per_gallon = serializers.DecimalField(
        max_digits=10,
        decimal_places=8,
    )
    cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )


class TripPlanSummaryResponseSerializer(serializers.Serializer):
    start = serializers.CharField()
    finish = serializers.CharField()
    route_distance_miles = serializers.FloatField()

    fuel_stops = CompactFuelStopSerializer(many=True)

    total_gallons_purchased = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    total_cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )


class FuelSummarySerializer(serializers.Serializer):
    trip_gallons_required = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    starting_fuel_gallons = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    gallons_purchased = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    total_cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    ending_fuel_gallons = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
    )


class TripMetadataSerializer(serializers.Serializer):
    candidate_station_count = serializers.IntegerField()
    normal_external_api_calls = serializers.IntegerField()


class TripPlanResponseSerializer(serializers.Serializer):
    start = LocationSerializer()
    finish = LocationSerializer()
    route = RouteSerializer()
    vehicle = VehicleSerializer()
    fuel_stops = FuelStopSerializer(many=True)
    fuel_summary = FuelSummarySerializer()
    metadata = TripMetadataSerializer()