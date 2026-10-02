from decimal import Decimal

from trip_planner.domain.entities import (
    Coordinates,
    PricedFuelStation,
    Route,
)
from trip_planner.domain.geometry import (
    find_route_fuel_stations,
    haversine_miles,
    sample_route,
)


def test_haversine_same_point_is_zero():
    point = Coordinates(
        latitude=41.0,
        longitude=-87.0,
    )

    assert haversine_miles(point, point) == 0


def test_sample_route_contains_start_and_finish():
    route = Route(
        distance_meters=160934.4,
        duration_seconds=3600,
        coordinates=(
            Coordinates(41.0, -87.0),
            Coordinates(41.5, -87.0),
            Coordinates(42.0, -87.0),
        ),
    )

    samples = sample_route(
        route,
        interval_miles=25,
    )

    assert samples[0].route_mile == 0
    assert samples[-1].route_mile == 100.0


def test_find_route_station_includes_nearby_station():
    route = Route(
        distance_meters=160934.4,
        duration_seconds=3600,
        coordinates=(
            Coordinates(41.0, -87.0),
            Coordinates(42.0, -87.0),
        ),
    )

    station = PricedFuelStation(
        id=1,
        opis_id=100,
        name="Test Fuel",
        address="1 Main St",
        city="Example",
        state="IL",
        coordinates=Coordinates(
            latitude=41.5,
            longitude=-87.05,
        ),
        price_per_gallon=Decimal("3.10"),
        geocode_quality="City_Centroid",
    )

    result = find_route_fuel_stations(
        route=route,
        stations=[station],
        corridor_miles=10,
        sample_interval_miles=5,
    )

    assert len(result) == 1
    assert result[0].station.opis_id == 100
    assert result[0].distance_from_route_miles < 10


def test_find_route_station_excludes_distant_station():
    route = Route(
        distance_meters=160934.4,
        duration_seconds=3600,
        coordinates=(
            Coordinates(41.0, -87.0),
            Coordinates(42.0, -87.0),
        ),
    )

    station = PricedFuelStation(
        id=1,
        opis_id=100,
        name="Far Away Fuel",
        address="1 Main St",
        city="Example",
        state="IL",
        coordinates=Coordinates(
            latitude=45.0,
            longitude=-100.0,
        ),
        price_per_gallon=Decimal("3.10"),
        geocode_quality="City_Centroid",
    )

    result = find_route_fuel_stations(
        route=route,
        stations=[station],
        corridor_miles=25,
    )

    assert result == []

def test_sample_route_interpolates_sparse_geometry():
    route = Route(
        distance_meters=160934.4,
        duration_seconds=3600,
        coordinates=(
            Coordinates(41.0, -87.0),
            Coordinates(42.0, -87.0),
        ),
    )

    samples = sample_route(
        route,
        interval_miles=10,
    )

    route_miles = [
        sample.route_mile
        for sample in samples
    ]

    assert route_miles == [
        0.0,
        10,
        20,
        30,
        40,
        50,
        60,
        70,
        80,
        90,
        100.0,
    ]