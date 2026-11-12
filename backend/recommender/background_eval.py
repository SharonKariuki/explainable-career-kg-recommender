"""Choose and report the weight of the profile background (interests, studies, experience).

The synthetic skill profiles are paired with a background text: one O*NET
task statement from tasks-v1, read as the user's description of their work.

- matched: a task of the profile's own career (the background supports the label)
- mismatched: a task of a career the profile's career does not relate to at all
  (grade 0 in tasks-v1), so a misleading background can be measured

Selection rule, fixed before any result was seen: on the validation sets,
take the background weight with the highest matched nDCG@5 (clean and
unseen-wording validation averaged) among the weights whose mismatched MRR
stays within 0.05 of the skills-only MRR on both sets. Weight 0 is the
skills-only ranking, so it is always eligible.

    python -m recommender.background_eval --run NAME          # validation: choose the weight
    python -m recommender.background_eval --run NAME --test   # test, once, at DEFAULT_PARAMS.background_weight

Writes data/results/<run>/background.csv and manifest.json.
"""

import argparse
import random
import sys
from dataclasses import replace

import pandas as pd

from recommender import task_sets
from recommender.engine import DEFAULT_PARAMS
from recommender.evaluate import Systems, bootstrap_interval
from recommender.evaluation import (
    describe_sets, noisy_test, noisy_validation, open_test_sets, test_profiles, validation_profiles,
)
from recommender.graph import get_graph
from recommender.results import configuration, run_dir, run_started, write_csv, write_manifest
from recommender.validate import profile_metrics

WEIGHTS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
MISMATCH_TOLERANCE = 0.05
PAIRING_SEED = 11
MEASURES = ['p@1', 'r@3', 'mrr', 'ndcg@5']


def pair(profiles, tasks, matched, seed=PAIRING_SEED):
    """[(profile, background text)]: a task of the profile's career, or of an unrelated one."""
    by_career = {}
    for t in tasks:
        by_career.setdefault(t.career_id, []).append(t)
    rng = random.Random(seed)
    used = {career: 0 for career in by_career}
    pairs = []
    for p in profiles:
        if matched:
            options = by_career[p.career_id]
            task = options[used[p.career_id] % len(options)]
            used[p.career_id] += 1
        else:
            task = rng.choice([t for t in tasks if t.grades.get(p.career_id, 0) == 0])
        pairs.append((p, task.skills[0]))
    return pairs


def score_pairs(engine, dataset, pairing, pairs, weights):
    rows = []
    for p, background in pairs:
        prepared = engine.prepare(p.skills, background)
        for w in weights:
            ranked = [r.career_id for r in engine.score(prepared, replace(DEFAULT_PARAMS, background_weight=w))[1]]
            rows.append({'dataset': dataset, 'pairing': pairing, 'weight': w, 'profile_id': p.profile_id,
                         **profile_metrics(ranked, {p.career_id})})
    return rows


def summarise(rows):
    frame = pd.DataFrame(rows)
    out = []
    for (dataset, pairing, w), g in frame.groupby(['dataset', 'pairing', 'weight'], sort=False):
        row = {'dataset': dataset, 'pairing': pairing, 'weight': w, 'profiles': len(g), **g[MEASURES].mean().to_dict()}
        row['mrr_low'], row['mrr_high'] = bootstrap_interval(g['mrr'].tolist())
        out.append(row)
    return pd.DataFrame(out).round(4)


def choose(summary):
    """The selection rule in the module docstring; returns (weight, eligible weights)."""
    s = summary.set_index(['dataset', 'pairing', 'weight'])
    datasets = summary.dataset.unique()
    eligible = [w for w in WEIGHTS
                if all(s.loc[(d, 'mismatched', w), 'mrr'] >= s.loc[(d, 'mismatched', 0.0), 'mrr'] - MISMATCH_TOLERANCE
                       for d in datasets)]
    best = max(eligible, key=lambda w: (sum(s.loc[(d, 'matched', w), 'ndcg@5'] for d in datasets), -w))
    return best, eligible


def run(test, folder, started):
    kg = get_graph()
    if test:
        with open_test_sets():
            clean = test_profiles(kg)
            held, noisy = noisy_test(kg)
            tasks = task_sets.task_test_profiles()
        names, role, weights = ('synthetic-test', 'noisy-test', 'tasks-v1-test'), 'test', [0.0, DEFAULT_PARAMS.background_weight]
    else:
        clean = validation_profiles(kg)
        held, noisy = noisy_validation(kg)
        tasks = task_sets.task_validation_profiles()
        names, role, weights = ('synthetic-validation', 'noisy-validation', 'tasks-v1-validation'), 'validation', WEIGHTS

    plain, hidden = Systems(kg), Systems(kg, hidden_names=held.values())
    rows = []
    for dataset, engine, profiles in [(names[0], plain.engine, clean), (names[1], hidden.engine, noisy)]:
        for pairing in ('matched', 'mismatched'):
            rows += score_pairs(engine, dataset, pairing, pair(profiles, tasks, pairing == 'matched'), weights)
    summary = summarise(rows)

    results = write_csv(summary, folder, 'background.csv')
    write_manifest(folder, started,
                   describe_sets({names[0]: clean, names[1]: (held, noisy), names[2]: tasks},
                                 roles={n: role for n in names}),
                   configuration(DEFAULT_PARAMS))

    pd.set_option('display.width', 160)
    print(summary.drop(columns=['profiles']).to_string(index=False))
    if not test:
        best, eligible = choose(summary)
        print(f'\nEligible weights (mismatched MRR within {MISMATCH_TOLERANCE} of skills-only): {eligible}')
        print(f'Chosen background weight: {best}')
    print(f'\nResults: {results}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--run', required=True)
    parser.add_argument('--test', action='store_true', help='report the test sets at the chosen weight (once)')
    args = parser.parse_args(argv)
    try:
        folder = run_dir(args.run)
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))
    run(args.test, folder, run_started(__spec__.name, sys.argv[1:] if argv is None else argv))


if __name__ == '__main__':
    main()
