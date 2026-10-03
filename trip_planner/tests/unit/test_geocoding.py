import httpx
import pytest

from trip_planner.integrations.geocoding import (
    HeiGitGeocoder,
    LocationNotFoundError,
)


def test_geocode_returns_us_location():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "features": [
                    {
                        "geometry": {
                            "type": "Point",
                            "coordinates": [
                                -87.66063,
                                41.87897,
                            ],
                        },
                        "properties": {
                            "label": "Chicago, IL, USA",
                            "country_a": "USA",
                        },
                    }
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )

    geocoder = HeiGitGeocoder(
        api_key="test-key",
        client=client,
    )

    result = geocoder.geocode("Chicago, IL")

    assert result.label == "Chicago, IL, USA"
    assert result.coordinates.latitude == 41.87897
    assert result.coordinates.longitude == -87.66063


def test_geocode_rejects_location_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "features": [],
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )

    geocoder = HeiGitGeocoder(
        api_key="test-key",
        client=client,
    )

    with pytest.raises(LocationNotFoundError):
        geocoder.geocode("Not A Real Place")


def test_geocode_rejects_non_us_result():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "features": [
                    {
                        "geometry": {
                            "type": "Point",
                            "coordinates": [
                                -0.1276,
                                51.5072,
                            ],
                        },
                        "properties": {
                            "label": "London, England",
                            "country_a": "GBR",
                        },
                    }
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )

    geocoder = HeiGitGeocoder(
        api_key="test-key",
        client=client,
    )

    with pytest.raises(LocationNotFoundError):
        geocoder.geocode("London")


def test_geocode_rejects_non_us_provider_result():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["boundary.country"] == "US"

        return httpx.Response(
            200,
            json={
                "features": [
                    {
                        "properties": {
                            "label": "Toronto, Ontario, Canada",
                            "country_a": "CAN",
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [
                                -79.3832,
                                43.6532,
                            ],
                        },
                    }
                ]
            },
            request=request,
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )

    try:
        geocoder = HeiGitGeocoder(
            api_key="test-key",
            client=client,
        )

        with pytest.raises(
                LocationNotFoundError,
                match="not within the USA",
        ):
            geocoder.geocode("Toronto, Canada")

    finally:
        client.close()
