import csv
from dataclasses import dataclass
from io import StringIO

import httpx

from trip_planner.integrations.geocoding import Coordinates


class CensusGeocodingError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class BatchAddress:
    record_id: int
    street: str
    city: str
    state: str
    zip_code: str = ""


@dataclass(frozen=True, slots=True)
class BatchGeocodeResult:
    record_id: int
    matched: bool
    match_type: str
    matched_address: str
    coordinates: Coordinates | None


class CensusBatchGeocoder:
    URL = (
        "https://geocoding.geo.census.gov/"
        "geocoder/locations/addressbatch"
    )

    MAX_RECORDS = 10_000
    MAX_FILE_BYTES = 5 * 1024 * 1024

    def __init__(self) -> None:
        self._client = httpx.Client(
            headers={
                "User-Agent": "spotter-fuel-route-assessment/1.0",
            },
            timeout=httpx.Timeout(
                120.0,
                connect=10.0,
            ),
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self) -> None:
        self._client.close()

    def geocode(
            self,
            addresses: list[BatchAddress],
    ) -> dict[int, BatchGeocodeResult]:
        if not addresses:
            return {}

        if len(addresses) > self.MAX_RECORDS:
            raise CensusGeocodingError(
                f"Batch contains {len(addresses)} records; "
                f"maximum is {self.MAX_RECORDS}."
            )

        csv_bytes = self._build_csv(addresses)

        if len(csv_bytes) > self.MAX_FILE_BYTES:
            raise CensusGeocodingError(
                "Generated Census batch file exceeds 5 MB."
            )

        try:
            response = self._client.post(
                self.URL,
                data={
                    "benchmark": "4",
                },
                files={
                    "addressFile": (
                        "addresses.csv",
                        csv_bytes,
                        "text/csv",
                    )
                },
            )

            response.raise_for_status()

        except httpx.HTTPError as exc:
            raise CensusGeocodingError(
                "Census batch geocoding request failed."
            ) from exc

        return self._parse_response(response.content)

    @staticmethod
    def _build_csv(
            addresses: list[BatchAddress],
    ) -> bytes:
        output = StringIO(newline="")
        writer = csv.writer(
            output,
            lineterminator="\n",
        )

        for address in addresses:
            writer.writerow(
                [
                    address.record_id,
                    address.street,
                    address.city,
                    address.state,
                    address.zip_code,
                ]
            )

        return output.getvalue().encode("utf-8")

    @staticmethod
    def _parse_response(
            content: bytes,
    ) -> dict[int, BatchGeocodeResult]:
        text = content.decode(
            "utf-8-sig",
            errors="strict",
        )

        reader = csv.reader(StringIO(text))

        results: dict[int, BatchGeocodeResult] = {}

        for row_number, row in enumerate(reader, start=1):
            if len(row) < 3:
                raise CensusGeocodingError(
                    "Unexpected Census response format "
                    f"on row {row_number}: {row!r}"
                )

            try:
                record_id = int(row[0])
            except ValueError as exc:
                raise CensusGeocodingError(
                    f"Invalid record ID on response row "
                    f"{row_number}."
                ) from exc

            match_indicator = row[2].strip()

            if match_indicator == "No_Match":
                results[record_id] = BatchGeocodeResult(
                    record_id=record_id,
                    matched=False,
                    match_type="No_Match",
                    matched_address="",
                    coordinates=None,
                )
                continue

            if match_indicator == "Tie":
                results[record_id] = BatchGeocodeResult(
                    record_id=record_id,
                    matched=False,
                    match_type="Tie",
                    matched_address="",
                    coordinates=None,
                )
                continue

            if match_indicator != "Match":
                raise CensusGeocodingError(
                    "Unknown Census match indicator "
                    f"{match_indicator!r} on row {row_number}."
                )

            if len(row) < 8:
                raise CensusGeocodingError(
                    "Matched Census response is incomplete "
                    f"on row {row_number}: {row!r}"
                )

            match_type = row[3].strip()
            matched_address = row[4].strip()
            coordinate_text = row[5].strip()

            try:
                longitude_text, latitude_text = (
                    coordinate_text.split(",", maxsplit=1)
                )

                coordinates = Coordinates(
                    latitude=float(latitude_text),
                    longitude=float(longitude_text),
                )

            except (ValueError, TypeError) as exc:
                raise CensusGeocodingError(
                    "Invalid coordinates returned for "
                    f"record {record_id}: "
                    f"{coordinate_text!r}"
                ) from exc

            results[record_id] = BatchGeocodeResult(
                record_id=record_id,
                matched=True,
                match_type=match_type or "Match",
                matched_address=matched_address,
                coordinates=coordinates,
            )

        return results