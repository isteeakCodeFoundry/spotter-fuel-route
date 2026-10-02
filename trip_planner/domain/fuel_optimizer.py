from collections import defaultdict
from decimal import Decimal

from trip_planner.domain.entities import (
    FuelPlan,
    FuelPurchase,
    RouteFuelStation,
)


class NoFeasibleFuelPlanError(Exception):
    """Raised when the vehicle cannot complete the route."""


MILES_PER_GALLON = Decimal("10")
MAX_RANGE_MILES = Decimal("500")
TANK_CAPACITY_GALLONS = MAX_RANGE_MILES / MILES_PER_GALLON

ZERO = Decimal("0")
MONEY_QUANTUM = Decimal("0.01")
FUEL_QUANTUM = Decimal("0.001")


def optimize_fuel_stops(
        *,
        route_distance_miles: float,
        stations: list[RouteFuelStation],
        mpg: Decimal = MILES_PER_GALLON,
        max_range_miles: Decimal = MAX_RANGE_MILES,
) -> FuelPlan:
    if route_distance_miles <= 0:
        raise ValueError(
            "Route distance must be greater than zero."
        )

    if mpg <= 0:
        raise ValueError(
            "Fuel efficiency must be greater than zero."
        )

    if max_range_miles <= 0:
        raise ValueError(
            "Maximum range must be greater than zero."
        )

    route_distance = Decimal(str(route_distance_miles))
    tank_capacity = max_range_miles / mpg

    candidates = _collapse_same_mile_stations(
        stations=stations,
        route_distance=route_distance,
    )

    _validate_route_reachability(
        route_distance=route_distance,
        stations=candidates,
        max_range_miles=max_range_miles,
    )

    trip_gallons_required = route_distance / mpg

    # Assessment assumption:
    # The vehicle begins with a full tank.
    current_fuel = tank_capacity
    current_mile = ZERO

    purchases: list[FuelPurchase] = []

    for index, station in enumerate(candidates):
        station_mile = Decimal(str(station.route_mile))

        distance_travelled = station_mile - current_mile

        if distance_travelled < ZERO:
            raise NoFeasibleFuelPlanError(
                "Fuel stations are not ordered along the route."
            )

        fuel_consumed = distance_travelled / mpg
        current_fuel -= fuel_consumed

        if current_fuel < ZERO:
            raise NoFeasibleFuelPlanError(
                "Vehicle cannot reach the next fuel station."
            )

        current_mile = station_mile

        remaining_distance = route_distance - current_mile

        if remaining_distance <= ZERO:
            break

        # If our current fuel already reaches the destination,
        # buying more fuel can never reduce trip cost.
        if current_fuel * mpg >= remaining_distance:
            continue

        cheaper_station = _find_first_cheaper_station(
            current_index=index,
            stations=candidates,
            max_range_miles=max_range_miles,
        )

        if cheaper_station is not None:
            cheaper_mile = Decimal(
                str(cheaper_station.route_mile)
            )

            target_fuel = (
                                  cheaper_mile - current_mile
                          ) / mpg
        else:
            target_fuel = min(
                tank_capacity,
                remaining_distance / mpg,
                )

        gallons_to_buy = max(
            ZERO,
            target_fuel - current_fuel,
            )

        if gallons_to_buy == ZERO:
            continue

        price = station.station.price_per_gallon

        cost = gallons_to_buy * price

        purchases.append(
            FuelPurchase(
                station=station,
                gallons_purchased=gallons_to_buy.quantize(
                    FUEL_QUANTUM
                ),
                cost=cost.quantize(MONEY_QUANTUM),
            )
        )

        current_fuel += gallons_to_buy

    final_leg_distance = route_distance - current_mile
    current_fuel -= final_leg_distance / mpg

    if current_fuel < ZERO:
        raise NoFeasibleFuelPlanError(
            "Vehicle cannot reach the destination."
        )

    total_gallons = sum(
        (
            purchase.gallons_purchased
            for purchase in purchases
        ),
        start=ZERO,
    )

    total_cost = sum(
        (
            purchase.cost
            for purchase in purchases
        ),
        start=ZERO,
    )

    return FuelPlan(
        stops=tuple(purchases),
        trip_gallons_required=trip_gallons_required.quantize(
            FUEL_QUANTUM
        ),
        starting_fuel_gallons=tank_capacity.quantize(
            FUEL_QUANTUM
        ),
        total_gallons_purchased=total_gallons.quantize(
            FUEL_QUANTUM
        ),
        total_cost=total_cost.quantize(
            MONEY_QUANTUM
        ),
        ending_fuel_gallons=current_fuel.quantize(
            FUEL_QUANTUM
        ),
    )


def _collapse_same_mile_stations(
        *,
        stations: list[RouteFuelStation],
        route_distance: Decimal,
) -> list[RouteFuelStation]:
    by_mile: dict[float, list[RouteFuelStation]] = defaultdict(list)

    for station in stations:
        station_mile = Decimal(str(station.route_mile))

        # Stations at/before the origin aren't needed because
        # the vehicle starts with a full tank.
        if station_mile <= ZERO:
            continue

        # No fuel purchase is useful at the destination.
        if station_mile >= route_distance:
            continue

        by_mile[station.route_mile].append(station)

    selected = []

    for route_mile, same_mile_stations in by_mile.items():
        best = min(
            same_mile_stations,
            key=lambda candidate: (
                candidate.station.price_per_gallon,
                candidate.distance_from_route_miles,
                candidate.station.opis_id,
            ),
        )

        selected.append(best)

    selected.sort(
        key=lambda candidate: candidate.route_mile
    )

    return selected


def _find_first_cheaper_station(
        *,
        current_index: int,
        stations: list[RouteFuelStation],
        max_range_miles: Decimal,
) -> RouteFuelStation | None:
    current = stations[current_index]
    current_mile = Decimal(str(current.route_mile))
    current_price = current.station.price_per_gallon

    for candidate in stations[current_index + 1:]:
        candidate_mile = Decimal(
            str(candidate.route_mile)
        )

        distance = candidate_mile - current_mile

        if distance > max_range_miles:
            break

        if candidate.station.price_per_gallon < current_price:
            return candidate

    return None


def _validate_route_reachability(
        *,
        route_distance: Decimal,
        stations: list[RouteFuelStation],
        max_range_miles: Decimal,
) -> None:
    points = [
        ZERO,
        *(
            Decimal(str(station.route_mile))
            for station in stations
        ),
        route_distance,
    ]

    for left, right in zip(points, points[1:]):
        if right - left > max_range_miles:
            raise NoFeasibleFuelPlanError(
                "No fuel station sequence can satisfy the "
                f"{max_range_miles}-mile maximum range."
            )