from collections.abc import Mapping
import unicodedata

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

    if any(unicodedata.category(character).startswith("C") for character in normalized):
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


class TripPlanResponseSerializer(serializers.Serializer):
    start = serializers.CharField()
    finish = serializers.CharField()
    message = serializers.CharField()