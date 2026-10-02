from decimal import Decimal

from trip_planner.domain.entities import (
    Coordinates,
    GeocodedLocation,
    PricedFuelStation,
    Route,
)
from trip_planner.services.trip_planner import (
    TripPlannerService,
)


class FakeGeocoder:
    def geocode(self, query):
        locations = {
            "Start": GeocodedLocation(
                query="Start",
                label="Start, USA",
                coordinates=Coordinates(
                    latitude=40.0,
                    longitude=-90.0,
                ),
            ),
            "Finish": GeocodedLocation(
                query="Finish",
                label="Finish, USA",
                coordinates=Coordinates(
                    latitude=35.0,
                    longitude=-90.0,
                ),
            ),
        }

        return locations[query]


class FakeRouter:
    def get_route(self, *, start, finish):
        return Route(
            distance_meters=965606.4,  # 600 miles
            duration_seconds=36000,
            coordinates=(
                start,
                Coordinates(
                    latitude=37.5,
                    longitude=-90.0,
                ),
                finish,
            ),
        )


class FakeFuelStationRepository:
    def find_geocoded_with_prices(self):
        return [
            PricedFuelStation(
                id=1,
                opis_id=100,
                name="Test Fuel",
                address="1 Main St",
                city="Test",
                state="MO",
                coordinates=Coordinates(
                    latitude=36.25,
                    longitude=-90.0,
                ),
                price_per_gallon=Decimal("3.00"),
                geocode_quality="City_Centroid",
            )
        ]


def test_trip_planner_builds_complete_plan():
    service = TripPlannerService(
        geocoder=FakeGeocoder(),
        router=FakeRouter(),
        fuel_station_repository=(
            FakeFuelStationRepository()
        ),
    )

    result = service.plan(
        start_query="Start",
        finish_query="Finish",
    )

    assert result.start.label == "Start, USA"
    assert result.finish.label == "Finish, USA"
    assert result.route.distance_miles == 600
    assert result.candidate_station_count >= 1
    assert result.fuel_plan.trip_gallons_required == Decimal(
        "60.000"
    )