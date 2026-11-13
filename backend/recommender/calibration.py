"""Choosing the close-runner-up margin δ (Measured Matching C3, #159; plan revision 2 §3.4).

δ is the largest value on a fixed grid that keeps, on development data only:
  - F_clean: false uncertainty on clean known-name inputs (synthetic validation; a flag whose only
    reason is shared_name is not counted, "M6-clean-excl") <= 0.05; and
  - F_unamb: false uncertainty on the gold development split, M6 on C* <= 0.15.
Rates are point estimates, as the plan states; their Kish-Wilson intervals are reported beside them.
The gold validation split is read once afterwards to confirm, and δ is never re-chosen on it.

Usage (from backend/):
    python -m recommender.calibration --run NAME
"""

import argparse
import json
import sys
from collections import defaultdict

import pandas as pd

from recommender import mapping_eval as me
from recommender.eval_stats import kish_wilson

F_CLEAN = 0.05
F_UNAMB = 0.15
GRID = tuple(round(0.001 * k, 3) for k in range(0, 101))   # 0.000 .. 0.100


def flagged_at(delta):
    """The matcher's flag with close_runner_up set at δ, recomputed from a reading."""
    def flagged(r):
        return bool(reasons_at(r, delta))
    return flagged


def reasons_at(r, delta):
    reasons = [x for x in r['reasons'] if x != 'close_runner_up']
    if delta and r['margin'] is not None and r['margin'] < delta:
        reasons.append('close_runner_up')
    return reasons


def clean_inputs(kg):
    """(text, intended node) for every distinct skill text in the synthetic validation profiles."""
    from recommender.evaluation import validation_profiles
    seen = {}
    for p in validation_profiles(kg):
        for text, node in zip(p.skills, p.skill_ids):
            seen.setdefault(text.casefold(), (text, node))
    return sorted(seen.values())


def clean_false_uncertainty(clean, readings, delta, exclude_shared_only=True):
    """M6-clean: share of correct clean readings that are flagged; each text is its own cluster."""
    units = {}
    for text, node in clean:
        r = readings[text]
        if r['node_id'] != node:
            continue
        reasons = reasons_at(r, delta)
        if exclude_shared_only and reasons == ['shared_name']:
            reasons = []
        units[text] = [bool(reasons)]
    return kish_wilson(units)


def curve(items, item_readings, clean, clean_readings, grid=GRID):
    rows = []
    for delta in grid:
        metrics, counts, _ = me.evaluate(items, item_readings, flagged=flagged_at(delta), delta=delta or None)
        clean_excl = clean_false_uncertainty(clean, clean_readings, delta)
        gate = metrics['M6 false uncertainty (gate, C*)']
        row = {'delta': delta, 'F_clean': clean_excl.p, 'F_clean_U': clean_excl.high, 'F_unamb': gate.p,
               'F_unamb_U': gate.high, 'M3': metrics['M3 ambiguous recall'].p,
               'M4': metrics['M4 no-concept recall'].p,
               'M7 primary': metrics['M7 confidently incorrect (primary)'].p}
        if 'M5 close-candidate recall' in metrics:
            close = metrics['M5 close-candidate recall']
            row.update({'M5 close n': close.n, 'M5 close recall': close.p})
        rows.append(row)
    return pd.DataFrame(rows)


def choose(frame):
    ok = frame[(frame.F_clean <= F_CLEAN) & (frame.F_unamb <= F_UNAMB)]
    return float(ok.delta.max()) if len(ok) else 0.0


def main(argv=None):
    from recommender.engine import get_engine
    from recommender.results import configuration, parse_run, run_started, write_csv, write_manifest

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--run', required=True)
    args = parser.parse_args(argv)
    folder = parse_run(__doc__.splitlines()[0], ['--run', args.run])
    started = run_started(__spec__.name, argv if argv is not None else sys.argv[1:])
    engine = get_engine()
    items = me.load_items('development', node_ids=set(engine.kg.skills()))
    item_readings = {r['query']: r for r in me.readings(engine.matcher, sorted({i['input'] for i in items}))}
    clean = clean_inputs(engine.kg)
    clean_readings = {r['query']: r for r in me.readings(engine.matcher, [t for t, _ in clean])}
    frame = curve(items, item_readings, clean, clean_readings)
    chosen = choose(frame)
    write_csv(frame.round(4), folder, 'delta_curve.csv')
    write_manifest(folder, started, {'mapping-v1-development': {'items': len(items)},
                                     'synthetic-validation clean inputs': {'texts': len(clean)}},
                   {**configuration(None), 'F_clean': F_CLEAN, 'F_unamb': F_UNAMB, 'chosen_delta': chosen})
    print(frame.round(4).to_string(index=False))
    print(json.dumps({'chosen_delta': chosen}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
