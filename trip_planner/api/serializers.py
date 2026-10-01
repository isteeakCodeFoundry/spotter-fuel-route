from rest_framework import serializers


class TripPlanRequestSerializer(serializers.Serializer):
    start = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )
    finish = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )

class TripPlanResponseSerializer(serializers.Serializer):
    start = serializers.CharField()
    finish = serializers.CharField()
    message = serializers.CharField()