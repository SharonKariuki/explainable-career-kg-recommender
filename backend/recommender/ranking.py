"""Rank careers for a declared skill profile.

1. Each declared skill is matched to a graph skill node (SkillMatcher).
2. Candidate careers are those one hop from a matched skill in the graph.
3. Each candidate is scored by the cosine similarity between the profile
   vector (match similarity per matched skill) and the career vector (edge
   weight per required skill), both weighted by IDF so that skills nearly
   every career requires, such as Python, count for less than distinctive
   ones.

Each recommendation keeps every matched skill's contribution to its score;
the contributions sum to the score. This is the initial ranking: the full
weighted scoring formula replaces it in Sprint 3.

Usage (from backend/):
    python -m recommender.ranking Python "machine learning" statistics --top 5
"""

import argparse
import math
from dataclasses import dataclass
from functools import lru_cache

from recommender.graph import get_graph
from recommender.matching import SkillMatcher


@dataclass(frozen=True)
class Contribution:
    query: str
    skill_id: str
    skill_label: str
    match_similarity: float
    edge_weight: float
    idf: float
    contribution: float


@dataclass(frozen=True)
class Recommendation:
    career_id: str
    title: str
    domain: str
    score: float
    contributions: tuple


class CareerRanker:
    def __init__(self, kg, matcher):
        self.kg = kg
        self.matcher = matcher
        careers = len(kg.careers())
        # Smoothed so a skill every career requires still counts (idf 1), just least.
        self.idf = {skill: math.log(careers / len(kg.careers_requiring(skill))) + 1 for skill in kg.skills()}
        self.career_norms = {
            career: math.sqrt(sum((w * self.idf[s]) ** 2 for s, w in kg.skills_of(career).items()))
            for career in kg.careers()
        }

    def rank(self, skills, top_k=10):
        """Return (matches, recommendations) for a list of declared skills."""
        matches = self.matcher.match(skills)

        # A skill node matched by several declared skills keeps its best match.
        best = {}
        for match in matches:
            if match.node_id not in best or match.similarity > best[match.node_id].similarity:
                best[match.node_id] = match
        profile = {node: match.similarity * self.idf[node] for node, match in best.items()}
        profile_norm = math.sqrt(sum(v * v for v in profile.values()))
        if not profile_norm:
            return matches, []

        reached = self.kg.traverse(profile, max_depth=1)
        candidates = [node for node, depth in reached.items() if depth == 1]

        recommendations = []
        for career in candidates:
            required = self.kg.skills_of(career)
            norm = profile_norm * self.career_norms[career]
            contributions = tuple(sorted(
                (
                    Contribution(
                        query=best[skill].query,
                        skill_id=skill,
                        skill_label=best[skill].node_label,
                        match_similarity=best[skill].similarity,
                        edge_weight=required[skill],
                        idf=round(self.idf[skill], 4),
                        contribution=profile[skill] * required[skill] * self.idf[skill] / norm,
                    )
                    for skill in profile if skill in required
                ),
                key=lambda c: -c.contribution,
            ))
            node = self.kg.node(career)
            recommendations.append(Recommendation(
                career_id=career,
                title=node['label'],
                domain=node['domain'],
                score=sum(c.contribution for c in contributions),
                contributions=contributions,
            ))

        recommendations.sort(key=lambda r: (-r.score, r.title))
        return matches, recommendations[:top_k]


@lru_cache(maxsize=1)
def get_ranker():
    kg = get_graph()
    return CareerRanker(kg, SkillMatcher(kg))


def main():
    parser = argparse.ArgumentParser(description='Rank careers for a list of skills.')
    parser.add_argument('skills', nargs='+', help='declared skills, e.g. Python "machine learning"')
    parser.add_argument('--top', type=int, default=10, help='number of careers to show')
    args = parser.parse_args()

    matches, recommendations = get_ranker().rank(args.skills, top_k=args.top)

    print('Matched skills')
    for m in matches:
        flag = '  (low confidence)' if m.low_confidence else ''
        print(f'  {m.query!r} -> {m.node_label} [{m.similarity:.2f}]{flag}')

    print('\nRecommended careers')
    if not recommendations:
        print('  (none)')
    for i, r in enumerate(recommendations, 1):
        print(f'{i:>3}. {r.title} ({r.domain})  score {r.score:.3f}')
        for c in r.contributions:
            print(f'       {c.skill_label}: +{c.contribution:.3f} '
                  f'(match {c.match_similarity:.2f}, weight {c.edge_weight:.2f}, idf {c.idf:.2f})')


if __name__ == '__main__':
    main()
