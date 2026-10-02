import json

import httpx
import pytest

from trip_planner.domain.entities import Coordinates
from trip_planner.integrations.routing import (
    HeiGitRoutingClient,
    RouteNotFoundError,
    RoutingProviderError,
)

def test_get_route_returns_parsed_route():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)

        assert body["coordinates"] == [
            [-87.66063, 41.87897],
            [-96.79700, 32.77670],
        ]

        assert body["instructions"] is False

        return httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [
                                [-87.66063, 41.87897],
                                [-90.0, 38.0],
                                [-96.79700, 32.77670],
                            ],
                        },
                        "properties": {
                            "summary": {
                                "distance": 1500000.0,
                                "duration": 50000.0,
                            }
                        },
                    }
                ],
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )

    router = HeiGitRoutingClient(
        api_key="test-key",
        client=client,
    )

    route = router.get_route(
        start=Coordinates(
            latitude=41.87897,
            longitude=-87.66063,
        ),
        finish=Coordinates(
            latitude=32.77670,
            longitude=-96.79700,
        ),
    )

    assert route.distance_meters == 1500000.0
    assert route.duration_seconds == 50000.0
    assert len(route.coordinates) == 3

    assert route.coordinates[0].latitude == 41.87897
    assert route.coordinates[0].longitude == -87.66063


def test_get_route_rejects_empty_route():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "type": "FeatureCollection",
                "features": [],
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )

    router = HeiGitRoutingClient(
        api_key="test-key",
        client=client,
    )

    with pytest.raises(RouteNotFoundError):
        router.get_route(
            start=Coordinates(
                latitude=41.0,
                longitude=-87.0,
            ),
            finish=Coordinates(
                latitude=32.0,
                longitude=-96.0,
            ),
        )


def test_get_route_handles_rate_limit():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={
                "error": "rate limit",
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )

    router = HeiGitRoutingClient(
        api_key="test-key",
        client=client,
    )

    with pytest.raises(RoutingProviderError):
        router.get_route(
            start=Coordinates(
                latitude=41.0,
                longitude=-87.0,
            ),
            finish=Coordinates(
                latitude=32.0,
                longitude=-96.0,
            ),
        )


def test_get_route_handles_provider_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={
                "error": "unavailable",
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )

    router = HeiGitRoutingClient(
        api_key="test-key",
        client=client,
    )

    with pytest.raises(RoutingProviderError):
        router.get_route(
            start=Coordinates(
                latitude=41.0,
                longitude=-87.0,
            ),
            finish=Coordinates(
                latitude=32.0,
                longitude=-96.0,
            ),
        )

@pytest.mark.parametrize(
    "exception_type",
    [
        httpx.RemoteProtocolError,
        httpx.ConnectError,
        httpx.ReadTimeout,
    ],
)
def test_retries_once_after_transient_transport_failure(
        monkeypatch,
        exception_type,
):
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            raise exception_type(
                "Temporary transport failure.",
                request=request,
            )

        return httpx.Response(
            200,
            json={
                "features": [
                    {
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [
                                [-87.66063, 41.87897],
                                [-96.784359, 32.736212],
                            ],
                        },
                        "properties": {
                            "summary": {
                                "distance": 1_000_000,
                                "duration": 50_000,
                            }
                        },
                    }
                ]
            },
            request=request,
        )

    monkeypatch.setattr(
        "trip_planner.integrations.routing.sleep",
        lambda _: None,
    )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
    )

    try:
        routing_client = HeiGitRoutingClient(
            api_key="test-api-key",
            client=client,
        )

        route = routing_client.get_route(
            start=Coordinates(
                latitude=41.87897,
                longitude=-87.66063,
            ),
            finish=Coordinates(
                latitude=32.736212,
                longitude=-96.784359,
            ),
        )

        assert call_count == 2
        assert route.distance_meters == 1_000_000
        assert route.duration_seconds == 50_000

    finally:
        client.close()


def test_stops_after_second_transient_transport_failure(
        monkeypatch,
):
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1

        raise httpx.RemoteProtocolError(
            "Temporary transport failure.",
            request=request,
        )

    monkeypatch.setattr(
        "trip_planner.integrations.routing.sleep",
        lambda _: None,
    )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
    )

    try:
        routing_client = HeiGitRoutingClient(
            api_key="test-api-key",
            client=client,
        )

        with pytest.raises(
                RoutingProviderError,
                match="Routing provider request failed",
        ):
            routing_client.get_route(
                start=Coordinates(
                    latitude=41.87897,
                    longitude=-87.66063,
                ),
                finish=Coordinates(
                    latitude=32.736212,
                    longitude=-96.784359,
                ),
            )

        assert call_count == 2

    finally:
        client.close()