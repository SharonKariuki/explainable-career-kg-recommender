"""The recommender, loaded once per server process and shared by every request.

Loading the knowledge graph and the SBERT model takes about 20 seconds, so it
happens at startup (warm_up) rather than on a user's first request. After
that, ranking a profile takes well under a second.
"""

from dataclasses import asdict

from recommender.engine import DEFAULT_PARAMS, get_engine
from recommender.explanation import ExplanationGenerator, requirement_level
from recommender.skills_gap import get_skills_gap


def warm_up():
    get_engine()
    get_skills_gap()


def career_code(career_id):
    return career_id.split(':', 1)[1]


def rank(skills, top_k=None):
    """(matches, recommendations) for a list of declared skills, best first."""
    return get_engine().rank(skills, top_k=top_k)


def match_summary(match):
    return {
        'query': match.query,
        'skill': match.node_label,
        'similarity': match.similarity,
        'low_confidence': match.low_confidence,
    }


def recommendation_summary(recommendation, rank_position):
    r = recommendation
    explanation = ExplanationGenerator().explain(r)
    return {
        'rank': rank_position,
        'career_code': career_code(r.career_id),
        'title': r.title,
        'domain': r.domain,
        'score': r.score,
        'components': asdict(r.components),
        'summary': explanation.sentences[0],
    }


def with_requirement(item):
    """Add the plain label ('Core requirement', 'Important', 'Supporting') for its edge weight."""
    return {**item, 'requirement': requirement_level(item['edge_weight'])[1]}


def recommendation_detail(recommendation, rank_position, matches):
    r = recommendation
    explanation = ExplanationGenerator().explain(r)
    p = DEFAULT_PARAMS
    return {
        **recommendation_summary(r, rank_position),
        'weights': {
            'coverage': p.coverage_weight,
            'profile_similarity': p.similarity_weight,
            'graph_proximity': p.proximity_weight,
        },
        'explanation': list(explanation.sentences),
        'skill_contributions': [with_requirement(asdict(c)) for c in r.skill_contributions],
        'proximity_paths': [asdict(p) for p in r.proximity_paths],
        'skills_gap': [with_requirement(asdict(g)) for g in get_skills_gap().gaps(r, matches)],
    }
