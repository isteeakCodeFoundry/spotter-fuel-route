from trip_planner.domain.entities import (
    Coordinates,
    GeocodedLocation,
)
import httpx


class GeocodingError(Exception):
    """Base error for geocoding failures."""


class LocationNotFoundError(GeocodingError):
    """Raised when a US location cannot be resolved."""

class HeiGitGeocoder:
    BASE_URL = "https://api.heigit.org/pelias/v1/search"

    def __init__(
            self,
            *,
            api_key: str,
            client: httpx.Client | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("HeiGIT API key must not be blank.")

        self._owns_client = client is None

        self._client = client or httpx.Client(
            headers={
                "Authorization": api_key,
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
        if self._owns_client:
            self._client.close()

    def geocode(
            self,
            query: str,
    ) -> GeocodedLocation:
        normalized_query = " ".join(query.split())

        if not normalized_query:
            raise ValueError("Location query must not be blank.")

        try:
            response = self._client.get(
                self.BASE_URL,
                params={
                    "text": normalized_query,
                    "size": 1,
                    "boundary.country": "US",
                },
            )

            response.raise_for_status()

        except httpx.HTTPError as exc:
            raise GeocodingError(
                "Location geocoding provider request failed."
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise GeocodingError(
                "Location geocoding provider returned invalid JSON."
            ) from exc

        features = payload.get("features")

        if not isinstance(features, list) or not features:
            raise LocationNotFoundError(
                f"Could not resolve location within the USA: "
                f"{normalized_query!r}"
            )

        feature = features[0]

        try:
            properties = feature["properties"]
            geometry = feature["geometry"]

            coordinates = geometry["coordinates"]

            longitude = float(coordinates[0])
            latitude = float(coordinates[1])

            label = str(properties["label"])
            country_code = str(properties["country_a"])

        except (
                KeyError,
                IndexError,
                TypeError,
                ValueError,
        ) as exc:
            raise GeocodingError(
                "Location geocoding provider returned "
                "an unexpected response."
            ) from exc

        if country_code != "USA":
            raise LocationNotFoundError(
                f"Location is not within the USA: "
                f"{normalized_query!r}"
            )

        if not (-90 <= latitude <= 90):
            raise GeocodingError(
                "Geocoder returned an invalid latitude."
            )

        if not (-180 <= longitude <= 180):
            raise GeocodingError(
                "Geocoder returned an invalid longitude."
            )

        return GeocodedLocation(
            query=normalized_query,
            label=label,
            coordinates=Coordinates(
                latitude=latitude,
                longitude=longitude,
            ),
        )