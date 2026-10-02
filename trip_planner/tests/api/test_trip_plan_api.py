from decimal import Decimal
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from trip_planner.domain.entities import (
    Coordinates,
    FuelPlan,
    FuelPurchase,
    GeocodedLocation,
    PricedFuelStation,
    Route,
    RouteFuelStation,
    TripPlan,
)
from trip_planner.services.trip_planner import (
    TripLocationNotFoundError,
)


def make_trip_plan() -> TripPlan:
    station = PricedFuelStation(
        id=1,
        opis_id=123,
        name="Test Fuel",
        address="1 Main St",
        city="Test City",
        state="MO",
        coordinates=Coordinates(
            latitude=38.0,
            longitude=-90.0,
        ),
        price_per_gallon=Decimal("3.00000000"),
        geocode_quality="City_Centroid",
    )

    route_station = RouteFuelStation(
        station=station,
        route_mile=450.0,
        distance_from_route_miles=1.5,
    )

    purchase = FuelPurchase(
        station=route_station,
        gallons_purchased=Decimal("10.000"),
        cost=Decimal("30.00"),
    )

    return TripPlan(
        start=GeocodedLocation(
            query="Chicago, IL",
            label="Chicago, IL, USA",
            coordinates=Coordinates(
                latitude=41.87897,
                longitude=-87.66063,
            ),
        ),
        finish=GeocodedLocation(
            query="Dallas, TX",
            label="Dallas, TX, USA",
            coordinates=Coordinates(
                latitude=32.736212,
                longitude=-96.784359,
            ),
        ),
        route=Route(
            distance_meters=965606.4,  # 600 miles
            duration_seconds=36000,
            coordinates=(
                Coordinates(
                    latitude=41.87897,
                    longitude=-87.66063,
                ),
                Coordinates(
                    latitude=32.736212,
                    longitude=-96.784359,
                ),
            ),
        ),
        fuel_plan=FuelPlan(
            stops=(purchase,),
            trip_gallons_required=Decimal("60.000"),
            starting_fuel_gallons=Decimal("50.000"),
            total_gallons_purchased=Decimal("10.000"),
            total_cost=Decimal("30.00"),
            ending_fuel_gallons=Decimal("0.000"),
        ),
        candidate_station_count=12,
    )


@override_settings(HEIGIT_API_KEY="test-key")
@patch(
    "trip_planner.api.views.TripPlannerService.plan",
    return_value=make_trip_plan(),
)
def test_plan_trip_accepts_valid_locations(mock_plan):
    client = APIClient()

    response = client.post(
        reverse("trip-plan"),
        {
            "start": "Chicago, IL",
            "finish": "Dallas, TX",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.data["start"]["label"] == "Chicago, IL, USA"
    assert response.data["finish"]["label"] == "Dallas, TX, USA"

    assert response.data["route"]["distance_miles"] == 600.0
    assert response.data["fuel_summary"]["total_cost"] == "30.00"

    assert len(response.data["fuel_stops"]) == 1

    mock_plan.assert_called_once_with(
        start_query="Chicago, IL",
        finish_query="Dallas, TX",
    )


def test_plan_trip_rejects_blank_start():
    client = APIClient()

    response = client.post(
        reverse("trip-plan"),
        {
            "start": "",
            "finish": "Dallas, TX",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "start" in response.data


def test_plan_trip_rejects_missing_finish():
    client = APIClient()

    response = client.post(
        reverse("trip-plan"),
        {
            "start": "Chicago, IL",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "finish" in response.data


def test_plan_trip_rejects_unexpected_fields():
    client = APIClient()

    response = client.post(
        reverse("trip-plan"),
        {
            "start": "Chicago, IL",
            "finish": "Dallas, TX",
            "admin": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_plan_trip_rejects_control_characters():
    client = APIClient()

    response = client.post(
        reverse("trip-plan"),
        {
            "start": "Chicago,\x00IL",
            "finish": "Dallas, TX",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_plan_trip_rejects_oversized_location():
    client = APIClient()

    response = client.post(
        reverse("trip-plan"),
        {
            "start": "A" * 256,
            "finish": "Dallas, TX",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@override_settings(HEIGIT_API_KEY="test-key")
@patch(
    "trip_planner.api.views.TripPlannerService.plan"
)
def test_plan_trip_does_not_interpret_sql_like_input(
        mock_plan,
):
    mock_plan.side_effect = TripLocationNotFoundError(
        "start",
        "' OR 1=1 --",
    )

    client = APIClient()

    response = client.post(
        reverse("trip-plan"),
        {
            "start": "' OR 1=1 --",
            "finish": "Dallas, TX",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["error"]["code"] == "LOCATION_NOT_FOUND"
    assert response.data["error"]["field"] == "start"

    mock_plan.assert_called_once_with(
        start_query="' OR 1=1 --",
        finish_query="Dallas, TX",
    )