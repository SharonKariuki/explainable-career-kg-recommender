"""
Recommendation and Explanation models.

These tables persist what the engine produced so that every ranking can be
audited later. The explainability requirement depends on this: an explanation
must be traceable to the exact evidence behind a score, so each term of

    FinalScore = wc * SkillCoverage + wp * GraphProximity - wm * MissingPenalty

is stored in its own column, never folded into a single number. The weights,
threshold and model in force at the time are stored in `scoring_config`, so a
stored score can be recomputed from its components.

Occupations are referenced by O*NET-SOC code only (for example
"15-1252.00"). Occupation and skill data live in the knowledge graph, not in
PostgreSQL.
"""

import uuid

from django.db import models

from apps.profiles.models import Profile


class Recommendation(models.Model):
    run_id = models.UUIDField(
        default=uuid.uuid4,
        db_index=True,
        help_text="Groups the ranked list produced by one recommendation request.",
    )
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="recommendations")
    occupation_code = models.CharField(
        max_length=10,
        db_index=True,
        help_text="O*NET-SOC code of the recommended occupation, e.g. 15-1252.00.",
    )
    rank = models.PositiveSmallIntegerField(help_text="1 is the top recommendation.")

    final_score = models.FloatField()
    skill_coverage = models.FloatField(help_text="SkillCoverage term before weighting.")
    graph_proximity = models.FloatField(help_text="GraphProximity term before weighting.")
    missing_penalty = models.FloatField(help_text="MissingPenalty term before weighting.")
    traversal_depth = models.PositiveSmallIntegerField(
        help_text="Number of hops from the matched skill nodes to the occupation."
    )

    scoring_config = models.JSONField(
        default=dict,
        help_text="Weights, threshold, depth limit and model name used for this score.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recommendations_recommendation"
        ordering = ["run_id", "rank"]
        constraints = [
            models.UniqueConstraint(fields=["run_id", "rank"], name="unique_rank_per_run"),
            models.UniqueConstraint(
                fields=["run_id", "occupation_code"],
                name="unique_occupation_per_run",
            ),
        ]
        indexes = [models.Index(fields=["profile", "created_at"])]

    def __str__(self):
        return f"#{self.rank} {self.occupation_code} ({self.final_score:.3f})"


class Explanation(models.Model):
    recommendation = models.OneToOneField(
        Recommendation, on_delete=models.CASCADE, related_name="explanation"
    )
    text = models.TextField(
        help_text="Plain-language explanation rendered from the structured evidence."
    )
    matched_skills = models.JSONField(
        default=list,
        help_text=(
            "One entry per matched skill: the user's wording, the graph skill id and "
            "label, the similarity score and the O*NET importance weight."
        ),
    )
    missing_skills = models.JSONField(
        default=list,
        help_text="Required skills the user did not match, with importance weights.",
    )
    evidence_paths = models.JSONField(
        default=list,
        help_text="Graph paths (node ids and edge types) linking user skills to the occupation.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recommendations_explanation"

    def __str__(self):
        return f"Explanation for {self.recommendation}"
