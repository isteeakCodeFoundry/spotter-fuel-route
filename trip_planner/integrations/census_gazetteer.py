import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from trip_planner.integrations.geocoding import Coordinates


class CensusGazetteerError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class GazetteerPlace:
    state: str
    name: str
    coordinates: Coordinates


PLACE_TYPE_SUFFIXES = (
    " consolidated government",
    " metropolitan government",
    " unified government",
    " municipality",
    " borough",
    " village",
    " town",
    " city",
    " cdp",
)

TOKEN_ALIASES = {
    "st": "saint",
    "ft": "fort",
    "mt": "mount",
}


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", errors="ignore").decode("ascii")
    value = value.casefold()

    value = re.sub(r"[^a-z0-9]+", " ", value)
    tokens = value.split()

    tokens = [
        TOKEN_ALIASES.get(token, token)
        for token in tokens
    ]

    return " ".join(tokens)


def _normalize_gazetteer_name(value: str) -> str:
    normalized = _normalize_text(value)

    for suffix in PLACE_TYPE_SUFFIXES:
        normalized_suffix = suffix.strip()

        if normalized.endswith(f" {normalized_suffix}"):
            return normalized[: -(len(normalized_suffix) + 1)]

    return normalized


class CensusGazetteer:
    REQUIRED_COLUMNS = {
        "USPS",
        "NAME",
        "INTPTLAT",
        "INTPTLONG",
    }

    def __init__(
            self,
            places: dict[tuple[str, str], list[GazetteerPlace]],
    ):
        self._places = places

    @classmethod
    def from_zip(cls, zip_path: Path) -> "CensusGazetteer":
        if not zip_path.is_file():
            raise CensusGazetteerError(
                f"Gazetteer ZIP does not exist: {zip_path}"
            )

        places: dict[
            tuple[str, str],
            list[GazetteerPlace],
        ] = {}

        with ZipFile(zip_path) as archive:
            filenames = [
                name
                for name in archive.namelist()
                if name.lower().endswith(".txt")
            ]

            if len(filenames) != 1:
                raise CensusGazetteerError(
                    "Expected exactly one Gazetteer text file "
                    f"inside {zip_path}."
                )

            with archive.open(filenames[0]) as raw_file:
                lines = (
                    line.decode("utf-8-sig")
                    for line in raw_file
                )

                reader = csv.DictReader(
                    lines,
                    delimiter="|",
                )

                columns = set(reader.fieldnames or ())

                missing = cls.REQUIRED_COLUMNS - columns

                if missing:
                    raise CensusGazetteerError(
                        "Gazetteer is missing required columns: "
                        f"{sorted(missing)}"
                    )

                for row_number, row in enumerate(
                        reader,
                        start=2,
                ):
                    try:
                        state = row["USPS"].strip().upper()
                        name = row["NAME"].strip()

                        coordinates = Coordinates(
                            latitude=float(row["INTPTLAT"]),
                            longitude=float(row["INTPTLONG"]),
                        )

                    except (KeyError, TypeError, ValueError) as exc:
                        raise CensusGazetteerError(
                            "Invalid Gazetteer record on line "
                            f"{row_number}."
                        ) from exc

                    normalized_name = (
                        _normalize_gazetteer_name(name)
                    )

                    key = (
                        state,
                        normalized_name,
                    )

                    places.setdefault(key, []).append(
                        GazetteerPlace(
                            state=state,
                            name=name,
                            coordinates=coordinates,
                        )
                    )

        return cls(places)

    def lookup(
            self,
            *,
            state: str,
            city: str,
    ) -> GazetteerPlace | None:
        key = (
            state.strip().upper(),
            _normalize_text(city),
        )

        matches = self._places.get(key, [])

        if len(matches) != 1:
            return None

        return matches[0]