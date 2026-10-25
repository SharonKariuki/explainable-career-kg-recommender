"""Final evaluation: the full engine against the keyword baseline and two ablations.

Systems:
  keyword      exact or substring name matching, no embeddings, no graph
  sbert_only   careers ranked by ProfileSimilarity alone (no graph)
  graph_only   exact name matching into the graph, ranked by Coverage and
               GraphProximity (no embeddings)
  full         the engine as tuned

Profile sets, none used for tuning:
  test         360 synthetic profiles (validation's sibling, different seed)
  noisy        360 profiles written only with names hidden from the matcher
  hand         30 everyday-language profiles, each with 1-2 correct careers

Metrics: Precision@1, Precision@3, Recall@3, Recall@5 and MRR, overall and
by profile size, plus a 95% bootstrap interval for full minus keyword MRR.
Writes data/results/<run>/evaluation.csv.

Usage (from backend/):
    python -m recommender.evaluate --run NAME
"""

import random
import sys

import numpy as np
import pandas as pd

from recommender.baseline import KeywordBaseline
from recommender.engine import DEFAULT_PARAMS, EngineParams, PreparedProfile, RecommendationEngine
from recommender.evaluation import (
    LockedSetError, describe_sets, hand_written_profiles, matching_accuracy, noisy_test, open_test_sets, precision_at_k,
    recall_at_k, reciprocal_rank, test_profiles,
)
from recommender.graph import get_graph
from recommender.matching import SkillMatch, SkillMatcher
from recommender.results import configuration, parse_run, run_started, write_csv, write_manifest

SYSTEMS = ('keyword', 'sbert_only', 'graph_only', 'full')
BOOTSTRAP_SAMPLES = 2000

# Graph-only keeps the tuned graph weights and drops ProfileSimilarity.
_graph_total = DEFAULT_PARAMS.coverage_weight + DEFAULT_PARAMS.proximity_weight
GRAPH_ONLY = EngineParams(
    coverage_weight=DEFAULT_PARAMS.coverage_weight / _graph_total,
    similarity_weight=0.0,
    proximity_weight=DEFAULT_PARAMS.proximity_weight / _graph_total,
)


class Systems:
    """The four rankers, sharing one graph. `hidden_names` hides held-out names."""

    def __init__(self, kg, hidden_names=()):
        self.kg = kg
        matcher = SkillMatcher(kg, hidden_names)
        self.engine = RecommendationEngine(kg, matcher)
        self.baseline = KeywordBaseline(kg)
        self.exact = {}
        for text, node in zip(matcher.texts, matcher.node_ids):
            self.exact.setdefault(text.casefold(), node)
        self.careers = sorted(kg.careers())

    def rank(self, system, skills):
        if system == 'keyword':
            return [r.career_id for r in self.baseline.rank(skills, top_k=None)[1]]
        if system == 'full':
            return [r.career_id for r in self.engine.rank(skills, top_k=None)[1]]
        if system == 'sbert_only':
            vector = self.engine.prepare(skills).profile_vector
            if vector is None:
                return []
            scores = {c: float(self.engine.career_vectors[c] @ vector) for c in self.careers}
            return sorted(self.careers, key=lambda c: (-scores[c], c))
        if system == 'graph_only':
            matches = tuple(
                SkillMatch(q, self.exact[q.casefold()], self.kg.node(self.exact[q.casefold()])['label'], q, 1.0, False)
                for q in SkillMatcher.clean(skills) if q.casefold() in self.exact
            )
            prepared = PreparedProfile(matches=matches, profile_vector=np.zeros(384, dtype=np.float32))
            return [r.career_id for r in self.engine.score(prepared, GRAPH_ONLY)[1]]
        raise ValueError(system)


def metrics(ranked, relevant):
    return {
        'p@1': precision_at_k(ranked, relevant, 1),
        'p@3': precision_at_k(ranked, relevant, 3),
        'r@3': recall_at_k(ranked, relevant, 3),
        'r@5': recall_at_k(ranked, relevant, 5),
        'mrr': reciprocal_rank(ranked, relevant),
    }


def bootstrap_interval(differences, seed=0):
    rng = random.Random(seed)
    n = len(differences)
    means = sorted(sum(differences[rng.randrange(n)] for _ in range(n)) / n for _ in range(BOOTSTRAP_SAMPLES))
    return means[int(0.025 * BOOTSTRAP_SAMPLES)], means[int(0.975 * BOOTSTRAP_SAMPLES) - 1]


def evaluate(systems, dataset, profiles):
    """One row per (system, profile) with its metrics."""
    rows = []
    for p in profiles:
        relevant = getattr(p, 'relevant', None) or {p.career_id}
        size = getattr(p, 'size', None) or len(p.skills)
        for system in SYSTEMS:
            rows.append({'dataset': dataset, 'system': system, 'profile_id': p.profile_id, 'size': size,
                         **metrics(systems.rank(system, p.skills), relevant)})
    return rows


def main(argv=None):
    run = parse_run(__doc__.splitlines()[0], argv)
    started = run_started(__spec__.name, argv)
    kg = get_graph()
    with open_test_sets():  # refuses a dirty working tree; locked again on exit
        test = test_profiles(kg)
        held, noisy = noisy_test(kg)
    hand = hand_written_profiles(kg)
    plain, hidden = Systems(kg), Systems(kg, hidden_names=held.values())

    rows = (evaluate(plain, 'test', test)
            + evaluate(hidden, 'noisy', noisy)
            + evaluate(plain, 'hand', hand))
    per_profile = pd.DataFrame(rows)

    measures = ['p@1', 'p@3', 'r@3', 'r@5', 'mrr']
    overall = per_profile.groupby(['dataset', 'system'])[measures].mean().assign(size='all')
    by_size = per_profile[per_profile.dataset != 'hand'].groupby(['dataset', 'system', 'size'])[measures].mean()
    summary = pd.concat([overall.reset_index(), by_size.reset_index()]).round(4)
    summary['size'] = summary['size'].astype(str)
    summary = summary[['dataset', 'system', 'size', *measures]]
    results_file = write_csv(summary, run, 'evaluation.csv')
    write_manifest(run, started, describe_sets({'synthetic-test': test, 'noisy-test': (held, noisy), 'hand-v1': hand}),
                   configuration(DEFAULT_PARAMS))

    pd.set_option('display.width', 140)
    for dataset in ('test', 'noisy', 'hand'):
        table = summary[(summary.dataset == dataset) & (summary['size'] == 'all')].set_index('system').loc[list(SYSTEMS)]
        print(f'\n== {dataset} ({per_profile[per_profile.dataset == dataset].profile_id.nunique()} profiles)')
        print(table[measures].to_string())
        if dataset != 'hand':
            mrr = summary[(summary.dataset == dataset) & (summary['size'] != 'all')].pivot(
                index='size', columns='system', values='mrr')[list(SYSTEMS)]
            print('MRR by profile size:\n' + mrr.to_string())
        rr = per_profile[per_profile.dataset == dataset].pivot(index='profile_id', columns='system', values='mrr')
        low, high = bootstrap_interval((rr['full'] - rr['keyword']).tolist())
        print(f'full - keyword MRR: {(rr["full"] - rr["keyword"]).mean():+.3f} (95% CI {low:+.3f} to {high:+.3f})')
        if dataset != 'hand':
            sparse = per_profile[(per_profile.dataset == dataset) & (per_profile['size'] == 2)]
            sp = sparse.pivot(index='profile_id', columns='system', values='mrr')
            low, high = bootstrap_interval((sp['full'] - sp['keyword']).tolist())
            print(f'  on 2-skill profiles: {(sp["full"] - sp["keyword"]).mean():+.3f} (95% CI {low:+.3f} to {high:+.3f})')

    accuracy = matching_accuracy(hidden.engine.matcher, noisy, DEFAULT_PARAMS.low_confidence_threshold)
    print(f'\nMatching on held-out names: {accuracy["correct"]:.1%} correct; '
          f'{accuracy["correct_when_confident"]:.1%} above the threshold, '
          f'{accuracy["correct_when_uncertain"]:.1%} below it ({accuracy["uncertain_share"]:.1%} of skills)')
    print(f'\nResults: {results_file}')


if __name__ == '__main__':
    try:
        main()
    except LockedSetError as error:
        print(f'evaluate.py: error: {error}', file=sys.stderr)
        sys.exit(2)
