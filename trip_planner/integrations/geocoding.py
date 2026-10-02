from dataclasses import dataclass
from time import monotonic, sleep

import httpx


class GeocodingError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Coordinates:
    latitude: float
    longitude: float


class NominatimGeocoder:
    BASE_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(
            self,
            *,
            user_agent: str,
            minimum_interval_seconds: float = 1.05,
    ):
        if minimum_interval_seconds < 1.0:
            raise ValueError(
                "Nominatim requests must be limited to at most one per second."
            )

        self._minimum_interval_seconds = minimum_interval_seconds
        self._last_request_at: float | None = None

        self._client = httpx.Client(
            headers={
                "User-Agent": user_agent,
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(
                15.0,
                connect=5.0,
            ),
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self) -> None:
        self._client.close()

    def geocode(self, query: str) -> Coordinates | None:
        query = " ".join(query.split())

        if not query:
            return None

        self._wait_for_rate_limit()

        try:
            response = self._client.get(
                self.BASE_URL,
                params={
                    "q": query,
                    "format": "jsonv2",
                    "limit": 1,
                    "countrycodes": "us",
                    "addressdetails": 1,
                },
            )

            response.raise_for_status()

        except httpx.HTTPError as exc:
            raise GeocodingError(
                f"Geocoding request failed for {query!r}."
            ) from exc

        try:
            results = response.json()
        except ValueError as exc:
            raise GeocodingError(
                "Geocoder returned invalid JSON."
            ) from exc

        if not results:
            return None

        result = results[0]

        try:
            return Coordinates(
                latitude=float(result["lat"]),
                longitude=float(result["lon"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GeocodingError(
                "Geocoder returned invalid coordinates."
            ) from exc

    def _wait_for_rate_limit(self) -> None:
        if self._last_request_at is not None:
            elapsed = monotonic() - self._last_request_at
            remaining = self._minimum_interval_seconds - elapsed

            if remaining > 0:
                sleep(remaining)

        self._last_request_at = monotonic()