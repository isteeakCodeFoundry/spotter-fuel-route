from trip_planner.domain.entities import TripPlan
from trip_planner.domain.fuel_optimizer import optimize_fuel_stops
from trip_planner.domain.geometry import find_route_fuel_stations
from trip_planner.integrations.geocoding import (
    HeiGitGeocoder,
    LocationNotFoundError,
)
from trip_planner.integrations.routing import HeiGitRoutingClient
from trip_planner.repositories.fuel_stations import FuelStationRepository

ROUTE_CORRIDOR_MILES = 10.0
ROUTE_SAMPLE_INTERVAL_MILES = 5.0


class TripLocationNotFoundError(Exception):
    def __init__(self, field: str, query: str) -> None:
        self.field = field
        self.query = query

        super().__init__(
            f"Could not resolve {field} location "
            f"within the USA: {query!r}"
        )


class TripPlannerService:
    def __init__(
            self,
            *,
            geocoder: HeiGitGeocoder,
            router: HeiGitRoutingClient,
            fuel_station_repository: FuelStationRepository,
    ) -> None:
        self._geocoder = geocoder
        self._router = router
        self._fuel_station_repository = fuel_station_repository

    def plan(
            self,
            *,
            start_query: str,
            finish_query: str,
    ) -> TripPlan:
        try:
            start = self._geocoder.geocode(start_query)
        except LocationNotFoundError as exc:
            raise TripLocationNotFoundError(
                "start",
                start_query,
            ) from exc

        try:
            finish = self._geocoder.geocode(finish_query)
        except LocationNotFoundError as exc:
            raise TripLocationNotFoundError(
                "finish",
                finish_query,
            ) from exc

        if start.coordinates == finish.coordinates:
            raise ValueError(
                "Start and finish locations must be different."
            )

        route = self._router.get_route(
            start=start.coordinates,
            finish=finish.coordinates,
        )

        stations = (
            self._fuel_station_repository
            .find_geocoded_with_prices()
        )

        candidates = find_route_fuel_stations(
            route=route,
            stations=stations,
            corridor_miles=ROUTE_CORRIDOR_MILES,
            sample_interval_miles=ROUTE_SAMPLE_INTERVAL_MILES,
        )

        fuel_plan = optimize_fuel_stops(
            route_distance_miles=route.distance_miles,
            stations=candidates,
        )

        return TripPlan(
            start=start,
            finish=finish,
            route=route,
            fuel_plan=fuel_plan,
            candidate_station_count=len(candidates),
        )