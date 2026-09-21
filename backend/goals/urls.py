from django.urls import path

from . import views

urlpatterns = [
    path("goals/", views.GoalListView.as_view()),
    path("goals/<int:year>/", views.GoalYearView.as_view()),
]
