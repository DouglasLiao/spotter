"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404, JsonResponse
from django.urls import include, path, re_path


def health(request):
    return JsonResponse({"status": "ok"})


def frontend(request):
    if not settings.FRONTEND_DIST:
        raise Http404("Frontend is served separately in this environment.")
    index = Path(settings.FRONTEND_DIST) / "index.html"
    if not index.is_file():
        raise Http404("Frontend build unavailable.")
    response = FileResponse(index.open("rb"), content_type="text/html")
    response["Cache-Control"] = "no-cache"
    return response


urlpatterns = [
    path("api/health/", health, name="health"),
    path("api/", include("routing.urls")),
    re_path(r"^(?!(?:api|admin|assets|static)(?:/|$)).*$", frontend, name="frontend"),
]
if not settings.SERVERLESS:
    urlpatterns.insert(1, path("admin/", admin.site.urls))
