from django.urls import path

from routing.views import RoutePlanView

urlpatterns = [
    path("routes/plan/", RoutePlanView.as_view(), name="route-plan"),
]
