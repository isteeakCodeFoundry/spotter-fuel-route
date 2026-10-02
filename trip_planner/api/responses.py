from trip_planner.domain.entities import TripPlan
from trip_planner.domain.fuel_optimizer import (
    MAX_RANGE_MILES,
    MILES_PER_GALLON,
    TANK_CAPACITY_GALLONS,
)


def build_trip_plan_response(plan: TripPlan) -> dict:
    return {
        "start": {
            "query": plan.start.query,
            "label": plan.start.label,
            "latitude": plan.start.coordinates.latitude,
            "longitude": plan.start.coordinates.longitude,
        },
        "finish": {
            "query": plan.finish.query,
            "label": plan.finish.label,
            "latitude": plan.finish.coordinates.latitude,
            "longitude": plan.finish.coordinates.longitude,
        },
        "route": {
            "distance_miles": round(
                plan.route.distance_miles,
                2,
            ),
            "duration_seconds": round(
                plan.route.duration_seconds,
                1,
            ),
            "geometry": {
                "type": "LineString",
                "coordinates": (
                    plan.route.geojson_coordinates
                ),
            },
        },
        "vehicle": {
            "maximum_range_miles": MAX_RANGE_MILES,
            "fuel_efficiency_mpg": MILES_PER_GALLON,
            "tank_capacity_gallons": (
                TANK_CAPACITY_GALLONS
            ),
        },
        "fuel_stops": [
            {
                "route_mile": round(
                    purchase.station.route_mile,
                    1,
                ),
                "distance_from_route_miles": round(
                    purchase.station.distance_from_route_miles,
                    1,
                ),
                "price_per_gallon": (
                    purchase.station.station.price_per_gallon
                ),
                "gallons_purchased": (
                    purchase.gallons_purchased
                ),
                "cost": purchase.cost,
                "station": {
                    "opis_id": (
                        purchase.station.station.opis_id
                    ),
                    "name": (
                        purchase.station.station.name
                    ),
                    "address": (
                        purchase.station.station.address
                    ),
                    "city": (
                        purchase.station.station.city
                    ),
                    "state": (
                        purchase.station.station.state
                    ),
                    "latitude": (
                        purchase.station
                        .station
                        .coordinates
                        .latitude
                    ),
                    "longitude": (
                        purchase.station
                        .station
                        .coordinates
                        .longitude
                    ),
                    "coordinate_quality": (
                        purchase.station
                        .station
                        .geocode_quality
                    ),
                },
            }
            for purchase in plan.fuel_plan.stops
        ],
        "fuel_summary": {
            "trip_gallons_required": (
                plan.fuel_plan.trip_gallons_required
            ),
            "starting_fuel_gallons": (
                plan.fuel_plan.starting_fuel_gallons
            ),
            "gallons_purchased": (
                plan.fuel_plan.total_gallons_purchased
            ),
            "total_cost": (
                plan.fuel_plan.total_cost
            ),
            "ending_fuel_gallons": (
                plan.fuel_plan.ending_fuel_gallons
            ),
        },
        "metadata": {
            "candidate_station_count": (
                plan.candidate_station_count
            ),
            "normal_external_api_calls": 3,
        },
    }

def build_trip_plan_summary_response(plan: TripPlan) -> dict:
    return {
        "start": plan.start.label,
        "finish": plan.finish.label,
        "route_distance_miles": round(
            plan.route.distance_miles,
            2,
        ),
        "fuel_stops": [
            {
                "route_mile": round(
                    purchase.station.route_mile,
                    1,
                ),
                "station": (
                    purchase.station.station.name
                ),
                "city": (
                    purchase.station.station.city
                ),
                "state": (
                    purchase.station.station.state
                ),
                "gallons_to_buy": (
                    purchase.gallons_purchased
                ),
                "price_per_gallon": (
                    purchase.station.station.price_per_gallon
                ),
                "cost": purchase.cost,
            }
            for purchase in plan.fuel_plan.stops
        ],
        "total_gallons_purchased": (
            plan.fuel_plan.total_gallons_purchased
        ),
        "total_cost": plan.fuel_plan.total_cost,
    }