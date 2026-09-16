from django.urls import path

from . import views

app_name = "recommendations"

urlpatterns = [
    path("", views.RecommendationListView.as_view(), name="list"),
    path("<int:pk>/", views.RecommendationDetailView.as_view(), name="detail"),
    path("<int:pk>/explanation/", views.ExplanationView.as_view(), name="explanation"),
    path("<int:pk>/skills-gap/", views.SkillsGapView.as_view(), name="skills-gap"),
]
