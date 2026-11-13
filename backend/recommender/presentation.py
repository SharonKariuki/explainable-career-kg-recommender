"""How confidently a recommendation may be presented (student-ready release, evidence safety).

The ranking's fit label ('strong', 'good', 'possible') comes from the score alone. On the gold
development split, 70% of profiles that humans judged to have too little evidence saw their top
career called a strong or good match. Evidence sufficiency cannot be classified reliably from the
graph (Measured Matching AC10, release study P2), so this module does something narrower and
safer: a recommendation keeps a strong or good label only when enough of the student's own
skills point *specifically* to that career; otherwise it is presented as a possible match, with
a sentence saying how much evidence there is. The ranking, the score and the `fit` field are
unchanged; the API adds `fit_shown` and `evidence_support`.

A skill counts as specific support for a career when its reading is confident (not flagged
uncertain), its similarity is at least MIN_SIMILARITY, the career requires it, and few careers
require it (at most `max_careers`), so generic skills such as Python, SQL or communication do
not count.

Thresholds are chosen on the students_v1 development split only, by a rule fixed before the
validation read: the setting with the lowest exposure, among those at or below 0.10, that keeps
the most strong or good labels on human-sufficient profiles.

Measures (Kish-Wilson over (profile, wording) units, clustered by profile):
  S1 exposure (gate): share of human-insufficient units whose top career is shown as a strong or
     good match. Target, fixed before the validation read: upper 95% bound <= 0.15.
  S2 kept (report): share of human-sufficient units shown strong or good by the score whose label
     is kept. No target; it is the cost of the rule.

Usage (from backend/):
    python -m recommender.presentation --run NAME --split development|validation
"""

import argparse
import itertools
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass

from recommender.explanation import fit_level

CONFIDENT_FITS = ('strong', 'good')
MIN_SIMILARITY = 0.60
EXPOSURE_TARGET_U = 0.15
DEV_EXPOSURE_CEILING = 0.10


@dataclass(frozen=True)
class PresentationParams:
    max_careers: int        # a skill required by more careers than this is generic, not specific support
    min_support: int        # specific skills needed to keep a strong or good label


# Chosen on development (data/results/student-ready-presentation-development).
DEFAULT_PARAMS = PresentationParams(max_careers=10, min_support=2)


def specific_support(kg, matches, recommendation, params=DEFAULT_PARAMS):
    """The student's confident, specific skills that this career requires."""
    best = {}
    for m in matches:
        if m.node_id not in best or m.similarity > best[m.node_id].similarity:
            best[m.node_id] = m
    required = {c.skill_id for c in recommendation.skill_contributions}
    return sorted(s for s, m in best.items()
                  if s in required and not m.uncertain and m.similarity >= MIN_SIMILARITY
                  and len(kg.careers_requiring(s)) <= params.max_careers)


def shown_fit(kg, matches, recommendation, params=DEFAULT_PARAMS):
    """(fit_shown, number of specific supporting skills)."""
    fit = fit_level(recommendation.score)
    support = len(specific_support(kg, matches, recommendation, params))
    if fit in CONFIDENT_FITS and support < params.min_support:
        return 'possible', support
    return fit, support


# ---- Evaluation ----

def evaluate(kg, units, params):
    """S1 and S2 for (human label, matches, ranked) units."""
    from recommender.eval_stats import kish_wilson
    exposure, kept = defaultdict(list), defaultdict(list)
    for profile_id, label, matches, ranked in units:
        if not ranked:
            continue
        top = ranked[0]
        fit, _ = shown_fit(kg, matches, top, params)
        if label == 'insufficient':
            exposure[profile_id].append(fit in CONFIDENT_FITS)
        elif label == 'sufficient' and fit_level(top.score) in CONFIDENT_FITS:
            kept[profile_id].append(fit in CONFIDENT_FITS)
    return kish_wilson(exposure), kish_wilson(kept)


def choose(rows):
    ok = [r for r in rows if r['S1 exposure'] <= DEV_EXPOSURE_CEILING]
    if not ok:
        return None
    return sorted(ok, key=lambda r: (-r['S2 kept'], r['S1 exposure'], r['max_careers']))[0]


def main(argv=None):
    import pandas as pd

    from recommender import student_eval as se
    from recommender.engine import get_engine
    from recommender.eval_stats import outcome
    from recommender.results import configuration, parse_run, run_started, write_csv, write_manifest

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--run', required=True)
    parser.add_argument('--split', choices=('development', 'validation'), required=True)
    args = parser.parse_args(argv)
    folder = parse_run(__doc__.splitlines()[0], ['--run', args.run])
    started = run_started(__spec__.name, argv if argv is not None else sys.argv[1:])
    engine = get_engine()
    profiles = [p for p in se.load_profiles(args.split) if p['sufficiency'] != 'borderline']
    units = []
    for p in profiles:
        for wording in p['wordings']:
            matches, ranked = engine.rank(list(wording), top_k=None)
            units.append((p['id'], p['sufficiency'], matches, ranked))
    if args.split == 'development':
        rows = []
        for max_careers, min_support in itertools.product((4, 6, 8, 10, 12, 14, 16, 20, 24), (1, 2, 3)):
            params = PresentationParams(max_careers, min_support)
            s1, s2 = evaluate(engine.kg, units, params)
            rows.append({**asdict(params), 'S1 exposure': s1.p, 'S1 high': s1.high, 'S2 kept': s2.p})
        best = choose(rows)
        write_csv(pd.DataFrame(rows).round(4), folder, 'presentation_grid.csv')
        summary = {'chosen': best, 'current DEFAULT_PARAMS': asdict(DEFAULT_PARAMS)}
    else:
        s1, s2 = evaluate(engine.kg, units, DEFAULT_PARAMS)
        summary = {'params': asdict(DEFAULT_PARAMS), 'S1 exposure': vars(s1), 'S2 kept': vars(s2),
                   'S1 outcome (U <= 0.15)': outcome(s1, EXPOSURE_TARGET_U, '<=')}
        write_csv(pd.DataFrame([{'measure': 'S1 exposure', **vars(s1)}, {'measure': 'S2 kept', **vars(s2)}]).round(4),
                  folder, 'presentation_metrics.csv')
    write_manifest(folder, started, {f'students-v1-{args.split}': {'profiles': len(profiles), 'units': len(units)}},
                   {**configuration(None), **{k: str(v) for k, v in summary.items()}})
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
