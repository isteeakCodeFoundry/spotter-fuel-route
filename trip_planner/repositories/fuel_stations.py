from django.db.models import Min

from trip_planner.domain.entities import (
    Coordinates,
    PricedFuelStation,
)
from trip_planner.models import FuelStation


class FuelStationRepository:
    def find_geocoded_with_prices(
            self,
    ) -> list[PricedFuelStation]:
        rows = (
            FuelStation.objects
            .filter(
                latitude__isnull=False,
                longitude__isnull=False,
                prices__isnull=False,
            )
            .annotate(
                effective_price=Min("prices__retail_price")
            )
            .values(
                "id",
                "opis_id",
                "name",
                "address",
                "city",
                "state",
                "latitude",
                "longitude",
                "geocode_quality",
                "effective_price",
            )
        )

        return [
            PricedFuelStation(
                id=row["id"],
                opis_id=row["opis_id"],
                name=row["name"],
                address=row["address"],
                city=row["city"],
                state=row["state"],
                coordinates=Coordinates(
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                ),
                price_per_gallon=row["effective_price"],
                geocode_quality=row["geocode_quality"],
            )
            for row in rows
        ]