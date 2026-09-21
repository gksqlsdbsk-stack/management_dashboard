from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("departments", views.DepartmentViewSet, basename="department")
router.register("items", views.InputItemViewSet, basename="item")

urlpatterns = [
    path("metric-keys/", views.MetricKeyListView.as_view()),
    *router.urls,
]
