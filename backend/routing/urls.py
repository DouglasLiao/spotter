from django.urls import path

from routing.views import CitySearchView, RoutePlanView

urlpatterns = [
    path("cities/", CitySearchView.as_view(), name="city-search"),
    path("routes/plan/", RoutePlanView.as_view(), name="route-plan"),
]
