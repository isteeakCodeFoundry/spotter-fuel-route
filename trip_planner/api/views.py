from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from trip_planner.api.responses import (
    build_trip_plan_response,
    build_trip_plan_summary_response,
)
from trip_planner.api.serializers import (
    TripPlanRequestSerializer,
    TripPlanResponseSerializer,
    TripPlanSummaryResponseSerializer,
)
from trip_planner.domain.fuel_optimizer import NoFeasibleFuelPlanError
from trip_planner.integrations.geocoding import (
    GeocodingError,
    HeiGitGeocoder,
)
from trip_planner.integrations.routing import (
    HeiGitRoutingClient,
    RouteNotFoundError,
    RoutingProviderError,
)
from trip_planner.repositories.fuel_stations import FuelStationRepository
from trip_planner.services.trip_planner import (
    TripLocationNotFoundError,
    TripPlannerService,
)


class TripPlanView(APIView):
    @extend_schema(
        summary="Plan a fuel-optimized trip",
        description=(
                "Plans a driving route between two locations within "
                "the United States and returns cost-effective fuel "
                "stops for a vehicle with a 500-mile maximum range "
                "and fuel efficiency of 10 MPG."
        ),
        request=TripPlanRequestSerializer,
        responses={
            200: TripPlanResponseSerializer,
        },
        tags=["Trips"],
    )
    def post(self, request):
        serializer = TripPlanRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        if not settings.HEIGIT_API_KEY:
            return Response(
                {
                    "error": {
                        "code": "PROVIDER_NOT_CONFIGURED",
                        "message": (
                            "HEIGIT_API_KEY is not configured."
                        ),
                    }
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        validated = serializer.validated_data

        try:
            with HeiGitGeocoder(
                    api_key=settings.HEIGIT_API_KEY
            ) as geocoder, HeiGitRoutingClient(
                api_key=settings.HEIGIT_API_KEY
            ) as router:
                service = TripPlannerService(
                    geocoder=geocoder,
                    router=router,
                    fuel_station_repository=FuelStationRepository(),
                )

                plan = service.plan(
                    start_query=validated["start"],
                    finish_query=validated["finish"],
                )

        except TripLocationNotFoundError as exc:
            return Response(
                {
                    "error": {
                        "code": "LOCATION_NOT_FOUND",
                        "field": exc.field,
                        "message": str(exc),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except ValueError as exc:
            return Response(
                {
                    "error": {
                        "code": "INVALID_TRIP",
                        "message": str(exc),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except (
                RouteNotFoundError,
                NoFeasibleFuelPlanError,
        ) as exc:
            return Response(
                {
                    "error": {
                        "code": "NO_FEASIBLE_TRIP",
                        "message": str(exc),
                    }
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        except (
                GeocodingError,
                RoutingProviderError,
        ):
            return Response(
                {
                    "error": {
                        "code": "MAP_PROVIDER_UNAVAILABLE",
                        "message": (
                            "The external mapping provider "
                            "is temporarily unavailable."
                        ),
                    }
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response_serializer = TripPlanResponseSerializer(
            data=build_trip_plan_response(plan)
        )
        response_serializer.is_valid(
            raise_exception=True
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )


class TripPlanSummaryView(APIView):
    @extend_schema(
        summary="Plan a fuel-optimized trip with compact output",
        description=(
                "Plans the same fuel-optimized trip as the full endpoint, "
                "but returns a compact response without route geometry. "
                "Useful for quickly reviewing fuel stops and total cost."
        ),
        request=TripPlanRequestSerializer,
        responses={
            200: TripPlanSummaryResponseSerializer,
        },
        tags=["Trips"],
    )
    def post(self, request):
        serializer = TripPlanRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        if not settings.HEIGIT_API_KEY:
            return Response(
                {
                    "error": {
                        "code": "PROVIDER_NOT_CONFIGURED",
                        "message": (
                            "HEIGIT_API_KEY is not configured."
                        ),
                    }
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        validated = serializer.validated_data

        try:
            with HeiGitGeocoder(
                    api_key=settings.HEIGIT_API_KEY
            ) as geocoder, HeiGitRoutingClient(
                api_key=settings.HEIGIT_API_KEY
            ) as router:
                service = TripPlannerService(
                    geocoder=geocoder,
                    router=router,
                    fuel_station_repository=FuelStationRepository(),
                )

                plan = service.plan(
                    start_query=validated["start"],
                    finish_query=validated["finish"],
                )

        except TripLocationNotFoundError as exc:
            return Response(
                {
                    "error": {
                        "code": "LOCATION_NOT_FOUND",
                        "field": exc.field,
                        "message": str(exc),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except ValueError as exc:
            return Response(
                {
                    "error": {
                        "code": "INVALID_TRIP",
                        "message": str(exc),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except (
                RouteNotFoundError,
                NoFeasibleFuelPlanError,
        ) as exc:
            return Response(
                {
                    "error": {
                        "code": "NO_FEASIBLE_TRIP",
                        "message": str(exc),
                    }
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        except (
                GeocodingError,
                RoutingProviderError,
        ):
            return Response(
                {
                    "error": {
                        "code": "MAP_PROVIDER_UNAVAILABLE",
                        "message": (
                            "The external mapping provider "
                            "is temporarily unavailable."
                        ),
                    }
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response_serializer = TripPlanSummaryResponseSerializer(
            data=build_trip_plan_summary_response(plan)
        )
        response_serializer.is_valid(
            raise_exception=True
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )