"""Choosing the evidence thresholds on the students_v1 development split (Measured Matching C4, #160).

Only the development split is read. Every grid point satisfies the plan's constraints (Q19):
w_min > ln(24) * 0.5, cap < W_min, G_min >= 2. Each (profile, wording) is ranked once with the
production engine; the thresholds are then applied to that fixed ranking, which they never change.

Choice rule (fixed before the run): among grid points whose development point estimates meet both
gate targets (insufficient recall >= 0.80, false-insufficient rate <= 0.10), take the one with the
highest balanced accuracy; when none meets both, take the highest balanced accuracy and report that
the targets were not met on development. Ties go to the simpler setting (smaller G_min, then larger
w_min, then smaller W_min). Borderline profiles are excluded, as in the gates.

Usage (from backend/):
    python -m recommender.evidence_calibration --run NAME [--allow-unfrozen]
"""

import argparse
import itertools
import json
import sys

import pandas as pd

from recommender import evidence as ev

RECALL_TARGET = 0.80
FALSE_TARGET = 0.10


def grid(raw_weights):
    """Constraint-satisfying settings. w_min sits just above each distinct concept weight."""
    levels = sorted({round(w, 4) for w in raw_weights if w > ev.NEVER_CORE_MAX})
    w_mins = [round(ev.NEVER_CORE_MAX + 1e-4, 4)] + [round(w + 1e-4, 4) for w in levels[:-1]]
    for w_min, G_min, W_min in itertools.product(w_mins, (2, 3), (3.5, 4.0, 4.5, 5.0, 6.0, 7.0)):
        for cap in (3.2, min(4.0, W_min - 0.01)):
            if cap < W_min and w_min <= cap:
                yield ev.EvidenceParams(w_min=w_min, cap=cap, W_min=W_min, G_min=G_min,
                                        epsilon=ev.DEFAULT_PARAMS.epsilon).check()


def score(units, params, engine):
    """Recall of insufficient and false-insufficient rate over (profile, wording) units."""
    tp = fn = fp = tn = 0
    for label, matches, ranked in units:
        predicted = ev.assess(engine, matches, ranked, params)['insufficient']
        if label == 'insufficient':
            tp += predicted; fn += not predicted
        else:
            fp += predicted; tn += not predicted
    recall = tp / (tp + fn) if tp + fn else 0.0
    false = fp / (fp + tn) if fp + tn else 0.0
    return {'recall': recall, 'false_insufficient': false, 'balanced_accuracy': (recall + 1 - false) / 2,
            'units': tp + fn + fp + tn}


def choose(frame):
    ok = frame[(frame.recall >= RECALL_TARGET) & (frame.false_insufficient <= FALSE_TARGET)]
    pool = ok if len(ok) else frame
    best = pool.sort_values(['balanced_accuracy', 'G_min', 'w_min', 'W_min'],
                            ascending=[False, True, False, True]).iloc[0]
    return best, bool(len(ok))


def main(argv=None):
    from recommender.engine import get_engine
    from recommender.results import configuration, parse_run, run_started, write_csv, write_manifest
    from recommender.student_eval import load_profiles

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--run', required=True)
    parser.add_argument('--allow-unfrozen', action='store_true')
    args = parser.parse_args(argv)
    folder = parse_run(__doc__.splitlines()[0], ['--run', args.run])
    started = run_started(__spec__.name, argv if argv is not None else sys.argv[1:])
    engine = get_engine()
    profiles = [p for p in load_profiles('development', allow_unfrozen=args.allow_unfrozen)
                if p['sufficiency'] != 'borderline']
    units = []
    for p in profiles:
        for wording in p['wordings']:
            matches, ranked = engine.rank(list(wording), top_k=None)
            units.append((p['sufficiency'], matches, ranked))
    rows = [{**vars(params), **score(units, params, engine)} for params in grid(ev.raw_weights(engine).values())]
    frame = pd.DataFrame(rows)
    best, met = choose(frame)
    write_csv(frame.round(4), folder, 'evidence_grid.csv')
    chosen = {k: (float(best[k]) if k != 'G_min' else int(best[k])) for k in ('w_min', 'cap', 'W_min', 'G_min', 'epsilon')}
    write_manifest(folder, started, {'students-v1-development': {'profiles': len(profiles), 'units': len(units)}},
                   {**configuration(None), 'chosen': chosen, 'targets_met_on_development': met})
    print(frame.sort_values('balanced_accuracy', ascending=False).head(15).round(4).to_string(index=False))
    print(json.dumps({'chosen': chosen, 'targets_met_on_development': met,
                      **{k: round(float(best[k]), 4) for k in ('recall', 'false_insufficient', 'balanced_accuracy')}}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
