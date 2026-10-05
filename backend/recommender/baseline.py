"""Keyword-matching baseline: the comparison point for the recommendation engine.

Uses the same career skill lists as the engine, but only each skill's primary
name: no embeddings, no alternative names, no edge weights and no graph
traversal. A declared skill matches a career skill when, ignoring case, the
two are equal or one contains the other (containment only for terms of at
least MIN_SUBSTRING_LENGTH characters, so "C" or "R" do not match
everything). A career scores the fraction of declared skills it matches.
"""

from dataclasses import dataclass
from functools import lru_cache

from recommender.graph import get_graph
from recommender.matching import SkillMatcher

MIN_SUBSTRING_LENGTH = 3


@dataclass(frozen=True)
class KeywordMatch:
    query: str
    skill_ids: tuple


@dataclass(frozen=True)
class BaselineRecommendation:
    career_id: str
    title: str
    domain: str
    score: float
    matched: tuple  # (query, skill label) pairs


def keyword_match(query, name):
    if query == name:
        return True
    shorter = min(query, name, key=len)
    return len(shorter) >= MIN_SUBSTRING_LENGTH and (query in name or name in query)


class KeywordBaseline:
    def __init__(self, kg):
        self.kg = kg
        self.names = {skill: kg.node(skill)['label'].lower() for skill in kg.skills()}

    def rank(self, skills, top_k=10):
        """Return (matches, recommendations), in the same shape as the engine."""
        queries = SkillMatcher.clean(skills)
        matches = tuple(
            KeywordMatch(q, tuple(sorted(s for s, name in self.names.items() if keyword_match(q.lower(), name))))
            for q in queries
        )

        recommendations = []
        for career in self.kg.careers():
            required = self.kg.skills_of(career)
            matched = tuple(
                (m.query, self.kg.node(s)['label']) for m in matches for s in m.skill_ids if s in required
            )
            hit_queries = {q for q, _ in matched}
            if hit_queries:
                node = self.kg.node(career)
                recommendations.append(BaselineRecommendation(
                    career_id=career,
                    title=node['label'],
                    domain=node['domain'],
                    score=len(hit_queries) / len(queries),
                    matched=matched,
                ))

        # Ties (common with few skills) go to the career matching more skill names.
        recommendations.sort(key=lambda r: (-r.score, -len(r.matched), r.title))
        return matches, recommendations[:top_k] if top_k else recommendations


@lru_cache(maxsize=1)
def get_baseline():
    return KeywordBaseline(get_graph())
