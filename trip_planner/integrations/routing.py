from time import sleep

import httpx

from trip_planner.domain.entities import (
    Coordinates,
    Route,
)

METERS_PER_MILE = 1609.344


class RoutingError(Exception):
    """Base error for routing failures."""


class RoutingProviderError(RoutingError):
    """Raised when the external routing provider is unavailable."""


class RouteNotFoundError(RoutingError):
    """Raised when no usable route can be returned."""


class HeiGitRoutingClient:
    BASE_URL = (
        "https://api.heigit.org/openrouteservice/"
        "v2/directions/driving-car/geojson"
    )

    def __init__(
            self,
            *,
            api_key: str,
            client: httpx.Client | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("HeiGIT API key must not be blank.")

        self._api_key = api_key
        self._owns_client = client is None

        self._client = client or httpx.Client(
            timeout=httpx.Timeout(
                30.0,
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

    def get_route(
            self,
            *,
            start: Coordinates,
            finish: Coordinates,
    ) -> Route:

        response = None

        for attempt in range(2):
            try:
                response = self._client.post(
                    self.BASE_URL,
                    headers={
                        "Authorization": self._api_key,
                        "Accept": "application/geo+json",
                        "Content-Type": "application/json",
                    },
                    json={
                        "coordinates": [
                            [
                                start.longitude,
                                start.latitude,
                            ],
                            [
                                finish.longitude,
                                finish.latitude,
                            ],
                        ],
                        "instructions": False,
                    },
                )

                break

            except (
                    httpx.RemoteProtocolError,
                    httpx.ConnectError,
                    httpx.ReadTimeout,
            ) as exc:
                if attempt == 1:
                    raise RoutingProviderError(
                        "Routing provider request failed."
                    ) from exc

                sleep(0.25)

            except httpx.HTTPError as exc:
                raise RoutingProviderError(
                    "Routing provider request failed."
                ) from exc

        if response is None:
            raise RoutingProviderError(
                "Routing provider request failed."
            )

        if response.status_code == 429:
            raise RoutingProviderError(
                "Routing provider rate limit exceeded."
            )

        if response.status_code >= 500:
            raise RoutingProviderError(
                "Routing provider is temporarily unavailable."
            )

        if response.status_code >= 400:
            raise RouteNotFoundError(
                "Routing provider could not calculate the route."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise RoutingProviderError(
                "Routing provider returned invalid JSON."
            ) from exc

        return self._parse_route(payload)

    @staticmethod
    def _parse_route(payload: dict) -> Route:
        try:
            features = payload["features"]

            if not features:
                raise RouteNotFoundError(
                    "Routing provider returned no route."
                )

            feature = features[0]

            geometry = feature["geometry"]
            properties = feature["properties"]
            summary = properties["summary"]

            if geometry["type"] != "LineString":
                raise RoutingProviderError(
                    "Routing provider returned unexpected geometry."
                )

            raw_coordinates = geometry["coordinates"]

            if len(raw_coordinates) < 2:
                raise RoutingProviderError(
                    "Routing provider returned insufficient geometry."
                )

            coordinates = tuple(
                Coordinates(
                    latitude=float(pair[1]),
                    longitude=float(pair[0]),
                )
                for pair in raw_coordinates
            )

            distance_meters = float(summary["distance"])
            duration_seconds = float(summary["duration"])

        except RouteNotFoundError:
            raise

        except (
                KeyError,
                IndexError,
                TypeError,
                ValueError,
        ) as exc:
            raise RoutingProviderError(
                "Routing provider returned an unexpected response."
            ) from exc

        if distance_meters <= 0:
            raise RoutingProviderError(
                "Routing provider returned invalid route distance."
            )

        if duration_seconds <= 0:
            raise RoutingProviderError(
                "Routing provider returned invalid route duration."
            )

        return Route(
            distance_meters=distance_meters,
            duration_seconds=duration_seconds,
            coordinates=coordinates,
        )