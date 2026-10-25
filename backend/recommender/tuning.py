"""Choose the engine's parameters on the validation profiles.

Grid: traversal depth, low-confidence threshold and weight, and every
combination of the three component weights in steps of 0.1 that sums to 1.
Each configuration is scored by mean reciprocal rank (MRR) of the correct
career over two validation sets of 360 profiles each: clean (names the
matcher knows) and unseen wording (names hidden from the matcher, so skills
must be recognised by meaning). Weights tuned on clean profiles alone leaned
too heavily on the graph for everyday wording. No test profiles are used.

Only the low-confidence settings change the components (through PageRank),
so each profile is scored once per low-confidence setting with every career
as a candidate; depth and weights are then applied to those stored
components, breaking ties by title as the engine does.

Writes data/results/<run>/tuning.csv (one row per configuration) and prints
the best configurations and the keyword baseline on the same profiles.

Usage (from backend/):
    python -m recommender.tuning --run NAME
"""

import itertools
import time

import numpy as np
import pandas as pd

from recommender.baseline import get_baseline
from recommender.engine import EngineParams, RecommendationEngine, get_engine
from recommender.evaluation import describe_sets, noisy_validation, reciprocal_rank, validation_profiles
from recommender.matching import SkillMatcher
from recommender.results import configuration, parse_run, run_started, write_csv, write_manifest

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


def score_set(engine, profiles):
    """Component tables for every low-confidence setting: {(threshold, weight): [table per profile]}."""
    prepared = [engine.prepare(p.skills) for p in profiles]
    return {
        (threshold, weight): [component_table(engine, pp, p.career_id, threshold, weight)
                              for pp, p in zip(prepared, profiles)]
        for threshold, weight in low_confidence_grid()
    }


def main(argv=None):
    run = parse_run(__doc__.splitlines()[0], argv)
    started = run_started(__spec__.name, argv)
    engine, baseline = get_engine(), get_baseline()
    kg = engine.kg
    held, noisy = noisy_validation(kg)
    clean = validation_profiles(kg)
    sets = {
        'clean': (engine, clean),
        'noisy': (RecommendationEngine(kg, SkillMatcher(kg, held.values())), noisy),
    }

    start = time.perf_counter()
    tables = {}
    for name, (set_engine, profiles) in sets.items():
        tables[name] = score_set(set_engine, profiles)
        print(f'{name} validation scored ({time.perf_counter() - start:.0f}s)')
    sizes = np.concatenate([[p.size for p in profiles] for _, profiles in sets.values()])

    rows = []
    for (threshold, lc_weight), weights, depth in itertools.product(low_confidence_grid(), weight_grid(), DEPTHS):
        rr = {}
        for name in sets:
            ranks = [rank_of_target(t, weights, depth) for t in tables[name][threshold, lc_weight]]
            rr[name] = np.array([1 / r if r else 0.0 for r in ranks])
        both = np.concatenate([rr[name] for name in sets])
        rows.append({
            'max_depth': depth, 'low_confidence_threshold': threshold, 'low_confidence_weight': lc_weight,
            'coverage_weight': weights[0], 'similarity_weight': weights[1], 'proximity_weight': weights[2],
            'mrr': both.mean(), **{f'mrr_{name}': rr[name].mean() for name in sets},
            **{f'mrr_size_{s}': both[sizes == s].mean() for s in sorted(set(sizes))},
        })

    results = pd.DataFrame(rows).sort_values('mrr', ascending=False).round(4)
    results_file = write_csv(results, run, 'tuning.csv')
    write_manifest(run, started, describe_sets({'synthetic-validation': clean, 'noisy-validation': (held, noisy)}),
                   configuration(None))  # a grid search: no single parameter set
    print(f'\n{len(results)} configurations -> {results_file}\n')
    print(results.head(10).to_string(index=False))

    for name, (_, profiles) in sets.items():
        rr = [reciprocal_rank([r.career_id for r in baseline.rank(p.skills, top_k=None)[1]], {p.career_id})
              for p in profiles]
        print(f'Keyword baseline, {name} validation: MRR {np.mean(rr):.3f}')


if __name__ == '__main__':
    main()
