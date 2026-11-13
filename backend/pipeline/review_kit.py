"""Human review of the AI-produced gold labels (release readiness P5; Measured Matching Q2).

`sample` writes review sheets: a seeded, stratified sample of frozen gold labels with blank verdict
columns. Reviewers see the item and the gold label only, never AjiraGuide output. `score` reads the
completed sheets and reports, per sheet, how often reviewers accept the gold label, with a
Kish-Wilson interval (clustered by mapping group or profile) and the outcome against the
acceptance level fixed here before any review: lower bound >= 0.80 means the labels may be treated
as human-approved; otherwise the affected results stay provisional.

Usage (from backend/):
    python -m pipeline.review_kit sample --out DIR
    python -m pipeline.review_kit score --sheets DIR
"""

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from pipeline import DATA_DIR

SEED = 2027
MAPPING_PER_SPLIT_LABEL = 25        # per (split, label) cell; all items when a cell is smaller
PROFILES_PER_SPLIT_LABEL = 20       # per (split, sufficiency) cell
ACCEPT_LOWER_BOUND = 0.80
VERDICTS = ('agree', 'disagree', 'unsure')


def read(name):
    return json.loads((DATA_DIR / 'eval_sets' / name).read_text(encoding='utf-8'))


def stratified(records, key, per_cell, rng):
    cells = defaultdict(list)
    for r in records:
        cells[key(r)].append(r)
    chosen = []
    for cell in sorted(cells):
        members = sorted(cells[cell], key=lambda r: r['id'])
        chosen += rng.sample(members, min(per_cell, len(members)))
    rng.shuffle(chosen)
    return chosen


def sample(out):
    from recommender.graph import get_graph
    kg = get_graph()
    label = lambda node: kg.node(node)['label']
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    mapping = stratified(read('mapping_v1.json'), lambda i: (i['split'], i['label']), MAPPING_PER_SPLIT_LABEL, rng)
    with open(out / 'mapping_review.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['id', 'group', 'input', 'gold_label', 'gold_acceptable', 'verdict', 'reviewer', 'comment'])
        for i in mapping:
            w.writerow([i['id'], i['group'], i['input'], i['label'],
                        ' | '.join(label(n) for n in i['acceptable']), '', '', ''])
    profiles = stratified(read('students_v1.json'), lambda p: (p['split'], p['sufficiency']),
                          PROFILES_PER_SPLIT_LABEL, rng)
    titles = {c.split(':')[1]: kg.node(c)['label'] for c in kg.careers()}
    with open(out / 'profile_review.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['id', 'skills (wording 1)', 'skills (wording 2)', 'gold_sufficiency', 'gold_reasons',
                    'gold_grade_3_careers', 'sufficiency_verdict', 'grades_verdict', 'reviewer', 'comment'])
        for p in profiles:
            w.writerow([p['id'], '; '.join(p['wordings'][0]), '; '.join(p['wordings'][1]), p['sufficiency'],
                        ' '.join(p['reasons']), ' | '.join(titles[c] for c, g in p['relevant'].items() if g == 3),
                        '', '', '', ''])
    print(f'{len(mapping)} mapping items and {len(profiles)} profiles written to {out}')


def acceptance(rows, verdict_column, cluster_column):
    """Share of decided rows (agree or disagree) where the reviewer agrees, Kish-Wilson by cluster."""
    from recommender.eval_stats import kish_wilson, outcome
    by = defaultdict(list)
    undecided = 0
    for r in rows:
        v = r[verdict_column].strip().lower()
        if v not in VERDICTS:
            raise ValueError(f"{r['id']}: {verdict_column} must be one of {VERDICTS}, not {v!r}")
        if v == 'unsure':
            undecided += 1
            continue
        by[r[cluster_column]].append(v == 'agree')
    estimate = kish_wilson(by)
    return {'decided': sum(len(v) for v in by.values()), 'unsure': undecided, 'agree': estimate.p,
            'low': estimate.low, 'high': estimate.high,
            'outcome': outcome(estimate, ACCEPT_LOWER_BOUND, '>=')}


def score(sheets):
    sheets = Path(sheets)
    with open(sheets / 'mapping_review.csv', encoding='utf-8') as f:
        mapping = list(csv.DictReader(f))
    with open(sheets / 'profile_review.csv', encoding='utf-8') as f:
        profiles = list(csv.DictReader(f))
    report = {'mapping labels': acceptance(mapping, 'verdict', 'group'),
              'profile sufficiency': acceptance(profiles, 'sufficiency_verdict', 'id'),
              'profile career grades': acceptance(profiles, 'grades_verdict', 'id')}
    print(json.dumps(report, indent=1, default=str))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='step', required=True)
    sub.add_parser('sample').add_argument('--out', required=True)
    sub.add_parser('score').add_argument('--sheets', required=True)
    args = parser.parse_args(argv)
    sample(args.out) if args.step == 'sample' else score(args.sheets)
    return 0


if __name__ == '__main__':
    sys.exit(main())
