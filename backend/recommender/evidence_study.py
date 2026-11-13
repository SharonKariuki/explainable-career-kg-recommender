"""Evidence-sufficiency redesign study on the students_v1 development split (release readiness, P2).

The approved rule (evidence-v1) marks most human-sufficient profiles insufficient (AC10 failed).
This study asks whether any graph-derived rule or model can meet the unchanged gate targets
(insufficient recall >= 0.80, false insufficient <= 0.10) on development data before a validation
read is spent. Only the development split is read. Three families are tried:

1. specificity rules: a confident reading counts when few careers require its node (df <= D) and
   its similarity is at least s_min; support is counted within one career or within one domain;
   insufficient when support < G;
2. the same with a minimum requirement weight;
3. a logistic model over those features, estimated by 5-fold cross-validation grouped by profile.

Usage (from backend/):
    python -m recommender.evidence_study --run NAME
"""

import argparse
import itertools
import json
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

from recommender.evidence import best_readings

RECALL_TARGET, FALSE_TARGET = 0.80, 0.10


def unit_features(kg, df, matches, ranked):
    best = best_readings(matches)
    domain = {c: kg.node(c)['domain'] for c in kg.careers()}

    def support(D, s_min, unit='career', r_min=0.0):
        good = {s for s, m in best.items() if m.similarity >= s_min and df[s] <= D}
        groups = defaultdict(set)
        for r in ranked:
            key = r.career_id if unit == 'career' else domain[r.career_id]
            groups[key] |= {c.skill_id for c in r.skill_contributions if c.skill_id in good
                            and (c.requirement_weight if c.requirement_weight is not None else c.edge_weight) >= r_min}
        return max((len(v) for v in groups.values()), default=0)

    sims = [m.similarity for m in matches] or [0.0]
    soft = sum(kg.node(m.node_id).get('skill_type') in ('transferable', 'essential') for m in matches)
    return support, [support(6, .5), support(12, .5), support(20, .5), support(12, .6), len(matches),
                     sum(m.similarity >= .6 for m in matches), sum(df[m.node_id] >= 20 for m in matches), soft,
                     float(np.mean(sims)), len(best)]


def rates(predicted, labels):
    predicted, labels = np.asarray(predicted, bool), np.asarray(labels, bool)
    return float((predicted & labels).sum() / labels.sum()), float((predicted & ~labels).sum() / (~labels).sum())


def main(argv=None):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold

    from recommender import student_eval as se
    from recommender.engine import get_engine
    from recommender.results import configuration, parse_run, run_started, write_csv, write_manifest

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--run', required=True)
    args = parser.parse_args(argv)
    folder = parse_run(__doc__.splitlines()[0], ['--run', args.run])
    started = run_started(__spec__.name, argv if argv is not None else sys.argv[1:])
    engine = get_engine()
    kg = engine.kg
    df = {s: len(kg.careers_requiring(s)) for s in kg.skills()}
    profiles = [p for p in se.load_profiles('development') if p['sufficiency'] != 'borderline']
    supports, features, labels, groups = [], [], [], []
    for p in profiles:
        for wording in p['wordings']:
            matches, ranked = engine.rank(list(wording), top_k=None)
            support, x = unit_features(kg, df, matches, ranked)
            supports.append(support)
            features.append(x)
            labels.append(p['sufficiency'] == 'insufficient')
            groups.append(p['id'])

    rows = []
    for D, s_min, G, unit, r_min in itertools.product((6, 8, 10, 12, 16, 20), (0.45, 0.5, 0.55, 0.6), (2, 3),
                                                      ('career', 'domain'), (0.0, 0.5)):
        recall, false = rates([s(D, s_min, unit, r_min) < G for s in supports], labels)
        rows.append({'family': 'rule', 'D': D, 's_min': s_min, 'G': G, 'unit': unit, 'r_min': r_min,
                     'recall': recall, 'false_insufficient': false})
    X, y, g = np.array(features, float), np.array(labels), np.array(groups)
    probability = np.zeros(len(y))
    for train, test in GroupKFold(5).split(X, y, g):
        model = LogisticRegression(max_iter=2000).fit(X[train], y[train])
        probability[test] = model.predict_proba(X[test])[:, 1]
    for threshold in np.round(np.arange(0.2, 0.85, 0.05), 2):
        recall, false = rates(probability >= threshold, y)
        rows.append({'family': 'logistic (grouped 5-fold CV)', 'threshold': float(threshold),
                     'recall': recall, 'false_insufficient': false})
    frame = pd.DataFrame(rows)
    feasible = frame[(frame.recall >= RECALL_TARGET) & (frame.false_insufficient <= FALSE_TARGET)]
    write_csv(frame.round(4), folder, 'evidence_study.csv')
    write_manifest(folder, started, {'students-v1-development': {'profiles': len(profiles), 'units': len(y)}},
                   {**configuration(None), 'feasible': len(feasible)})
    best = frame.assign(balanced=(frame.recall + 1 - frame.false_insufficient) / 2).sort_values('balanced', ascending=False)
    print(best.head(10).round(3).to_string(index=False))
    print(json.dumps({'settings meeting both targets on development': len(feasible)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
