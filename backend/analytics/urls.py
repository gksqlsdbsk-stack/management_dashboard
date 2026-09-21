from django.urls import path

from . import views

urlpatterns = [
    path("status/", views.StatusView.as_view()),
    path("status/matrix/", views.StatusMatrixView.as_view()),
    path("dashboard/", views.DashboardView.as_view()),
    path("dashboard/export/", views.DashboardExportView.as_view()),
    path("monthly-report/", views.MonthlyReportView.as_view()),
    path("monthly-report/export/", views.MonthlyReportExportView.as_view()),
]
