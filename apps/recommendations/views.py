"""Recommendation endpoints. Stubs only in Sprint 1."""

from apps.common_stub import NotImplementedView


class RecommendationListView(NotImplementedView):
    description = "Generate (POST) or list (GET) ranked recommendations for the current user."
    planned_sprint = 3


class RecommendationDetailView(NotImplementedView):
    description = "Retrieve one recommendation with its score components."
    planned_sprint = 3


class ExplanationView(NotImplementedView):
    description = "Retrieve the explanation and evidence for one recommendation."
    planned_sprint = 4


class SkillsGapView(NotImplementedView):
    description = "Retrieve the skills gap for one recommendation."
    planned_sprint = 4
