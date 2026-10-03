from collections.abc import Sequence
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from trip_planner.domain.entities import (
    Coordinates,
    PricedFuelStation,
    Route,
    RouteFuelStation,
)

EARTH_RADIUS_MILES = 3958.7613


@dataclass(frozen=True, slots=True)
class RouteSample:
    coordinates: Coordinates
    route_mile: float


def haversine_miles(
        first: Coordinates,
        second: Coordinates,
) -> float:
    lat1 = radians(first.latitude)
    lon1 = radians(first.longitude)
    lat2 = radians(second.latitude)
    lon2 = radians(second.longitude)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    value = (
            sin(delta_lat / 2) ** 2
            + cos(lat1)
            * cos(lat2)
            * sin(delta_lon / 2) ** 2
    )

    return 2 * EARTH_RADIUS_MILES * asin(sqrt(value))


def interpolate_coordinates(
        start: Coordinates,
        finish: Coordinates,
        fraction: float,
) -> Coordinates:
    return Coordinates(
        latitude=(
                start.latitude
                + (finish.latitude - start.latitude) * fraction
        ),
        longitude=(
                start.longitude
                + (finish.longitude - start.longitude) * fraction
        ),
    )


def sample_route(
        route: Route,
        *,
        interval_miles: float = 5.0,
) -> tuple[RouteSample, ...]:
    if interval_miles <= 0:
        raise ValueError(
            "Route sampling interval must be greater than zero."
        )

    if len(route.coordinates) < 2:
        raise ValueError(
            "Route must contain at least two coordinates."
        )

    segment_lengths: list[float] = []

    for start, finish in zip(
            route.coordinates,
            route.coordinates[1:],
            strict=False,
    ):
        segment_lengths.append(
            haversine_miles(start, finish)
        )

    geometry_distance = sum(segment_lengths)

    if geometry_distance <= 0:
        raise ValueError(
            "Route geometry has no measurable distance."
        )

    scale = route.distance_miles / geometry_distance

    samples: list[RouteSample] = [
        RouteSample(
            coordinates=route.coordinates[0],
            route_mile=0.0,
        )
    ]

    next_target_route_mile = interval_miles
    raw_distance_before_segment = 0.0

    for index, raw_segment_length in enumerate(
            segment_lengths
    ):
        if raw_segment_length <= 0:
            continue

        start = route.coordinates[index]
        finish = route.coordinates[index + 1]

        raw_distance_after_segment = (
                raw_distance_before_segment
                + raw_segment_length
        )

        segment_route_start = (
                raw_distance_before_segment * scale
        )
        segment_route_end = (
                raw_distance_after_segment * scale
        )

        while (
                next_target_route_mile
                < route.distance_miles
                and next_target_route_mile
                <= segment_route_end
        ):
            fraction = (
                               next_target_route_mile
                               - segment_route_start
                       ) / (
                               segment_route_end
                               - segment_route_start
                       )

            samples.append(
                RouteSample(
                    coordinates=interpolate_coordinates(
                        start,
                        finish,
                        fraction,
                    ),
                    route_mile=next_target_route_mile,
                )
            )

            next_target_route_mile += interval_miles

        raw_distance_before_segment = (
            raw_distance_after_segment
        )

    samples.append(
        RouteSample(
            coordinates=route.coordinates[-1],
            route_mile=route.distance_miles,
        )
    )

    return tuple(samples)


def find_route_fuel_stations(
        *,
        route: Route,
        stations: Sequence[PricedFuelStation],
        corridor_miles: float = 25.0,
        sample_interval_miles: float = 5.0,
) -> list[RouteFuelStation]:
    if corridor_miles <= 0:
        raise ValueError(
            "Route corridor must be greater than zero."
        )

    samples = sample_route(
        route,
        interval_miles=sample_interval_miles,
    )

    candidates: list[RouteFuelStation] = []

    for station in stations:
        nearest_sample: RouteSample | None = None
        nearest_distance = float("inf")

        for sample in samples:
            distance = haversine_miles(
                station.coordinates,
                sample.coordinates,
            )

            if distance < nearest_distance:
                nearest_distance = distance
                nearest_sample = sample

        if (
                nearest_sample is None
                or nearest_distance > corridor_miles
        ):
            continue

        candidates.append(
            RouteFuelStation(
                station=station,
                route_mile=nearest_sample.route_mile,
                distance_from_route_miles=nearest_distance,
            )
        )

    candidates.sort(
        key=lambda candidate: (
            candidate.route_mile,
            candidate.station.price_per_gallon,
            candidate.station.opis_id,
        )
    )

    return candidates