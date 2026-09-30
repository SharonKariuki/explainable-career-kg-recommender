"""Choose the engine's parameters on the validation profiles.

Grid: traversal depth, low-confidence threshold and weight, and every
combination of the three component weights in steps of 0.1 that sums to 1.
Each configuration is scored by mean reciprocal rank (MRR) of the correct
career over the 360 validation profiles; the test profiles are not used, so
they stay unseen for the final evaluation.

Only the low-confidence settings change the components (through PageRank),
so each profile is scored once per low-confidence setting with every career
as a candidate; depth and weights are then applied to those stored
components, breaking ties by title as the engine does.

Writes data/results/tuning.csv (one row per configuration) and prints the
best configurations and the keyword baseline on the same profiles.

Usage (from backend/):
    python -m recommender.tuning
"""

import itertools
import time

import numpy as np
import pandas as pd

from pipeline import DATA_DIR
from recommender.baseline import get_baseline
from recommender.engine import EngineParams, get_engine
from recommender.evaluation import reciprocal_rank, validation_profiles

RESULTS_FILE = DATA_DIR / 'results' / 'tuning.csv'

DEPTHS = (1, 3)
LOW_CONFIDENCE_THRESHOLDS = (0.5, 0.6, 0.7)
LOW_CONFIDENCE_WEIGHTS = (0.0, 0.5, 1.0)
WEIGHT_STEPS = 10


def weight_grid():
    for c in range(WEIGHT_STEPS + 1):
        for s in range(WEIGHT_STEPS + 1 - c):
            yield c / WEIGHT_STEPS, s / WEIGHT_STEPS, (WEIGHT_STEPS - c - s) / WEIGHT_STEPS


def low_confidence_grid():
    # With full weight the threshold changes nothing, so it is scored once.
    for weight in LOW_CONFIDENCE_WEIGHTS:
        for threshold in (LOW_CONFIDENCE_THRESHOLDS if weight < 1 else LOW_CONFIDENCE_THRESHOLDS[1:2]):
            yield threshold, weight


def component_table(engine, prepared, target, threshold, weight):
    """Components of every candidate at depth 3, with a flag for depth-1 candidates."""
    params = EngineParams(max_depth=3, low_confidence_threshold=threshold, low_confidence_weight=weight)
    _, recommendations = engine.score(prepared, params)
    return {
        'components': np.array([
            [r.components.coverage, r.components.profile_similarity, r.components.graph_proximity]
            for r in recommendations
        ]),
        'direct': np.array([bool(r.skill_contributions) for r in recommendations]),
        'titles': [r.title for r in recommendations],
        'target': next((i for i, r in enumerate(recommendations) if r.career_id == target), None),
    }


def rank_of_target(table, weights, depth):
    """1-based rank of the correct career, or None if it is not a candidate."""
    target = table['target']
    if target is None or (depth == 1 and not table['direct'][target]):
        return None
    keep = table['direct'] if depth == 1 else np.ones(len(table['titles']), dtype=bool)
    scores = table['components'] @ np.array(weights)
    mine, title = scores[target], table['titles'][target]
    better = (scores > mine) | ((scores == mine) & (np.array(table['titles']) < title))
    return 1 + int((better & keep).sum())


def main():
    engine, baseline = get_engine(), get_baseline()
    profiles = validation_profiles(engine.kg)
    sizes = np.array([p.size for p in profiles])

    start = time.perf_counter()
    prepared = [engine.prepare(p.skills) for p in profiles]
    rows = []
    for threshold, lc_weight in low_confidence_grid():
        tables = [component_table(engine, pp, p.career_id, threshold, lc_weight) for pp, p in zip(prepared, profiles)]
        for weights, depth in itertools.product(weight_grid(), DEPTHS):
            ranks = [rank_of_target(t, weights, depth) for t in tables]
            rr = np.array([1 / r if r else 0.0 for r in ranks])
            hit3 = np.array([bool(r and r <= 3) for r in ranks])
            rows.append({
                'max_depth': depth, 'low_confidence_threshold': threshold, 'low_confidence_weight': lc_weight,
                'coverage_weight': weights[0], 'similarity_weight': weights[1], 'proximity_weight': weights[2],
                'mrr': rr.mean(), 'recall_at_3': hit3.mean(),
                **{f'mrr_size_{s}': rr[sizes == s].mean() for s in sorted(set(sizes))},
            })
        print(f'low-confidence threshold {threshold}, weight {lc_weight}: done ({time.perf_counter() - start:.0f}s)')

    results = pd.DataFrame(rows).sort_values(['mrr', 'recall_at_3'], ascending=False).round(4)
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(RESULTS_FILE, index=False)
    print(f'\n{len(results)} configurations -> {RESULTS_FILE}\n')
    print(results.head(10).to_string(index=False))

    rr = np.array([
        reciprocal_rank([r.career_id for r in baseline.rank(p.skills, top_k=None)[1]], {p.career_id})
        for p in profiles
    ])
    by_size = ', '.join(f'size {s}: {rr[sizes == s].mean():.3f}' for s in sorted(set(sizes)))
    print(f'\nKeyword baseline on the same profiles: MRR {rr.mean():.3f} ({by_size})')


if __name__ == '__main__':
    main()
