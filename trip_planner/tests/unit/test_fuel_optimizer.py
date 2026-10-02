from decimal import Decimal

import pytest

from trip_planner.domain.entities import (
    Coordinates,
    PricedFuelStation,
    RouteFuelStation,
)
from trip_planner.domain.fuel_optimizer import (
    NoFeasibleFuelPlanError,
    optimize_fuel_stops,
)


def make_station(
        *,
        opis_id: int,
        route_mile: float,
        price: str,
        detour: float = 1.0,
) -> RouteFuelStation:
    return RouteFuelStation(
        station=PricedFuelStation(
            id=opis_id,
            opis_id=opis_id,
            name=f"Station {opis_id}",
            address="1 Main St",
            city="Test City",
            state="TX",
            coordinates=Coordinates(
                latitude=32.0,
                longitude=-96.0,
            ),
            price_per_gallon=Decimal(price),
            geocode_quality="City_Centroid",
        ),
        route_mile=route_mile,
        distance_from_route_miles=detour,
    )


def test_route_under_500_miles_needs_no_purchase():
    plan = optimize_fuel_stops(
        route_distance_miles=400,
        stations=[],
    )

    assert plan.stops == ()
    assert plan.trip_gallons_required == Decimal("40.000")
    assert plan.total_gallons_purchased == Decimal("0.000")
    assert plan.total_cost == Decimal("0.00")
    assert plan.ending_fuel_gallons == Decimal("10.000")


def test_purchase_only_required_fuel_to_finish():
    plan = optimize_fuel_stops(
        route_distance_miles=600,
        stations=[
            make_station(
                opis_id=1,
                route_mile=450,
                price="3.00",
            )
        ],
    )

    assert len(plan.stops) == 1
    assert plan.stops[0].gallons_purchased == Decimal("10.000")
    assert plan.stops[0].cost == Decimal("30.00")
    assert plan.ending_fuel_gallons == Decimal("0.000")


def test_optimizer_waits_for_cheaper_station():
    plan = optimize_fuel_stops(
        route_distance_miles=900,
        stations=[
            make_station(
                opis_id=1,
                route_mile=400,
                price="4.00",
            ),
            make_station(
                opis_id=2,
                route_mile=450,
                price="3.00",
            ),
        ],
    )

    assert len(plan.stops) == 1

    stop = plan.stops[0]

    assert stop.station.station.opis_id == 2
    assert stop.gallons_purchased == Decimal("40.000")
    assert stop.cost == Decimal("120.00")


def test_same_route_mile_uses_cheapest_station():
    plan = optimize_fuel_stops(
        route_distance_miles=700,
        stations=[
            make_station(
                opis_id=1,
                route_mile=450,
                price="4.00",
            ),
            make_station(
                opis_id=2,
                route_mile=450,
                price="3.00",
            ),
        ],
    )

    assert len(plan.stops) == 1
    assert plan.stops[0].station.station.opis_id == 2


def test_optimizer_rejects_unreachable_route():
    with pytest.raises(NoFeasibleFuelPlanError):
        optimize_fuel_stops(
            route_distance_miles=1200,
            stations=[
                make_station(
                    opis_id=1,
                    route_mile=600,
                    price="3.00",
                ),
            ],
        )