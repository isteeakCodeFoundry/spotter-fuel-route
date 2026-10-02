from pathlib import Path

from django.conf import settings
from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from trip_planner.integrations.census_gazetteer import (
    CensusGazetteer,
    CensusGazetteerError,
)
from trip_planner.integrations.census_geocoding import (
    BatchAddress,
    CensusBatchGeocoder,
    CensusGeocodingError,
)
from trip_planner.models import FuelStation


class Command(BaseCommand):
    help = (
        "Enrich fuel stations with coordinates using "
        "Census address geocoding and Gazetteer fallback."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
        )

        parser.add_argument(
            "--offline",
            action="store_true",
            help=(
                "Skip Census network address geocoding "
                "and use only the bundled Gazetteer."
            ),
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        offline = options["offline"]

        if limit is not None and limit <= 0:
            raise CommandError(
                "--limit must be greater than zero."
            )

        query = (
            FuelStation.objects
            .filter(
                latitude__isnull=True,
                longitude__isnull=True,
            )
            .order_by("opis_id")
        )

        if limit is not None:
            query = query[:limit]

        stations = list(query)

        if not stations:
            self.stdout.write(
                self.style.SUCCESS(
                    "No stations require enrichment."
                )
            )
            return

        address_matches = 0

        if not offline:
            address_matches = self._apply_address_matches(
                stations
            )

        gazetteer_matches = self._apply_gazetteer_matches(
            stations
        )

        unresolved = sum(
            station.latitude is None
            or station.longitude is None
            for station in stations
        )

        FuelStation.objects.bulk_update(
            stations,
            fields=[
                "latitude",
                "longitude",
                "geocode_source",
                "geocode_quality",
            ],
            batch_size=1000,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\nLocation enrichment completed."
            )
        )
        self.stdout.write(
            f"Processed: {len(stations)}"
        )
        self.stdout.write(
            f"Address matches: {address_matches}"
        )
        self.stdout.write(
            f"Gazetteer matches: {gazetteer_matches}"
        )
        self.stdout.write(
            f"Unresolved: {unresolved}"
        )

    def _apply_address_matches(
            self,
            stations: list[FuelStation],
    ) -> int:
        addresses = [
            BatchAddress(
                record_id=station.opis_id,
                street=station.address,
                city=station.city,
                state=station.state,
            )
            for station in stations
        ]

        self.stdout.write(
            f"Submitting {len(addresses)} addresses "
            "to Census batch geocoder..."
        )

        try:
            with CensusBatchGeocoder() as geocoder:
                results = geocoder.geocode(addresses)

        except CensusGeocodingError as exc:
            self.stderr.write(
                self.style.WARNING(
                    "Census address geocoding failed; "
                    "continuing with offline Gazetteer. "
                    f"Reason: {exc}"
                )
            )
            return 0

        matched = 0

        by_opis = {
            station.opis_id: station
            for station in stations
        }

        for opis_id, result in results.items():
            station = by_opis.get(opis_id)

            if (
                    station is None
                    or not result.matched
                    or result.coordinates is None
            ):
                continue

            station.latitude = result.coordinates.latitude
            station.longitude = result.coordinates.longitude
            station.geocode_source = "census_address"
            station.geocode_quality = (
                    result.match_type or "Match"
            )

            matched += 1

        return matched

    @staticmethod
    def _apply_gazetteer_matches(
            stations: list[FuelStation],
    ) -> int:
        gazetteer_path = (
                settings.BASE_DIR
                / "data"
                / "2026_Gaz_place_national.zip"
        )

        try:
            gazetteer = CensusGazetteer.from_zip(
                Path(gazetteer_path)
            )

        except CensusGazetteerError as exc:
            raise CommandError(str(exc)) from exc

        matched = 0

        for station in stations:
            if (
                    station.latitude is not None
                    and station.longitude is not None
            ):
                continue

            place = gazetteer.lookup(
                state=station.state,
                city=station.city,
            )

            if place is None:
                continue

            station.latitude = place.coordinates.latitude
            station.longitude = place.coordinates.longitude
            station.geocode_source = "census_gazetteer"
            station.geocode_quality = "City_Centroid"

            matched += 1

        return matched