import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import perf_counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from trip_planner.models import FuelPrice, FuelStation

EXPECTED_HEADERS = (
    "OPIS Truckstop ID",
    "Truckstop Name",
    "Address",
    "City",
    "State",
    "Rack ID",
    "Retail Price",
)


class Command(BaseCommand):
    help = "Import Spotter assessment fuel station and fuel price data."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Path to the fuel price CSV file.",
        )

    def handle(self, *args, **options):
        started_at = perf_counter()

        csv_path = Path(options["csv_path"])

        if not csv_path.is_file():
            raise CommandError(
                f"CSV file does not exist: {csv_path}"
            )

        stations_by_opis: dict[int, dict] = {}
        prices_by_opis: dict[int, list[Decimal]] = {}

        rows_read = 0

        try:
            with csv_path.open(
                    mode="r",
                    encoding="utf-8-sig",
                    newline="",
            ) as csv_file:
                reader = csv.DictReader(csv_file)

                actual_headers = tuple(reader.fieldnames or ())

                if actual_headers != EXPECTED_HEADERS:
                    raise CommandError(
                        "Unexpected CSV headers.\n"
                        f"Expected: {EXPECTED_HEADERS}\n"
                        f"Received: {actual_headers}"
                    )

                for line_number, row in enumerate(
                        reader,
                        start=2,
                ):
                    rows_read += 1

                    parsed = self._parse_row(
                        row=row,
                        line_number=line_number,
                    )

                    opis_id = parsed["opis_id"]

                    existing_station = (
                        stations_by_opis.get(opis_id)
                    )

                    if existing_station is None:
                        stations_by_opis[opis_id] = {
                            "opis_id": opis_id,
                            "name": parsed["name"],
                            "address": parsed["address"],
                            "city": parsed["city"],
                            "state": parsed["state"],
                            "rack_id": parsed["rack_id"],
                        }
                    else:
                        self._validate_duplicate_station(
                            existing=existing_station,
                            incoming=parsed,
                            line_number=line_number,
                        )

                        existing_station["name"] = (
                            self._preferred_name(
                                existing_station["name"],
                                parsed["name"],
                            )
                        )

                    prices_by_opis.setdefault(
                        opis_id,
                        [],
                    ).append(
                        parsed["retail_price"]
                    )

        except UnicodeDecodeError as exc:
            raise CommandError(
                f"CSV file is not valid UTF-8: {csv_path}"
            ) from exc

        with transaction.atomic():
            existing_stations = FuelStation.objects.in_bulk(
                stations_by_opis.keys(),
                field_name="opis_id",
            )

            stations_to_create = []
            stations_to_update = []

            for opis_id, station_data in (
                    stations_by_opis.items()
            ):
                existing = existing_stations.get(opis_id)

                if existing is None:
                    stations_to_create.append(
                        FuelStation(**station_data)
                    )
                    continue

                existing.name = station_data["name"]
                existing.address = station_data["address"]
                existing.city = station_data["city"]
                existing.state = station_data["state"]
                existing.rack_id = station_data["rack_id"]

                stations_to_update.append(existing)

            FuelStation.objects.bulk_create(
                stations_to_create,
                batch_size=1000,
            )

            if stations_to_update:
                FuelStation.objects.bulk_update(
                    stations_to_update,
                    fields=[
                        "name",
                        "address",
                        "city",
                        "state",
                        "rack_id",
                    ],
                    batch_size=1000,
                )

            persisted_stations = (
                FuelStation.objects.in_bulk(
                    stations_by_opis.keys(),
                    field_name="opis_id",
                )
            )

            station_ids = [
                station.id
                for station in persisted_stations.values()
            ]

            FuelPrice.objects.filter(
                station_id__in=station_ids
            ).delete()

            prices_to_create = []

            for opis_id, prices in prices_by_opis.items():
                station = persisted_stations[opis_id]

                for retail_price in prices:
                    prices_to_create.append(
                        FuelPrice(
                            station=station,
                            retail_price=retail_price,
                        )
                    )

            FuelPrice.objects.bulk_create(
                prices_to_create,
                batch_size=1000,
            )

        elapsed_seconds = perf_counter() - started_at

        self.stdout.write(
            self.style.SUCCESS(
                "\nFuel price import completed successfully."
            )
        )
        self.stdout.write(
            f"Rows read: {rows_read}"
        )
        self.stdout.write(
            f"Unique stations: {len(stations_by_opis)}"
        )
        self.stdout.write(
            "Price observations: "
            f"{sum(len(values) for values in prices_by_opis.values())}"
        )
        self.stdout.write(
            f"Elapsed: {elapsed_seconds:.3f} seconds"
        )

    @staticmethod
    def _parse_row(
            row: dict[str, str],
            line_number: int,
    ) -> dict:
        try:
            opis_id = int(
                row["OPIS Truckstop ID"].strip()
            )
            rack_id = int(
                row["Rack ID"].strip()
            )
        except (ValueError, AttributeError) as exc:
            raise CommandError(
                "Invalid numeric identifier on CSV line "
                f"{line_number}."
            ) from exc

        if opis_id < 0 or rack_id < 0:
            raise CommandError(
                f"Negative identifier on CSV line {line_number}."
            )

        try:
            retail_price = Decimal(
                row["Retail Price"].strip()
            )
        except (InvalidOperation, AttributeError) as exc:
            raise CommandError(
                "Invalid retail price on CSV line "
                f"{line_number}."
            ) from exc

        if retail_price <= 0:
            raise CommandError(
                "Retail price must be positive on CSV line "
                f"{line_number}."
            )

        name = row["Truckstop Name"].strip()
        address = row["Address"].strip()
        city = row["City"].strip()
        state = row["State"].strip().upper()

        required_values = {
            "Truckstop Name": name,
            "Address": address,
            "City": city,
            "State": state,
        }

        missing_fields = [
            field_name
            for field_name, value in required_values.items()
            if not value
        ]

        if missing_fields:
            raise CommandError(
                "Missing required value(s) on CSV line "
                f"{line_number}: {', '.join(missing_fields)}"
            )

        if len(name) > 100:
            raise CommandError(
                "Truckstop Name exceeds 100 characters "
                f"on CSV line {line_number}."
            )

        if len(address) > 150:
            raise CommandError(
                "Address exceeds 150 characters "
                f"on CSV line {line_number}."
            )

        if len(city) > 100:
            raise CommandError(
                "City exceeds 100 characters "
                f"on CSV line {line_number}."
            )

        if len(state) != 2 or not state.isalpha():
            raise CommandError(
                "Invalid state code on CSV line "
                f"{line_number}: {state!r}"
            )

        return {
            "opis_id": opis_id,
            "name": name,
            "address": address,
            "city": city,
            "state": state,
            "rack_id": rack_id,
            "retail_price": retail_price,
        }

    @staticmethod
    def _validate_duplicate_station(
            existing: dict,
            incoming: dict,
            line_number: int,
    ) -> None:
        stable_fields = (
            "address",
            "city",
            "state",
            "rack_id",
        )

        for field_name in stable_fields:
            if existing[field_name] != incoming[field_name]:
                raise CommandError(
                    "Conflicting station data for OPIS ID "
                    f"{existing['opis_id']} on CSV line "
                    f"{line_number}: "
                    f"field {field_name!r} differs."
                )

    @staticmethod
    def _preferred_name(
            first: str,
            second: str,
    ) -> str:
        return max(
            (first, second),
            key=lambda value: (
                len(value),
                value,
            ),
        )