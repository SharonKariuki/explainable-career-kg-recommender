"""Career and evidence-sufficiency evaluation on independent student profiles (Measured Matching C1, #157).

Each profile in students_v1.json has two or more wordings of the same skills, graded career
relevance (3 primary, 2 also recommended, 1 related) and a human sufficiency label
(sufficient, insufficient or borderline). Two kinds of result, kept apart:

- Career metrics (report only): P@1 (grade >= 2), Recall@3 and MRR (grade >= 1) and nDCG@5,
  per (profile, wording). Wordings are averaged within a profile, then a cluster bootstrap over
  profiles gives the interval. Per-family results are always exploratory.
- Sufficiency (gates AC9, AC10 once C4 provides a predictor): Kish-Wilson proportions over
  (profile, wording) units clustered by profile, on adjudicated non-borderline profiles, and
  again with borderline counted each way.

Loading follows mapping_eval: frozen by sha256; an unfrozen development draft only with
allow_unfrozen; the test split only inside open_test_sets().
"""

import json
from collections import defaultdict
from itertools import combinations

from pipeline import DATA_DIR
from recommender.eval_stats import cluster_bootstrap, kish_wilson, mean_of_cluster_means
from recommender.evaluation import check_test_set, graded_metrics
from recommender.results import normalised_hash

STUDENTS_FILE = DATA_DIR / 'eval_sets' / 'students_v1.json'
FROZEN = {'students_v1.json': '49d0f88e26ff491bccff1df5e47bc6f3e557fe939208422d7ca8f47cdee7082a'}
SPLITS = ('development', 'validation', 'test')
SUFFICIENCY = ('sufficient', 'insufficient', 'borderline')
REASONS = ('I1', 'I2', 'I3', 'I4', 'I5', 'B1')
CAREER_METRICS = ('p@1', 'r@3', 'mrr', 'ndcg@5')


class UnfrozenSetError(RuntimeError):
    pass


def validate_profiles(profiles, career_codes):
    problems, seen = [], set()
    for k, p in enumerate(profiles):
        where = p.get('id', f'#{k}')
        for field in ('id', 'family', 'split', 'wordings', 'relevant', 'sufficiency'):
            if field not in p:
                problems.append(f'{where}: missing {field}')
        if p.get('id') in seen:
            problems.append(f'{where}: duplicate id')
        seen.add(p.get('id'))
        if p.get('split') not in SPLITS:
            problems.append(f'{where}: split must be one of {SPLITS}')
        if p.get('sufficiency') not in SUFFICIENCY:
            problems.append(f'{where}: sufficiency must be one of {SUFFICIENCY}')
        if len(p.get('wordings', [])) < 2:
            problems.append(f'{where}: needs at least two wordings')
        bad = {c: g for c, g in p.get('relevant', {}).items() if c not in career_codes or g not in (1, 2, 3)}
        if bad:
            problems.append(f'{where}: invalid grades {bad}')
        unknown = [r for r in p.get('reasons', []) if r not in REASONS]
        if unknown:
            problems.append(f'{where}: unknown reason codes {unknown}')
    return problems


def load_profiles(split, path=STUDENTS_FILE, allow_unfrozen=False, career_codes=None):
    if split not in SPLITS:
        raise ValueError(f'split must be one of {SPLITS}')
    if split == 'test':
        check_test_set('students-v1-test')
    expected = FROZEN.get(path.name)
    if expected is None:
        if not (allow_unfrozen and split == 'development'):
            raise UnfrozenSetError(f'{path.name} is not frozen; only its development split can be read, '
                                   'with allow_unfrozen')
    elif normalised_hash(path) != expected:
        raise UnfrozenSetError(f'{path.name} no longer matches its frozen sha256')
    profiles = json.loads(path.read_text(encoding='utf-8'))
    if career_codes is not None:
        problems = validate_profiles(profiles, career_codes)
        if problems:
            raise ValueError(f'{len(problems)} problems in {path.name}: ' + '; '.join(problems[:5]))
    return [p for p in profiles if p['split'] == split]


# ---- Career metrics ----

def career_rows(profiles, rank, n_careers=24):
    """One row per (profile, wording). `rank(skills)` returns career ids, best first."""
    rows = []
    for p in profiles:
        grades = {f'career:{c}': g for c, g in p['relevant'].items()}
        for w, skills in enumerate(p['wordings']):
            ranked = rank(list(skills))
            m = graded_metrics(ranked, grades, n_careers)
            rows.append({'profile': p['id'], 'family': p['family'], 'wording': w,
                         'first': ranked[0] if ranked else None, **{k: m[k] for k in CAREER_METRICS}})
    return rows


def summarise_careers(rows, by=None):
    """Point estimate and cluster-bootstrap interval per metric (clusters = profiles)."""
    groups = defaultdict(list)
    for r in rows:
        groups[r[by] if by else 'all'].append(r)
    out = {}
    for name, group in groups.items():
        profiles = {r['profile'] for r in group}
        result = {'profiles': len(profiles), 'units': len(group),
                  'status': 'reliable' if len(profiles) >= 60 and not by else 'exploratory'}
        for metric in CAREER_METRICS:
            values = defaultdict(list)
            for r in group:
                values[r['profile']].append(r[metric])
            result[metric] = cluster_bootstrap(values, mean_of_cluster_means)
        out[name] = result
    return out


def wording_agreement(rows):
    """Per profile, the share of wording pairs ranking the same first career; then bootstrapped."""
    firsts = defaultdict(list)
    for r in rows:
        firsts[r['profile']].append(r['first'])
    per_profile = {pid: [float(a == b) for a, b in combinations(f, 2)] for pid, f in firsts.items() if len(f) >= 2}
    return cluster_bootstrap(per_profile, mean_of_cluster_means)


# ---- Sufficiency ----

def sufficiency(profiles, predict_insufficient=None):
    """Gate quantities for AC9 and AC10. Without a predictor (before C4) nothing is computed."""
    if predict_insufficient is None:
        return {'available': False, 'reason': 'evidence sufficiency is implemented in C4'}
    units = [(p, w, bool(predict_insufficient(list(s)))) for p in profiles for w, s in enumerate(p['wordings'])]

    def estimate(label_of, want):
        """Share of units predicted insufficient among profiles whose (resolved) label is `want`:
        recall when want is 'insufficient' (AC9), false-insufficient rate when 'sufficient' (AC10)."""
        by_profile = defaultdict(list)
        for p, _, predicted_insufficient in units:
            if label_of(p) == want:
                by_profile[p['id']].append(predicted_insufficient)
        return kish_wilson(by_profile)

    adjudicated = lambda p: p['sufficiency']
    as_sufficient = lambda p: 'sufficient' if p['sufficiency'] == 'borderline' else p['sufficiency']
    as_insufficient = lambda p: 'insufficient' if p['sufficiency'] == 'borderline' else p['sufficiency']
    return {
        'available': True,
        'borderline_profiles': sum(p['sufficiency'] == 'borderline' for p in profiles),
        'AC9 insufficient recall': estimate(adjudicated, 'insufficient'),
        'AC10 false insufficient': estimate(adjudicated, 'sufficient'),
        'AC9 with borderline as insufficient': estimate(as_insufficient, 'insufficient'),
        'AC10 with borderline as sufficient': estimate(as_sufficient, 'sufficient'),
    }


# ---- M8: evidence contamination (needs C4's supporting concepts) ----

def evidence_contamination(units):
    """M8a-c from per-unit evidence. Each unit: profile id, the supporting concepts, the
    insufficient decision with and without gold-wrong concepts, and the gold-wrong concepts."""
    contaminated = defaultdict(list)
    flips = defaultdict(list)
    wrong_meaningful = 0
    for u in units:
        bad = set(u['support']) & set(u['gold_wrong'])
        contaminated[u['profile']].append(bool(bad))
        flips[u['profile']].append(u['insufficient'] != u['insufficient_without_wrong'])
        wrong_meaningful += len(bad)
    return {'M8a contamination': kish_wilson(contaminated), 'M8b decision flips': kish_wilson(flips),
            'M8c wrong but meaningful (count)': wrong_meaningful}
