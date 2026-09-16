from django.contrib import admin

from .models import Explanation, Recommendation


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "occupation_code",
        "rank",
        "final_score",
        "skill_coverage",
        "graph_proximity",
        "missing_penalty",
        "traversal_depth",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("occupation_code",)


@admin.register(Explanation)
class ExplanationAdmin(admin.ModelAdmin):
    list_display = ("recommendation", "created_at")
