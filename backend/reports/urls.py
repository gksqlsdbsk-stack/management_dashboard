from django.urls import path

from . import views

urlpatterns = [
    path("my-report/<int:year>/<int:month>/", views.MyReportView.as_view()),
    path("my-report/<int:year>/<int:month>/submit/", views.MyReportSubmitView.as_view()),
    path("my-report/<int:year>/<int:month>/upload/", views.MyReportUploadView.as_view()),
    path("departments/<int:department_id>/report/<int:year>/<int:month>/", views.DepartmentReportView.as_view()),
    path(
        "departments/<int:department_id>/report/<int:year>/<int:month>/reopen/",
        views.DepartmentReportReopenView.as_view(),
    ),
]
