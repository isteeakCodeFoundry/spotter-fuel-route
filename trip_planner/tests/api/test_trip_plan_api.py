from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def test_plan_trip_accepts_valid_locations():
    client = APIClient()

    response = client.post(
        reverse("trip-plan"),
        {
            "start": "Chicago, IL",
            "finish": "Dallas, TX",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "start": "Chicago, IL",
        "finish": "Dallas, TX",
        "message": "Trip planning endpoint is ready.",
    }


def test_plan_trip_rejects_blank_start():
    client = APIClient()

    response = client.post(
        reverse("trip-plan"),
        {
            "start": "",
            "finish": "Dallas, TX",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "start" in response.data


def test_plan_trip_rejects_missing_finish():
    client = APIClient()

    response = client.post(
        reverse("trip-plan"),
        {
            "start": "Chicago, IL",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "finish" in response.data



    def test_plan_trip_rejects_unexpected_fields():
        client = APIClient()

    response = client.post(
        reverse("trip-plan"),
        {
            "start": "Chicago, IL",
            "finish": "Dallas, TX",
            "admin": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_plan_trip_rejects_control_characters():
    client = APIClient()

    response = client.post(
        reverse("trip-plan"),
        {
            "start": "Chicago,\x00IL",
            "finish": "Dallas, TX",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_plan_trip_rejects_oversized_location():
    client = APIClient()

    response = client.post(
        reverse("trip-plan"),
        {
            "start": "A" * 256,
            "finish": "Dallas, TX",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_plan_trip_treats_sql_like_text_as_plain_input():
    client = APIClient()

    response = client.post(
        reverse("trip-plan"),
        {
            "start": "' OR 1=1 --",
            "finish": "Dallas, TX",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["start"] == "' OR 1=1 --"