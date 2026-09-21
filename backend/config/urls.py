from django.urls import include, path

urlpatterns = [
    path("api/", include("accounts.urls")),
    path("api/", include("organization.urls")),
    path("api/", include("reports.urls")),
]
