"""Recommendation history: store the top recommendations each time a profile is saved.

The snapshot keeps what the user was shown (rank, score, explanation and skill
gaps), so later changes to the profile or the engine never rewrite the past.
"""

import dataclasses

from django.db import transaction

from core import services
from core.models import Recommendation, RecommendationExplanation, RecommendationRun, SkillGap
from recommender.engine import DEFAULT_PARAMS
from recommender import presentation
from recommender.explanation import ExplanationGenerator, requirement_of
from recommender.skills_gap import get_skills_gap

SNAPSHOT_SIZE = 10
GAPS_PER_RECOMMENDATION = 5


@transaction.atomic
def snapshot(user, profile):
    """Store the profile's current top recommendations; returns the run, or None without skills."""
    if not profile.skills:
        return None
    background = profile.background_text()
    matches, ranked = services.rank(profile.skills, top_k=SNAPSHOT_SIZE, background=background)
    if not ranked:
        return None
    run = RecommendationRun.objects.create(user=user, skills=list(profile.skills), background=background,
                                           params=dataclasses.asdict(DEFAULT_PARAMS))
    explainer = ExplanationGenerator()
    for position, r in enumerate(ranked, 1):
        # Store the label and wording the student was shown, which the release safety rule limits
        # when few specific skills support the career (recommender.presentation).
        shown = presentation.shown_fit(services.kg(), matches, r)
        stored = Recommendation.objects.create(
            run=run, rank=position, career_code=services.career_code(r.career_id), title=r.title, domain=r.domain,
            score=r.score, fit=shown[0], components=dataclasses.asdict(r.components),
        )
        RecommendationExplanation.objects.create(
            recommendation=stored, sentences=list(explainer.explain(r, matches, rank=position, display=shown).sentences))
        SkillGap.objects.bulk_create(
            SkillGap(recommendation=stored, position=i, skill_id=g.skill_id, label=g.label,
                     requirement=requirement_of(g)[1])
            for i, g in enumerate(get_skills_gap().gaps(r, matches, limit=GAPS_PER_RECOMMENDATION), 1)
        )
    return run


def run_summary(run, previous=None):
    """A run for the history list: when, which skills, and the top three careers."""
    top = list(run.recommendations.all()[:3])
    return {
        'id': run.id,
        'created_at': run.created_at,
        'skills': run.skills,
        'has_background': bool(run.background),
        'top': [{'career_code': r.career_code, 'title': r.title, 'score': r.score} for r in top],
        'changed': previous is not None and [r.career_code for r in top] != [
            r.career_code for r in previous.recommendations.all()[:3]],
    }


def run_detail(run, previous=None):
    """Every stored recommendation, with its explanation, gaps and rank in the previous run."""
    before = {r.career_code: r.rank for r in previous.recommendations.all()} if previous else {}
    return {
        **run_summary(run, previous),
        'background': run.background,
        'previous_id': previous.id if previous else None,
        'recommendations': [
            {
                'rank': r.rank,
                'previous_rank': before.get(r.career_code),
                'career_code': r.career_code,
                'title': r.title,
                'domain': r.domain,
                'score': r.score,
                'fit': r.fit,
                'explanation': r.explanation.sentences,
                'skill_gaps': [{'label': g.label, 'requirement': g.requirement} for g in r.skill_gaps.all()],
            }
            for r in run.recommendations.select_related('explanation').prefetch_related('skill_gaps')
        ],
    }
