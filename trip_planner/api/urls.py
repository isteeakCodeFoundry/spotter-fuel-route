from django.urls import path

from trip_planner.api.views import TripPlanView


urlpatterns = [
    path(
        "trips/plan/",
        TripPlanView.as_view(),
        name="trip-plan",
    ),
]