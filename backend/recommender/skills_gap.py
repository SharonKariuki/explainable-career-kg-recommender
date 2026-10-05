"""Skills gap: what a recommended career requires that the user did not declare.

The gap is every skill the career requires (an edge in the knowledge graph)
whose node none of the user's declared skills matched, ranked by

    priority = edge_weight ** 2 * idf

Squaring the edge weight lets how strongly the career needs a skill dominate,
so core requirements lead; IDF then demotes skills nearly every career needs
(Python, Microsoft Excel) in favour of ones distinctive to this career. With
edge_weight * idf instead, low-weight niche tools crowded the top (XLISP-STAT
and XGobi for Statisticians, ahead of Mathematics and Stata).

Each gap skill keeps its edge weight, IDF and the data sources of its edge,
so it can be traced to the graph and explained.
"""

from dataclasses import dataclass
from functools import lru_cache

from recommender.engine import get_engine

DEFAULT_LIMIT = 10


@dataclass(frozen=True)
class GapSkill:
    skill_id: str
    label: str
    skill_type: str
    edge_weight: float
    idf: float
    priority: float
    sources: tuple


class SkillsGapModule:
    def __init__(self, kg, idf):
        self.kg = kg
        self.idf = idf

    def gaps(self, recommendation, matches, limit=DEFAULT_LIMIT):
        """The career's required skills not matched by any declared skill, highest priority first."""
        have = {m.node_id for m in matches}
        career = recommendation.career_id
        items = []
        for skill, weight in self.kg.skills_of(career).items():
            if skill in have:
                continue
            node = self.kg.node(skill)
            idf = round(self.idf[skill], 4)  # stored rounded; priority uses the same value so it can be recomputed
            items.append(GapSkill(
                skill_id=skill,
                label=node['label'],
                skill_type=node['skill_type'],
                edge_weight=weight,
                idf=idf,
                priority=weight * weight * idf,
                sources=tuple(sorted(self.kg.graph.edges[career, skill]['sources'])),
            ))
        items.sort(key=lambda g: (-g.priority, g.label))
        return tuple(items[:limit]) if limit else tuple(items)


@lru_cache(maxsize=1)
def get_skills_gap():
    engine = get_engine()
    return SkillsGapModule(engine.kg, engine.idf)
