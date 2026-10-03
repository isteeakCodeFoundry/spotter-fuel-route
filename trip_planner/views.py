from django.shortcuts import render


def trip_map(request):
    return render(
        request,
        "trip_planner/trip_map.html",
    )