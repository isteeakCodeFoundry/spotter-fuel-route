from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Coordinates:
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class GeocodedLocation:
    query: str
    label: str
    coordinates: Coordinates


@dataclass(frozen=True, slots=True)
class Route:
    distance_meters: float
    duration_seconds: float
    coordinates: tuple[Coordinates, ...]

    @property
    def distance_miles(self) -> float:
        return self.distance_meters / 1609.344

    @property
    def geojson_coordinates(self) -> list[list[float]]:
        return [
            [
                coordinate.longitude,
                coordinate.latitude,
            ]
            for coordinate in self.coordinates
        ]


@dataclass(frozen=True, slots=True)
class PricedFuelStation:
    id: int
    opis_id: int
    name: str
    address: str
    city: str
    state: str
    coordinates: Coordinates
    price_per_gallon: Decimal
    geocode_quality: str


@dataclass(frozen=True, slots=True)
class RouteFuelStation:
    station: PricedFuelStation
    route_mile: float
    distance_from_route_miles: float

@dataclass(frozen=True, slots=True)
class FuelPurchase:
    station: RouteFuelStation
    gallons_purchased: Decimal
    cost: Decimal


@dataclass(frozen=True, slots=True)
class FuelPlan:
    stops: tuple[FuelPurchase, ...]
    trip_gallons_required: Decimal
    starting_fuel_gallons: Decimal
    total_gallons_purchased: Decimal
    total_cost: Decimal
    ending_fuel_gallons: Decimal

@dataclass(frozen=True, slots=True)
class FuelPurchase:
    station: RouteFuelStation
    gallons_purchased: Decimal
    cost: Decimal


@dataclass(frozen=True, slots=True)
class FuelPlan:
    stops: tuple[FuelPurchase, ...]
    trip_gallons_required: Decimal
    starting_fuel_gallons: Decimal
    total_gallons_purchased: Decimal
    total_cost: Decimal
    ending_fuel_gallons: Decimal

@dataclass(frozen=True, slots=True)
class TripPlan:
    start: GeocodedLocation
    finish: GeocodedLocation
    route: Route
    fuel_plan: FuelPlan
    candidate_station_count: int