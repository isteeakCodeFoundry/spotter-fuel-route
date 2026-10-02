from django.urls import path

from trip_planner.api.views import (
    TripPlanSummaryView,
    TripPlanView,
)


urlpatterns = [
    path(
        "trips/plan/",
        TripPlanView.as_view(),
        name="trip-plan",
    ),
    path(
        "trips/plan/summary/",
        TripPlanSummaryView.as_view(),
        name="trip-plan-summary",
    ),
]