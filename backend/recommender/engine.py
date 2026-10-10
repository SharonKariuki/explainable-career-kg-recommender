"""Recommendation engine: rank careers for a declared skill profile.

Each declared skill is matched to a graph skill node (SkillMatcher). Candidate
careers are those within `max_depth` hops of a matched skill (breadth-first
traversal), and each candidate is scored

    score = coverage_weight * Coverage
          + similarity_weight * ProfileSimilarity
          + proximity_weight * GraphProximity

with every component in 0-1:

- Coverage: the share of the profile the career requires. Each matched skill
  counts by its IDF (so skills every career needs, like Python, count least),
  scaled by how well it matched and how strongly the career requires it.
- ProfileSimilarity: cosine between the mean SBERT embedding of the declared
  skills and the embedding of the career's O*NET title and description. It
  uses no graph structure.
- GraphProximity: personalised PageRank, a random walk over the graph that
  restarts at the matched skills (weighted by match strength and IDF). A
  career's visit probability is divided by its total edge weight, since
  careers with many skills would otherwise attract the walk regardless of
  the profile, and scaled so the closest career scores 1. It rewards careers
  that are well connected to the profile through shared skills and careers,
  even when they do not require the declared skills directly.

A match below `low_confidence_threshold` keeps its nearest skill node but
counts at `low_confidence_weight` of its similarity. Every recommendation
stores its components and the skills behind them, which is what the
explanation module reads.
"""

import math
from dataclasses import dataclass, replace
from functools import lru_cache

import networkx as nx
import numpy as np

from pipeline.embeddings import encode, get_model, load_embeddings
from recommender.graph import get_graph
from recommender.matching import LOW_CONFIDENCE_THRESHOLD, SkillMatcher

PAGERANK_DAMPING = 0.85


@dataclass(frozen=True)
class EngineParams:
    """Defaults chosen by `python -m recommender.tuning` on clean and
    unseen-wording validation profiles (combined MRR 0.608).

    Depth 3 and threshold 0.70 scored within 0.002 of these, which is noise;
    depth 1 keeps every recommendation tied to a declared skill, and 0.60 is
    the threshold the held-out matching results support.
    """
    max_depth: int = 1
    low_confidence_threshold: float = LOW_CONFIDENCE_THRESHOLD
    low_confidence_weight: float = 0.5
    coverage_weight: float = 0.7
    similarity_weight: float = 0.1
    proximity_weight: float = 0.2


DEFAULT_PARAMS = EngineParams()


@dataclass(frozen=True)
class ScoreComponents:
    coverage: float
    profile_similarity: float
    graph_proximity: float


@dataclass(frozen=True)
class SkillContribution:
    """A declared skill the career requires, and its share of Coverage."""
    query: str
    skill_id: str
    skill_label: str
    match_similarity: float
    low_confidence: bool
    edge_weight: float
    idf: float
    coverage_share: float


@dataclass(frozen=True)
class ProximityPath:
    """A required skill through which the random walk reaches the career."""
    skill_id: str
    skill_label: str
    share: float


@dataclass(frozen=True)
class Recommendation:
    career_id: str
    title: str
    domain: str
    score: float
    components: ScoreComponents
    skill_contributions: tuple
    proximity_paths: tuple


@dataclass(frozen=True)
class PreparedProfile:
    matches: tuple
    profile_vector: np.ndarray


class RecommendationEngine:
    def __init__(self, kg, matcher):
        self.kg = kg
        self.matcher = matcher
        self.careers = sorted(kg.careers())
        self.idf = {s: math.log(len(self.careers) / len(kg.careers_requiring(s))) + 1 for s in kg.skills()}
        self.strength = dict(kg.graph.degree(weight='weight'))

        texts = {c: f"{kg.node(c)['label']}. {kg.node(c)['description']}" for c in self.careers}
        vectors = load_embeddings(texts.values())
        self.career_vectors = {c: vectors[t] for c, t in texts.items()}

    def prepare(self, skills):
        """Encode and match a profile once, so it can be scored under many parameter sets."""
        queries = self.matcher.clean(skills)
        if not queries:
            return PreparedProfile(matches=(), profile_vector=None)
        vectors = encode(queries)
        mean = vectors.mean(axis=0)
        return PreparedProfile(
            matches=tuple(self.matcher.match_encoded(queries, vectors)),
            profile_vector=mean / np.linalg.norm(mean),
        )

    def rank(self, skills, top_k=10, params=DEFAULT_PARAMS):
        """Return (matches, recommendations) for a list of declared skills."""
        return self.score(self.prepare(skills), params, top_k)

    def score(self, prepared, params=DEFAULT_PARAMS, top_k=None):
        matches = tuple(
            replace(m, low_confidence=m.similarity < params.low_confidence_threshold) for m in prepared.matches
        )
        # A skill node matched by several declared skills keeps its best match.
        best = {}
        for m in matches:
            if m.node_id not in best or m.similarity > best[m.node_id].similarity:
                best[m.node_id] = m
        if not best:
            return matches, []
        strength = {
            node: m.similarity * (params.low_confidence_weight if m.low_confidence else 1.0)
            for node, m in best.items()
        }
        visits = self.random_walk(strength)
        proximity = self.proximity(visits)
        profile_idf = sum(self.idf[node] for node in best)

        reached = self.kg.traverse(best, params.max_depth)
        candidates = [n for n, d in reached.items() if d > 0 and self.kg.node(n)['kind'] == 'career']

        recommendations = []
        for career in candidates:
            required = self.kg.skills_of(career)
            contributions = tuple(sorted(
                (
                    SkillContribution(
                        query=best[s].query, skill_id=s, skill_label=best[s].node_label,
                        match_similarity=best[s].similarity, low_confidence=best[s].low_confidence,
                        edge_weight=required[s], idf=round(self.idf[s], 4),
                        coverage_share=strength[s] * self.idf[s] * required[s] / profile_idf,
                    )
                    for s in best if s in required
                ),
                key=lambda c: -c.coverage_share,
            ))
            components = ScoreComponents(
                coverage=sum(c.coverage_share for c in contributions),
                profile_similarity=max(0.0, float(self.career_vectors[career] @ prepared.profile_vector)),
                graph_proximity=proximity[career],
            )
            node = self.kg.node(career)
            recommendations.append(Recommendation(
                career_id=career,
                title=node['label'],
                domain=node['domain'],
                score=(params.coverage_weight * components.coverage
                       + params.similarity_weight * components.profile_similarity
                       + params.proximity_weight * components.graph_proximity),
                components=components,
                skill_contributions=contributions,
                proximity_paths=self.proximity_paths(career, visits),
            ))

        recommendations.sort(key=lambda r: (-r.score, r.title))
        return matches, recommendations[:top_k] if top_k else recommendations

    def random_walk(self, strength):
        """Visit probabilities, or None when no matched skill carries any weight
        (every match uncertain with low_confidence_weight 0): nothing to walk from."""
        restart = {node: s * self.idf[node] for node, s in strength.items()}
        if not any(restart.values()):
            return None
        return nx.pagerank(self.kg.graph, alpha=PAGERANK_DAMPING, personalization=restart, weight='weight', tol=1e-8)

    def proximity(self, visits):
        if visits is None:
            return {c: 0.0 for c in self.careers}
        raw = {c: visits[c] / self.strength[c] for c in self.careers}
        top = max(raw.values())
        return {c: v / top if top else 0.0 for c, v in raw.items()}

    def proximity_paths(self, career, visits, limit=3):
        """The skills the walk mostly arrives through; shares of the career's visits."""
        if visits is None:
            return ()
        inflow = {
            skill: visits[skill] * weight / self.strength[skill]
            for skill, weight in self.kg.skills_of(career).items()
        }
        total = sum(inflow.values())
        top = sorted(inflow, key=lambda s: -inflow[s])[:limit]
        return tuple(ProximityPath(s, self.kg.node(s)['label'], inflow[s] / total) for s in top)


@lru_cache(maxsize=1)
def get_engine():
    """The shared engine. Loads the graph and the SBERT model up front (about 20s),
    so later calls rank in well under a second."""
    kg = get_graph()
    get_model()
    return RecommendationEngine(kg, SkillMatcher(kg))
