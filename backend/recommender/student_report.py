"""Career, sufficiency and M8 results on one students_v1 split (Measured Matching C4/C6, #160).

Every (profile, wording) is ranked once by the production engine with top_k=None; the evidence
rule (recommender.evidence, production thresholds) is applied to that ranking. Reported:

- career metrics (report only, AC16): P@1, Recall@3, MRR, nDCG@5 with cluster-bootstrap intervals,
  and wording agreement;
- sufficiency gates AC9 (insufficient recall) and AC10 (false insufficient): Kish-Wilson over
  (profile, wording) units clustered by profile, borderline excluded and also resolved each way;
  exploratory subgroups by reason code and for the mixed-profile family;
- M8 evidence contamination: gold-wrong selections (student_inputs labels) inside the best-supported
  career's support, and decision flips when they are removed.

The test split is read only inside open_test_sets(), which needs a clean working tree.

Usage (from backend/):
    python -m recommender.student_report --run NAME --split validation|test
"""

import argparse
import contextlib
import json
import sys
from collections import defaultdict

import pandas as pd

from recommender import evidence as ev
from recommender import student_eval as se
from recommender.eval_stats import kish_wilson


def gold_wrong(matches, labels):
    """Selected nodes the gold input labels reject (no_concept, or not in the acceptable set)."""
    wrong = set()
    for m in matches:
        gold = labels.get(' '.join(m.query.split()).casefold())
        if gold is not None and m.node_id not in gold['acceptable']:
            wrong.add(m.node_id)
    return wrong


def read_split(engine, profiles):
    """One unit per (profile, wording): the ranking, the evidence and the M8 quantities."""
    units = []
    for p in profiles:
        for w, wording in enumerate(p['wordings']):
            matches, ranked = engine.rank(list(wording), top_k=None)
            assessment = ev.assess(engine, matches, ranked)
            wrong = gold_wrong(matches, p.get('input_labels', {}))
            # M8b: the same ranking, with gold-wrong selections removed from the evidence only.
            without = ev.assess(engine, [m for m in matches if m.node_id not in wrong], ranked)
            units.append({'profile': p, 'wording': w, 'ranked': [r.career_id for r in ranked],
                          'insufficient': assessment['insufficient'], 'evidence': assessment['evidence'],
                          'support': assessment['evidence']['supporting_skills'], 'gold_wrong': sorted(wrong),
                          'insufficient_without_wrong': without['insufficient']})
    return units


def subgroup(units, include):
    """Exploratory share predicted insufficient among units whose profile matches `include`."""
    by = defaultdict(list)
    for u in units:
        if include(u['profile']):
            by[u['profile']['id']].append(u['insufficient'])
    return kish_wilson(by) if by else None


def report(units, profiles):
    cache = {(u['profile']['id'], tuple(u['profile']['wordings'][u['wording']])): u for u in units}
    lookup = {tuple(p['wordings'][w]): (p['id'], w) for p in profiles for w in range(len(p['wordings']))}
    insufficient_of = lambda skills: cache[(lookup[tuple(skills)][0], tuple(skills))]['insufficient']
    ranked_of = lambda skills: cache[(lookup[tuple(skills)][0], tuple(skills))]['ranked']

    # Career metrics need at least one relevant career; profiles graded 0 everywhere (soft skills only,
    # for example) are left out of them and counted.
    graded = [p for p in profiles if p['relevant']]
    rows = se.career_rows(graded, ranked_of)
    careers = se.summarise_careers(rows)
    gates = se.sufficiency(profiles, insufficient_of)
    reasons = {code: subgroup(units, lambda p, c=code: p['sufficiency'] == 'insufficient' and c in p['reasons'])
               for code in ('I1', 'I2', 'I3', 'I4', 'I5')}
    reasons['B1 (borderline, share flagged)'] = subgroup(units, lambda p: 'B1' in p['reasons'])
    reasons['mixed family, human sufficient (false insufficient)'] = subgroup(
        units, lambda p: p['family'] == 'mixed_ambiguous' and p['sufficiency'] == 'sufficient')
    m8 = se.evidence_contamination([{'profile': u['profile']['id'], 'support': u['support'],
                                     'gold_wrong': u['gold_wrong'], 'insufficient': u['insufficient'],
                                     'insufficient_without_wrong': u['insufficient_without_wrong']} for u in units])
    m8['profiles without any relevant career (not in career metrics)'] = len(profiles) - len(graded)
    return careers, se.wording_agreement(rows), gates, reasons, m8, rows


def main(argv=None):
    from recommender.engine import get_engine
    from recommender.evaluation import open_test_sets
    from recommender.graph import get_graph
    from recommender.results import configuration, parse_run, run_started, write_csv, write_manifest

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--run', required=True)
    parser.add_argument('--split', choices=('development', 'validation', 'test'), required=True)
    args = parser.parse_args(argv)
    folder = parse_run(__doc__.splitlines()[0], ['--run', args.run])
    started = run_started(__spec__.name, argv if argv is not None else sys.argv[1:])
    codes = {c.split(':')[1] for c in get_graph().careers()}
    opened = open_test_sets() if args.split == 'test' else contextlib.nullcontext()
    with opened:
        profiles = se.load_profiles(args.split, career_codes=codes)
    engine = get_engine()
    units = read_split(engine, profiles)
    careers, agreement, gates, reasons, m8, rows = report(units, profiles)

    def flat(name, est):
        return {'metric': name, **(vars(est) if hasattr(est, 'p') else {'value': est})}
    table = [flat(k, v) for k, v in gates.items() if k not in ('available',)]
    table += [flat(f'subgroup {k}', v) for k, v in reasons.items() if v is not None]
    table += [flat(k, v) for k, v in m8.items()]
    write_csv(pd.DataFrame(table).round(4), folder, 'sufficiency_metrics.csv')
    write_csv(pd.DataFrame(rows).round(4), folder, 'career_rows.csv')
    write_csv(pd.DataFrame([{'profile': u['profile']['id'], 'wording': u['wording'],
                             'human': u['profile']['sufficiency'], 'insufficient': u['insufficient'],
                             'supported_concepts': u['evidence']['supported_concepts'],
                             'meaningful_concepts': u['evidence']['meaningful_concepts'],
                             'reasons': ' '.join(u['evidence']['reasons'])} for u in units]),
              folder, 'sufficiency_units.csv')
    summary = {'careers': {k: {m: (v if not hasattr(v, '__dict__') else vars(v)) for m, v in r.items()}
                           for k, r in careers.items()},
               'wording agreement': vars(agreement) if hasattr(agreement, '__dict__') else agreement}
    (folder / 'careers.json').write_text(json.dumps(summary, indent=1, default=str), encoding='utf-8')
    write_manifest(folder, started, {f'students-v1-{args.split}': {'profiles': len(profiles), 'units': len(units)}},
                   {**configuration(None), 'evidence_thresholds': vars(ev.DEFAULT_PARAMS)})
    print(pd.DataFrame(table).round(4).to_string(index=False))
    print(json.dumps(summary, indent=1, default=str)[:3000])
    return 0


if __name__ == '__main__':
    sys.exit(main())
