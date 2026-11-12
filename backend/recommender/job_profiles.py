"""Job-posting profiles: does each career come first for the skills employers ask for?

data/eval_sets/job_skills.json lists, for each of the 24 careers, the skills
job postings and career guides ask for. It was researched from sources other
than O*NET and ESCO (each entry records them), so it checks the system against
an outside view of the jobs rather than against its own data. It is a
development set: it may guide changes, and the locked test sets judge them.

Each career gives several profiles, from rich to sparse:

- full: its core and common skills
- core: the core skills only
- core-3 (three draws): three core skills, the cold-start case
- with-soft: four core skills plus its soft skills
- everyday: three short phrases a student might type

data/eval_sets/job_check.json is the held-out check: two real postings per
career, in their own wording (posting-a, posting-b), and a short student CV
(student), researched separately and not looked at until the matching changes
it checks were fixed. Run it with --check.

    python -m recommender.job_profiles --run NAME [--check]

writes job_profiles.csv (one row per profile), job_summary.csv (per variant)
and job_unmatched.csv (declared skills that matched nothing closely).
"""

import json
import random
import sys

import pandas as pd

from pipeline import DATA_DIR
from recommender.engine import DEFAULT_PARAMS, get_engine
from recommender.evaluation import describe_sets, hit_at_k, reciprocal_rank
from recommender.results import configuration, parse_run, run_started, write_csv, write_manifest

JOB_SKILLS = DATA_DIR / 'eval_sets' / 'job_skills.json'
JOB_CHECK = DATA_DIR / 'eval_sets' / 'job_check.json'
CHECK_VARIANTS = ('posting_a', 'posting_b', 'student')
DRAW_SEED = 7
COLD_START_DRAWS = 3


def load_jobs(path=JOB_SKILLS):
    return json.loads(path.read_text(encoding='utf-8'))


def job_profiles(jobs, seed=DRAW_SEED):
    """(code, variant, skills) for every career, in a fixed order."""
    rng = random.Random(seed)
    profiles = []
    for code in sorted(jobs):
        job = jobs[code]
        core = list(job['core'])
        profiles.append((code, 'full', core + list(job['common'])))
        profiles.append((code, 'core', core))
        for draw in range(COLD_START_DRAWS):
            profiles.append((code, f'core-3 #{draw + 1}', rng.sample(core, 3)))
        profiles.append((code, 'with-soft', core[:4] + list(job['soft'])))
        profiles.append((code, 'everyday', list(job['everyday'])))
    return profiles


def check_profiles(jobs):
    """(code, variant, skills) for the held-out check set."""
    return [(code, variant.replace('_', '-'), list(jobs[code][variant]))
            for code in sorted(jobs) for variant in CHECK_VARIANTS]


def career_code(career_id):
    return career_id.split(':', 1)[-1]


def run(jobs, profiles, engine=None, params=DEFAULT_PARAMS):
    engine = engine or get_engine()
    rows, unmatched = [], []
    for code, variant, skills in profiles:
        matches, ranked = engine.rank(skills, top_k=None, params=params)
        order = [career_code(r.career_id) for r in ranked]
        relevant = {code}
        rows.append({
            'career': jobs[code]['title'], 'code': code, 'variant': variant, 'skills': '; '.join(skills),
            'rank': order.index(code) + 1 if code in order else None,
            'rr': reciprocal_rank(order, relevant), 'hit@1': hit_at_k(order, relevant, 1),
            'hit@3': hit_at_k(order, relevant, 3), 'top3': '; '.join(r.title for r in ranked[:3]),
            'uncertain': sum(m.low_confidence for m in matches),
        })
        unmatched += [{'skill': m.query, 'nearest': m.node_label, 'similarity': m.similarity, 'career': jobs[code]['title']}
                      for m in matches if m.low_confidence]
    rows = pd.DataFrame(rows)
    summary = (rows.assign(variant=rows.variant.str.replace(r' #\d', '', regex=True))
               .groupby('variant')[['rr', 'hit@1', 'hit@3']].mean()
               .rename(columns={'rr': 'MRR'}))
    summary.loc['all'] = rows[['rr', 'hit@1', 'hit@3']].mean().rename({'rr': 'MRR'})
    unmatched = pd.DataFrame(unmatched, columns=['skill', 'nearest', 'similarity', 'career']).drop_duplicates('skill')
    return rows, summary.round(3).reset_index(), unmatched


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    check = '--check' in args
    folder = parse_run(__doc__.splitlines()[0], [a for a in args if a != '--check'])
    started = run_started(__spec__.name, args)
    jobs = load_jobs(JOB_CHECK if check else JOB_SKILLS)
    profiles = check_profiles(jobs) if check else job_profiles(jobs)
    rows, summary, unmatched = run(jobs, profiles)
    write_csv(rows, folder, 'job_profiles.csv')
    write_csv(summary, folder, 'job_summary.csv')
    write_csv(unmatched.sort_values('similarity'), folder, 'job_unmatched.csv')
    name = 'job-check' if check else 'job-profiles'
    write_manifest(folder, started, describe_sets({name: profiles}, roles={name: 'check' if check else 'development'}),
                   configuration(DEFAULT_PARAMS))
    print(summary.to_string(index=False))
    misses = rows[rows['hit@3'] == 0].sort_values('rank', ascending=False)
    print(f'\n{len(misses)} of {len(rows)} profiles miss the top 3:')
    print(misses[['career', 'variant', 'rank', 'top3']].to_string(index=False))
    print(f'\nWritten: {folder}')


if __name__ == '__main__':
    main()
