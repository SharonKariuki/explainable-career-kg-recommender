"""Task-statement evaluation set (tasks-v1): O*NET task statements as profiles.

Each profile is one O*NET 31.0 Core task statement, entered word for word as
a single input. The pipeline never reads task statements or related
occupations, so these profiles and labels are independent of the graph.

Graded labels (docs/evaluation_protocol.md):
  3  an occupation that lists the task (two when O*NET lists the same text
     under both)
  2  the occupation of a near-identical task: nominated at SBERT cosine
     >= 0.85, kept only when accepted in twin_review.csv
  1  an O*NET Primary-Short related occupation of a listing occupation
Primary-Long and Supplemental relations are stored, ungraded, for
sensitivity analysis.

Evaluation-design decisions (recorded in the protocol):
- Texts equal after lower-casing and removing punctuation and spacing are
  one profile; it counts toward the quota of the listing occupation with the
  lowest Task ID.
- Ten profiles per occupation are drawn at random (seed 7), then split five
  and five. Tasks linked by any nominated pair share a split. Within that,
  the split balances per occupation first the tasks that contain a graph
  skill name of two or more words (or a single-word tool name, matched with
  its exact case), then the thirds of cosine to the occupation description.

Steps (from backend/), none of which runs the recommender:
    python -m recommender.task_sets nominate   # write twin_review.csv to review
    python -m recommender.task_sets build      # write tasks_v1.csv from the reviewed pairs
    python -m recommender.task_sets verify     # check the stored table in three tiers

The set is loaded only once frozen: its sha256 recorded in FROZEN.
"""

import argparse
import hashlib
import itertools
import json
import random
import re
from dataclasses import dataclass, field

import networkx as nx
import pandas as pd

from pipeline import DATA_DIR, RAW_DIR
from pipeline.onet import ONET_DIR, SCOPE_FILE, read_onet
from recommender.evaluation import check_test_set
from recommender.results import normalised_hash

EVAL_DIR = DATA_DIR / 'eval_sets'
TASKS_FILE = EVAL_DIR / 'tasks_v1.csv'
TWIN_FILE = EVAL_DIR / 'twin_review.csv'
TASK_SEED = 7
PER_CAREER = 10
PER_SPLIT = 5
TWIN_THRESHOLD = 0.85
SPLITS = ('validation', 'test')
DECISIONS = {'accept', 'reject'}
# sha256 of the O*NET 31.0 files the set is built from.
RAW_FILES = {
    ONET_DIR / 'Task Statements.txt': 'aee1788c7ce2ebf19c1700bc4a1d7aa69a59965736d56a521945256df3f68d08',
    ONET_DIR / 'Related Occupations.txt': 'af539f6f01a36e9514a0dd13cbe125df8cca1114c690505342837f338621906c',
    RAW_DIR / 'onet' / 'db_31_0_text.zip': '6883548adf5fde64cf6f801b35d15519c9225f2732c3cab0e281c652d16b23a9',
}
# sha256 (line endings normalised) of each frozen file; None until it is reviewed and frozen.
FROZEN = {
    'tasks_v1.csv': 'f6cc9db450c9b8fdb714e5f01f3ab2a91760868e8b1fca7661bcc410a2a2a84b',
    'twin_review.csv': '1b557b3b2f3c922a9c5b396b8e57a6b4f194164acb4a9fc54411d05b4e4dc6b4',
}
# Processed data (normalised sha256) the stored covariates were computed from (v1): the wording
# flag from the graph's skill names, the cosine from occupations.csv descriptions.
COVARIATE_DATA = {
    'esco_occupation_skills.csv': '730a0fd91330a4d0d50c50029e2d579c3ab1acacb300a32ccbc86cc020f68e6f',
    'esco_occupations.csv': '40d9022063397afb94fdd42b21ab48c437fcebd04407a8cec22b2c657a92a76c',
    'esco_onet_map.csv': '0f969e55c9bc4a83b169610fc27c38e1ca9de4fd4972a0c8d7535d882f1cefe2',
    'esco_skills.csv': '8ca13e4006818d6c261ce40ce28fb4ce37678118de1cc1ea0bc6266fe9221579',
    'occupations.csv': '1e269e3b46ee92fe38f7da2d374c135fcd6bec4a1fccad632a6c1ff7e2b17f5c',
    'onet_skills.csv': '40739fd1460fd8925a588cf2ba521f8322e9eb003b57afb1e747bae6271cf37d',
    'onet_tools.csv': '85704841128099482501c5e6c6b966bf1aeed2fd844552864d831dbaafe7eeea',
}
# Stored cosines are rounded to 2 decimals, so a harmless floating-point difference can move a
# value across a rounding edge: one step, 0.01. Anything larger is a real change (another model
# version, or edited descriptions).
COSINE_TOLERANCE = 0.01


class VerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class GradedProfile:
    profile_id: str
    career_id: str
    skills: tuple
    grades: dict  # career id -> 3, 2 or 1
    strata: dict = field(default_factory=dict)  # covariate -> value, for the overlap breakdown


def career_id(code):
    return f'career:{code}'


def check_raw():
    for path, expected in RAW_FILES.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'{path.name} differs from the O*NET 31.0 file tasks-v1 was built from')


def normalise(text):
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', text.lower()).split())


def core_tasks():
    codes = set(pd.read_csv(SCOPE_FILE, dtype=str).onet_soc_code)
    tasks = read_onet('Task Statements.txt')
    tasks = tasks[tasks['O*NET-SOC Code'].isin(codes) & (tasks['Task Type'] == 'Core')]
    return (tasks.rename(columns={'O*NET-SOC Code': 'onet_soc_code', 'Task ID': 'task_id', 'Task': 'task'})
            [['task_id', 'onet_soc_code', 'task']].sort_values('task_id', key=lambda s: s.astype(int))
            .reset_index(drop=True))


def candidates(tasks):
    """One row per distinct normalised text: its Task IDs, listing occupations and quota owner."""
    rows = []
    for _, group in tasks.groupby(tasks.task.map(normalise), sort=False):
        group = group.sort_values('task_id', key=lambda s: s.astype(int))
        first = group.iloc[0]
        rows.append({'task_id': first.task_id, 'task': first.task, 'owner': first.onet_soc_code,
                     'task_ids': list(group.task_id), 'source_codes': sorted(set(group.onet_soc_code))})
    return pd.DataFrame(rows).sort_values('task_id', key=lambda s: s.astype(int)).reset_index(drop=True)


def related_occupations():
    """{(code, related code): tier} within the 24 careers, in O*NET's direction."""
    codes = set(pd.read_csv(SCOPE_FILE, dtype=str).onet_soc_code)
    r = read_onet('Related Occupations.txt')
    r = r[r['O*NET-SOC Code'].isin(codes) & r['Related O*NET-SOC Code'].isin(codes)]
    return {(a, b): tier for a, b, tier in zip(r['O*NET-SOC Code'], r['Related O*NET-SOC Code'], r['Relatedness Tier'])}


def skill_name_flag(names):
    """Whether a text contains a graph skill name of two or more words (any case) or a
    single-word tool name (exact case, so the verb 'access' is not the tool 'Access').
    `names` has columns label and skill_type."""
    names = names[names.label.str.len() >= 4]
    words = names.label.str.split().str.len()
    multi = sorted(set(names[words >= 2].label), key=len, reverse=True)
    tools = sorted(set(names[(words == 1) & (names.skill_type == 'tool')].label), key=len, reverse=True)
    multi_re = re.compile(r'\b(' + '|'.join(map(re.escape, multi)) + r')\b', re.IGNORECASE)
    tool_re = re.compile(r'\b(' + '|'.join(map(re.escape, tools)) + r')\b')
    return lambda text: bool(multi_re.search(text) or tool_re.search(text))


def graph_name_flag():
    from recommender.graph import get_graph
    from recommender.matching import graph_skill_names
    kg = get_graph()
    names = graph_skill_names(kg)
    names['skill_type'] = [kg.node(n)['skill_type'] for n in names.node_id]
    return skill_name_flag(names)


def nominate():
    """Cross-career task pairs at cosine >= TWIN_THRESHOLD, for review."""
    from pipeline.embeddings import encode
    check_raw()
    tasks = core_tasks()
    vectors = encode(tasks.task.tolist())
    similarity = vectors @ vectors.T
    rows = []
    for i in range(len(tasks)):
        for j in range(i + 1, len(tasks)):
            a, b = tasks.iloc[i], tasks.iloc[j]
            if a.onet_soc_code != b.onet_soc_code and similarity[i, j] >= TWIN_THRESHOLD:
                rows.append({'task_id_a': a.task_id, 'code_a': a.onet_soc_code, 'task_a': a.task,
                             'task_id_b': b.task_id, 'code_b': b.onet_soc_code, 'task_b': b.task,
                             'cosine': round(float(similarity[i, j]), 4), 'decision': 'pending', 'reason': ''})
    return pd.DataFrame(rows)


def select(cands, seed=TASK_SEED):
    """PER_CAREER candidates per owner, drawn at random."""
    rng = random.Random(seed)
    chosen = []
    for owner, group in sorted(cands.groupby('owner')):
        ids = sorted(group.task_id, key=int)
        chosen += rng.sample(ids, PER_CAREER)
    return cands[cands.task_id.isin(chosen)].reset_index(drop=True)


def assign_splits(chosen, pairs, flagged, third, seed=TASK_SEED):
    """{candidate task_id: split}, found exactly: PER_SPLIT per owner and split and nominated
    pairs never split (hard); then, per owner, the smallest validation-test gap in flagged
    candidates, then in each third of own-description cosine; then the smallest overall gaps."""
    key = {t: c.task_id for c in chosen.itertuples() for t in c.task_ids}
    owner = dict(zip(chosen.task_id, chosen.owner))
    links = nx.Graph()
    links.add_edges_from((key[a], key[b]) for a, b in zip(pairs.task_id_a, pairs.task_id_b)
                         if a in key and b in key and key[a] != key[b])
    groups = sorted((sorted(g, key=int) for g in nx.connected_components(links)), key=lambda g: int(g[0]))
    careers = sorted(set(owner.values()))
    ids = {c: sorted((t for t in owner if owner[t] == c), key=int) for c in careers}

    def gaps(c, val):
        side = lambda t: 1 if t in val else -1
        return (abs(sum(side(t) * flagged[t] for t in ids[c])),
                sum(abs(sum(side(t) for t in ids[c] if third[t] == k)) for k in range(3)))

    options = {c: [frozenset(v) for v in itertools.combinations(ids[c], PER_SPLIT)] for c in careers}
    best = None
    for sides in itertools.product((True, False), repeat=len(groups)):  # True: the group is in validation
        forced = {t: side for group, side in zip(groups, sides) for t in group}
        picks = {}
        for c in careers:
            fits = [v for v in options[c] if all((t in v) == forced[t] for t in ids[c] if t in forced)]
            if not fits:
                break
            score = min(gaps(c, v) for v in fits)
            picks[c] = [v for v in fits if gaps(c, v) == score]
        else:
            total = tuple(map(sum, zip(*(gaps(c, picks[c][0]) for c in careers))))
            if best is None or total < best[0]:
                best = (total, picks)
    if best is None:
        raise RuntimeError('no split satisfies the quotas and the near-duplicate groups')

    # Among each owner's equally good splits, balance the overall totals.
    rng = random.Random(seed)
    picks = best[1]
    choice = {c: rng.choice(sorted(picks[c], key=sorted)) for c in careers}

    def overall(choice):
        val = set().union(*choice.values())
        side = lambda t: 1 if t in val else -1
        return (abs(sum(side(t) * flagged[t] for t in owner)),
                sum(abs(sum(side(t) for t in owner if third[t] == k)) for k in range(3)))
    for _ in range(10):
        changed = False
        for c in careers:
            current = overall(choice)
            for v in sorted(picks[c], key=sorted):
                trial = {**choice, c: v}
                if overall(trial) < current:
                    choice, current, changed = trial, overall(trial), True
        if not changed:
            break
    validation = set().union(*choice.values())
    return {t: 'validation' if t in validation else 'test' for t in owner}


def labels(chosen, pairs):
    """{candidate task_id: (grades, Primary-Long, Supplemental)} from O*NET and the reviewed pairs."""
    related = related_occupations()
    twins = {}
    for p in pairs[pairs.decision == 'accept'].itertuples():
        twins.setdefault(p.task_id_a, set()).add(p.code_b)
        twins.setdefault(p.task_id_b, set()).add(p.code_a)
    result = {}
    for c in chosen.itertuples():
        grades = {code: 3 for code in c.source_codes}
        for code in {x for t in c.task_ids for x in twins.get(t, ())}:
            grades[code] = max(grades.get(code, 0), 2)
        tiers = {tier: sorted({b for (a, b), x in related.items() if a in c.source_codes and x == tier})
                 for tier in ('Primary-Short', 'Primary-Long', 'Supplemental')}
        for code in tiers['Primary-Short']:
            grades[code] = max(grades.get(code, 0), 1)
        result[c.task_id] = (dict(sorted(grades.items())), tiers['Primary-Long'], tiers['Supplemental'])
    return result


def description_cosines(chosen):
    """{candidate task_id: highest SBERT cosine to a listing occupation's description, to 2 decimals}."""
    from pipeline.embeddings import encode
    occupations = pd.read_csv(DATA_DIR / 'processed' / 'occupations.csv', dtype=str)
    descriptions = dict(zip(occupations.onet_soc_code, occupations.title + '. ' + occupations.description))
    codes = sorted(descriptions)
    vectors = dict(zip(codes, encode([descriptions[c] for c in codes])))
    return {c.task_id: round(max(float(v @ vectors[s]) for s in c.source_codes), 2)
            for c, v in zip(chosen.itertuples(), encode(chosen.task.tolist()))}


def cosine_thirds(cosine):
    """Thirds of the rounded cosines; equal values fall in the same third."""
    ranks = pd.Series(cosine).rank(method='min', pct=True)
    return {t: min(int(q * 3 - 1e-9), 2) for t, q in ranks.items()}


def task_row(c, label, split, cosine, third, flagged):
    """One row of tasks_v1.csv for candidate `c`; build and check_regeneration both use it."""
    grades, primary_long, supplemental = label
    return {
        'profile_id': f'task-{c.task_id}', 'task_id': c.task_id, 'onet_soc_code': c.owner,
        'task_ids': json.dumps(c.task_ids), 'source_codes': json.dumps(c.source_codes),
        'split': split, 'task': c.task, 'grades': json.dumps(grades),
        'primary_long': json.dumps(primary_long), 'supplemental': json.dumps(supplemental),
        'own_description_cosine': cosine, 'cosine_third': third, 'names_a_graph_skill': flagged,
    }


def build(pairs):
    """The tasks-v1 table from the reviewed pairs. Raises if any pair is undecided."""
    undecided = sorted(set(pairs.decision) - DECISIONS)
    if undecided:
        raise ValueError(f'every nominated pair needs accept or reject before building; found {undecided}')
    check_raw()
    flag = graph_name_flag()
    chosen = select(candidates(core_tasks()))
    flagged = {c.task_id: flag(c.task) for c in chosen.itertuples()}
    cosine = description_cosines(chosen)
    third = cosine_thirds(cosine)
    split = assign_splits(chosen, pairs, flagged, third)
    label = labels(chosen, pairs)
    rows = [task_row(c, label[c.task_id], split[c.task_id], cosine[c.task_id], third[c.task_id], flagged[c.task_id])
            for c in chosen.itertuples()]
    return pd.DataFrame(rows).sort_values(['onet_soc_code', 'split', 'task_id']).reset_index(drop=True)


# Verification in three tiers. The stored table (the frozen tasks_v1.csv) is authoritative:
# nothing here rewrites it, and SBERT values are only ever compared, never used to re-split.

def check_frozen(required):
    """The frozen files match their recorded sha256. Before freezing, `required` loaders refuse;
    verification skips the files that are not frozen yet."""
    for filename, expected in FROZEN.items():
        if expected is None:
            if required:
                raise RuntimeError(f'{filename} is not frozen yet; review it and record its sha256 in FROZEN')
        elif normalised_hash(EVAL_DIR / filename) != expected:
            raise VerificationError(f'{filename} no longer matches its frozen sha256')


def check_integrity():
    """Tier 1: the raw O*NET files and, once frozen, the frozen files match their sha256."""
    check_raw()
    check_frozen(required=False)


def covariate_data_unchanged(files=None):
    """Whether the processed data (all files, or `files`) is what the stored covariates came from."""
    from recommender.results import configuration
    current = configuration(None)['processed_data']
    return all(current.get(f) == COVARIATE_DATA.get(f) for f in (files or COVARIATE_DATA.keys() | current.keys()))


def same_tasks(chosen, table):
    """Problems if the table does not hold exactly the selected tasks, once each."""
    problems = []
    if table.task_id.duplicated().any():
        problems.append(f'task IDs repeated: {sorted(set(table.task_id[table.task_id.duplicated()]), key=int)}')
    if set(chosen.task_id) != set(table.task_id):
        problems.append(f'selected task IDs differ: {sorted(set(chosen.task_id) ^ set(table.task_id), key=int)}')
    return problems


def check_regeneration(table, pairs):
    """Tier 2, without SBERT: task IDs, texts, owners, labels and (while the graph data is the
    one it came from) the wording flag regenerate exactly from the raw files and the reviewed
    pairs; the stored cosine thirds are the thirds of the stored cosines; and the split
    regenerates exactly from the stored flag and thirds. Raises VerificationError listing
    every difference."""
    chosen = select(candidates(core_tasks()))
    problems = same_tasks(chosen, table)
    stored = table.set_index('task_id')
    if not problems:
        third = cosine_thirds(stored.own_description_cosine.to_dict())
        problems += [f'task {t} cosine_third: stored {stored.at[t, "cosine_third"]}, '
                     f'third of its stored cosine {third[t]}'
                     for t in sorted(third, key=int) if third[t] != stored.at[t, 'cosine_third']]
        flag = graph_name_flag() if covariate_data_unchanged() else None
        label = labels(chosen, pairs)
        split = assign_splits(chosen, pairs, stored.names_a_graph_skill.to_dict(), stored.cosine_third.to_dict())
        for c in chosen.itertuples():
            row = stored.loc[c.task_id]
            # The covariates come from the table itself (the flag is recomputed while its data is
            # unchanged); everything else is regenerated.
            expected = task_row(c, label[c.task_id], split[c.task_id], row.own_description_cosine,
                                row.cosine_third, flag(c.task) if flag else row.names_a_graph_skill)
            del expected['task_id']  # the index
            if set(expected) != set(stored.columns):
                problems.append(f'columns differ: {sorted(set(expected) ^ set(stored.columns))}')
                break
            for column, value in expected.items():
                if stored.at[c.task_id, column] != value:
                    problems.append(f'task {c.task_id} {column}: stored {stored.at[c.task_id, column]!r}, '
                                    f'regenerated {value!r}')
    if problems:
        raise VerificationError(f'{len(problems)} differences:\n' + '\n'.join(problems))


def check_covariate_drift(table):
    """Tier 3, with SBERT: recomputed cosines must lie within COSINE_TOLERANCE of the stored
    ones (raises otherwise). Returns a warning for each task whose recomputed third differs;
    the stored third, and so the split, stands. After the occupation descriptions change,
    the stored cosines describe the v1 descriptions: they stand, and drift is not checked."""
    chosen = select(candidates(core_tasks()))
    problems = same_tasks(chosen, table)
    if problems:
        raise VerificationError('; '.join(problems))
    if not covariate_data_unchanged(['occupations.csv']):
        return ['occupations.csv differs from the v1 data the stored cosines came from; '
                'stored cosines and split stand, drift not checked']
    stored = table.set_index('task_id')
    cosine = description_cosines(chosen)
    beyond = {t: round(abs(c - stored.at[t, 'own_description_cosine']), 4) for t, c in cosine.items()
              if abs(c - stored.at[t, 'own_description_cosine']) > COSINE_TOLERANCE + 1e-9}
    if beyond:
        raise VerificationError(f'cosine drift above {COSINE_TOLERANCE}: {beyond}')
    third = cosine_thirds(cosine)
    return [f'task {t}: recomputed cosine third {third[t]}, stored {stored.at[t, "cosine_third"]} (split unchanged)'
            for t in sorted(third, key=int) if third[t] != stored.at[t, 'cosine_third']]


def read_table(path=TASKS_FILE):
    return pd.read_csv(path, dtype={'task_id': str, 'onet_soc_code': str})


def read_pairs(path=TWIN_FILE):
    return pd.read_csv(path, dtype={'task_id_a': str, 'task_id_b': str, 'code_a': str, 'code_b': str})


def is_frozen():
    return None not in FROZEN.values()


def _load(split):
    check_frozen(required=True)
    table = read_table()
    return [
        GradedProfile(r.profile_id, career_id(r.onet_soc_code), (r.task,),
                      {career_id(c): g for c, g in json.loads(r.grades).items()},
                      {'description cosine third': int(r.cosine_third),
                       'names a graph skill': bool(r.names_a_graph_skill)})
        for r in table[table.split == split].itertuples()
    ]


def task_validation_profiles():
    return _load('validation')


def task_test_profiles():
    check_test_set('tasks-v1-test')
    return _load('test')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('step', choices=['nominate', 'build', 'verify'])
    step = parser.parse_args(argv).step
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    if step == 'nominate':
        pairs = nominate()
        with open(TWIN_FILE, 'x', newline='', encoding='utf-8') as file:  # never overwrite a reviewed file
            pairs.to_csv(file, index=False)
        print(f'{len(pairs)} pairs to review -> {TWIN_FILE}')
    elif step == 'verify':
        table, pairs = read_table(), read_pairs()
        check_integrity()
        check_regeneration(table, pairs)
        warnings = check_covariate_drift(table)
        print(f'tasks-v1 verified: integrity, exact regeneration, cosines within {COSINE_TOLERANCE}; '
              f'{len(warnings)} cosine-third warnings')
        for w in warnings:
            print('  warning:', w)
    else:
        if FROZEN['tasks_v1.csv'] is not None:
            parser.error('tasks_v1.csv is frozen; build a new version instead')
        table = build(read_pairs())
        table.to_csv(TASKS_FILE, index=False)
        counts = table.groupby(['onet_soc_code', 'split']).size()
        print(f'{len(table)} profiles -> {TASKS_FILE}; per career and split: {counts.min()}-{counts.max()}')


if __name__ == '__main__':
    main()
