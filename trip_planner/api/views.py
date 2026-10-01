from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from trip_planner.api.serializers import (
    TripPlanRequestSerializer,
    TripPlanResponseSerializer,
)


class TripPlanView(APIView):
    @extend_schema(
        summary="Plan a fuel-optimized trip",
        description=(
                "Plans a route between two locations within the United States "
                "and determines cost-effective fuel stops along the route."
        ),
        request=TripPlanRequestSerializer,
        responses={200: TripPlanResponseSerializer},
        tags=["Trips"],
    )
    def post(self, request):
        serializer = TripPlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        return Response(
            {
                "start": validated_data["start"],
                "finish": validated_data["finish"],
                "message": "Trip planning endpoint is ready.",
            }
        )