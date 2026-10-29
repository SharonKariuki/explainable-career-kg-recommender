"""Measure the current configuration on validation and development sets only.

For baseline checks and model selection (docs/evaluation_protocol.md); it
never loads a test set. Per set and system: Precision@1, Precision@3,
Recall@3, MRR, nDCG@3, nDCG@5 and candidate rate, with 95% bootstrap
intervals for P@1 and nDCG@5, followed by the regression probes
(recommender/probes.py).

With one correct career per profile, Precision@3 is at most 1/3, so P@1 is
the precision figure to compare against a target.

Once tasks-v1 is frozen, its validation split is also scored and written to graded.csv:
Precision@1 at grade >= 2 beside grade 3 only, with the grade-2 disclosure.

Writes data/results/<run>/validation.csv, probes.csv and manifest.json (and graded.csv).

Usage (from backend/):
    python -m recommender.validate --run NAME
"""

import pandas as pd

from recommender import task_sets
from recommender.engine import DEFAULT_PARAMS
from recommender.evaluate import SYSTEMS, Systems, bootstrap_interval, evaluate_graded, graded_report, print_graded
from recommender.evaluation import (
    describe_sets, hand_written_profiles, ndcg_at_k, noisy_validation, precision_at_k, recall_at_k, reciprocal_rank,
    validation_profiles,
)
from recommender.graph import get_graph
from recommender.probes import run_probes
from recommender.results import configuration, parse_run, run_started, write_csv, write_manifest

MEASURES = ['p@1', 'p@3', 'r@3', 'mrr', 'ndcg@3', 'ndcg@5', 'candidate_rate']
INTERVALS = ['p@1', 'ndcg@5']


def profile_metrics(ranked, relevant):
    grades = {career: 1 for career in relevant}
    return {
        'p@1': precision_at_k(ranked, relevant, 1),
        'p@3': precision_at_k(ranked, relevant, 3),
        'r@3': recall_at_k(ranked, relevant, 3),
        'mrr': reciprocal_rank(ranked, relevant),
        'ndcg@3': ndcg_at_k(ranked, grades, 3),
        'ndcg@5': ndcg_at_k(ranked, grades, 5),
        'candidate_rate': float(bool(ranked)),
    }


def summarise(rows):
    per_profile = pd.DataFrame(rows)
    summary = []
    for (dataset, role, system), group in per_profile.groupby(['dataset', 'role', 'system'], sort=False):
        row = {'dataset': dataset, 'role': role, 'system': system, 'profiles': len(group),
               **group[MEASURES].mean().to_dict()}
        for measure in INTERVALS:
            row[f'{measure}_low'], row[f'{measure}_high'] = bootstrap_interval(group[measure].tolist())
        summary.append(row)
    return pd.DataFrame(summary).round(4)


def main(argv=None):
    run = parse_run(__doc__.splitlines()[0], argv)
    started = run_started(__spec__.name, argv)
    kg = get_graph()
    clean = validation_profiles(kg)
    held, noisy = noisy_validation(kg)
    hand = hand_written_profiles(kg)
    graded = {'tasks-v1-validation': task_sets.task_validation_profiles()} if task_sets.is_frozen() else {}
    plain, hidden = Systems(kg), Systems(kg, hidden_names=held.values())

    rows = []
    for dataset, role, systems, profiles in [('synthetic-validation', 'validation', plain, clean),
                                             ('noisy-validation', 'validation', hidden, noisy),
                                             ('hand-v1', 'development', plain, hand)]:
        for p in profiles:
            relevant = getattr(p, 'relevant', None) or {p.career_id}
            for system in SYSTEMS:
                rows.append({'dataset': dataset, 'role': role, 'system': system,
                             **profile_metrics(systems.rank(system, p.skills), relevant)})
    summary = summarise(rows)
    probes = pd.DataFrame([vars(r) for r in run_probes(plain.engine)])

    graded_rows = [r for name, profiles in graded.items() for r in evaluate_graded(plain, name, 'validation', profiles)]
    graded_table = graded_report(graded_rows) if graded_rows else None

    results_file = write_csv(summary, run, 'validation.csv')
    write_csv(probes, run, 'probes.csv')
    if graded_table is not None:
        write_csv(graded_table, run, 'graded.csv')
    write_manifest(run, started, describe_sets({'synthetic-validation': clean, 'noisy-validation': (held, noisy),
                                                'hand-v1': hand, **graded},
                                               roles={name: 'validation' for name in graded}),
                   configuration(DEFAULT_PARAMS))

    pd.set_option('display.width', 160)
    for dataset in summary.dataset.unique():
        table = summary[summary.dataset == dataset].set_index('system')
        print(f'\n== {dataset} ({table.role.iloc[0]}, {table.profiles.iloc[0]} profiles)')
        print(table[MEASURES].to_string())
        full = table.loc['full']
        print(f"full: P@1 {full['p@1']:.3f} (95% CI {full['p@1_low']:.3f}-{full['p@1_high']:.3f}), "
              f"nDCG@5 {full['ndcg@5']:.3f} (95% CI {full['ndcg@5_low']:.3f}-{full['ndcg@5_high']:.3f})")
    if graded_table is not None:
        print_graded(graded_table)
    else:
        print('\ntasks-v1 is not frozen: graded validation reporting skipped')
    print(f'\nRegression probes: {probes.passed.sum()} of {len(probes)} pass')
    for r in probes.itertuples():
        print(f"  {'PASS' if r.passed else 'FAIL'}  {r.name}: {r.observed}")
    print(f'\nResults: {results_file}')


if __name__ == '__main__':
    main()
