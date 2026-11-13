"""Build the Measured Matching gold sets, mapping_v1 and students_v1 (#159), reproducibly.

Every step reads and writes files under data/eval_sets/gold_v1/:

    authored/        inputs and profiles as the authors wrote them (with their intent notes)
    assembled.json   ids, groups and splits (seeded), made by `assemble`
    packages/        what annotators see: no intent, category, family or split (`packages`)
    annotations/A/, annotations/B/   the two independent annotations
    adjudication/    the third annotator's decisions on disagreements
    agreement.json   per-split agreement and freeze conditions (`agreement`)

`build` then writes data/eval_sets/mapping_v1.json and students_v1.json from the adjudicated
labels. Nothing here reads AjiraGuide output; splits are assigned before any annotation.

Usage (from backend/):
    python -m pipeline.gold_sets assemble | packages | agreement | relabel-packages | adjudication-packages | build
"""

import argparse
import json
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from pipeline import DATA_DIR

# GOLD_DIR lets annotation run in a folder outside the repository; the committed copy is the default.
GOLD = Path(os.environ.get('GOLD_DIR', DATA_DIR / 'eval_sets' / 'gold_v1'))
SEED = 159
SPLIT_SHARES = (('development', 0.22), ('validation', 0.39), ('test', 0.39))
BATCH = {'mapping': 280, 'profiles': 115, 'inputs': 300, 'pairs': 200}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def authored(prefix):
    records = []
    for path in sorted((GOLD / 'authored').glob(f'{prefix}*.json')):
        records += read_json(path)
    return records


def key(text):
    return ' '.join(text.split()).casefold()


# ---- assemble: ids and seeded, stratified splits ----

def allocate(units, rng, size=len):
    """Assign split names to units (lists of records), filling each split's share of records."""
    units = list(units)
    rng.shuffle(units)
    total = sum(size(u) for u in units)
    targets = [(name, share * total) for name, share in SPLIT_SHARES]
    filled = Counter()
    out = []
    for u in units:
        # the split furthest below its target, as a share of that target
        name = min(targets, key=lambda t: (filled[t[0]] / t[1], t[0] != 'development'))[0]
        filled[name] += size(u)
        out.append((name, u))
    return out


def assemble():
    # One random stream per section, so adding items to one section leaves the others' splits as they are.
    rng = random.Random(f'{SEED}-mapping')
    # Mapping items: groups stay together; stratified by category.
    items, seen, duplicates = [], set(), []
    for it in authored('mapping_'):
        if key(it['input']) in seen:
            duplicates.append(it['input'])
            continue
        seen.add(key(it['input']))
        items.append(it)
    groups = defaultdict(list)
    for it in items:
        groups[it['group']].append(it)
    by_category = defaultdict(list)
    for g in sorted(groups):
        by_category[groups[g][0]['category']].append(groups[g])
    placed = []
    for category in sorted(by_category):
        for split, group in allocate(by_category[category], rng):
            placed += [dict(it, split=split) for it in group]
    rng.shuffle(placed)
    mapping = [{'id': f'm-{n:04d}', **it} for n, it in enumerate(placed, 1)]

    # Student profiles: each profile is its own cluster; stratified by intent and subtype.
    rng = random.Random(f'{SEED}-students')
    profiles, seen_sets, duplicate_profiles = [], set(), []
    for p in authored('profiles_'):
        skills = frozenset(key(s) for s in p['wordings'][0])
        if skills in seen_sets:
            duplicate_profiles.append(p['key'])
            continue
        seen_sets.add(skills)
        profiles.append(p)
    strata = defaultdict(list)
    for p in profiles:
        strata[(p['intended_sufficiency'], (p.get('intended_reasons') or [''])[0], p.get('subtype', ''))].append([p])
    placed = []
    for stratum in sorted(strata):
        for split, (p,) in allocate(strata[stratum], rng):
            placed.append(dict(p, split=split))
    rng.shuffle(placed)
    students = [{'id': f's-{n:04d}', **p} for n, p in enumerate(placed, 1)]

    # M8: every distinct student input (case and spacing ignored), labelled once, context-free.
    inputs = {}
    for p in students:
        for wording in p['wordings']:
            for text in wording:
                inputs.setdefault(key(text), text.strip())
    keys = sorted(inputs)
    random.Random(f'{SEED}-inputs').shuffle(keys)
    student_inputs = [{'id': f'i-{n:04d}', 'input': inputs[k]} for n, k in enumerate(keys, 1)]

    rng = random.Random(f'{SEED}-pairs')
    pairs = authored('concept_pairs_')
    for split, (p,) in allocate([[p] for p in pairs], rng):
        p['split'] = 'development' if split == 'development' else 'validation'   # pairs: dev and validation only
    write_json(GOLD / 'assembled.json', {'seed': SEED, 'dropped_duplicate_inputs': duplicates,
                                         'dropped_duplicate_profiles': duplicate_profiles, 'mapping': mapping,
                                         'students': students, 'student_inputs': student_inputs, 'pairs': pairs})
    print(f'{len(mapping)} mapping items ({len(duplicates)} duplicate inputs dropped), {len(students)} profiles, '
          f'{len(student_inputs)} distinct student inputs, {len(pairs)} concept pairs')
    print('mapping by split and category:', dict(Counter((i['split'], i['category']) for i in mapping)))
    print('profiles by split and intent:', dict(Counter((p['split'], p['intended_sufficiency']) for p in students)))


# ---- packages: what annotators see ----

def packages():
    data = read_json(GOLD / 'assembled.json')
    shared = read_json(GOLD / 'catalogue' / 'shared_names.json')
    nodes = {n['id']: n['label'] for n in read_json(GOLD / 'catalogue' / 'skill_nodes.json')}

    def owners(text):
        found = shared.get(key(text))
        return [{'id': n, 'label': nodes[n]} for n in found] if found else None

    def mapping_task(r):
        task = {'id': r['id'], 'input': r['input']}
        if owners(r['input']):
            task['shared_name_owners'] = owners(r['input'])
        return task

    sets = {
        'mapping': [mapping_task(r) for r in data['mapping']],
        'inputs': [mapping_task(r) for r in data['student_inputs']],
        'profiles': [{'id': p['id'], 'wordings': p['wordings']} for p in data['students']],
        'pairs': [{'pair': p['pair'], 'a': p['a'], 'a_label': nodes[p['a']], 'b': p['b'], 'b_label': nodes[p['b']]}
                  for p in data['pairs']],
    }
    for name, tasks in sets.items():
        for k in range(0, len(tasks), BATCH[name]):
            write_json(GOLD / 'packages' / f'{name}_{k // BATCH[name] + 1:02d}.json', tasks[k:k + BATCH[name]])
        print(name, len(tasks), 'tasks in', -(-len(tasks) // BATCH[name]), 'batches')


# ---- agreement ----

def annotations(who, name, round=2):
    """One annotator's labels. Round 2 applies the blind re-label of disagreed items (plan
    revision 3 R4 step 2) over the first-round labels; round 1 is the first round alone."""
    out = {}
    for path in sorted((GOLD / 'annotations' / who).glob(f'{name}_*.json')):
        for r in read_json(path):
            out[r.get('id', r.get('pair'))] = r
    if round >= 2:
        for path in sorted((GOLD / 'annotations' / who).glob(f'relabel_{name}_*.json')):
            for r in read_json(path):
                out[r['id']] = {**r, 'relabelled': True}
    return out


def relabel_packages():
    """Items whose mapping class the two annotators disagreed on in round 1, as plain tasks."""
    packages_ = {n: {t['id']: t for path in sorted((GOLD / 'packages').glob(f'{n}_*.json')) for t in read_json(path)}
                 for n in ('mapping', 'inputs')}
    for name, tasks in packages_.items():
        A, B = annotations('A', name, round=1), annotations('B', name, round=1)
        if not (set(tasks) <= set(A) and set(tasks) <= set(B)):
            print(name, 'not fully annotated yet; skipped')
            continue
        disagreed = [tasks[i] for i in tasks if i in A and i in B and A[i]['label'] != B[i]['label']]
        size = 200
        for k in range(0, len(disagreed), size):
            write_json(GOLD / 'packages' / f'relabel_{name}_{k // size + 1:02d}.json', disagreed[k:k + size])
        print(name, len(disagreed), 'to re-label')


def agreement():
    from recommender import agreement as ag
    data = read_json(GOLD / 'assembled.json')
    careers = [c['code'] for c in read_json(GOLD / 'catalogue' / 'careers.json')]
    report = {}
    for name, records, split_of in (('mapping', data['mapping'], lambda r: r['split']),
                                    ('inputs', data['student_inputs'], lambda r: 'all'),
                                    ('profiles', data['students'], lambda r: r['split'])):
        section = {}
        for round in ((1, 2) if name != 'profiles' else (1,)):
            section[f'round {round}'] = agreement_section(name, records, split_of, careers, round)
        report[name] = section
    A, B = annotations('A', 'pairs'), annotations('B', 'pairs')
    both = [p['pair'] for p in data['pairs'] if p['pair'] in A and p['pair'] in B]
    if both:
        report['pairs'] = {'n': len(both), 'kappa (report only)': ag.cohen_kappa(
            [A[p]['relationship'] for p in both], [B[p]['relationship'] for p in both])}
    write_json(GOLD / 'agreement.json', report)
    print(json.dumps(report, indent=1)[:8000])


def agreement_section(name, records, split_of, careers, round):
    from recommender import agreement as ag
    A, B = annotations('A', name, round), annotations('B', name, round)
    missing = [r['id'] for r in records if r['id'] not in A or r['id'] not in B]
    by_split = defaultdict(list)
    for r in records:
        if r['id'] in A and r['id'] in B:
            by_split[split_of(r)].append((A[r['id']], B[r['id']]))
    section = {'missing': len(missing)}
    for split, pairs in sorted(by_split.items()):
        a, b = zip(*pairs)
        if name == 'profiles':
            section[split] = {'sufficiency': ag.sufficiency_agreement([x['sufficiency'] for x in a],
                                                                      [y['sufficiency'] for y in b]),
                              'grades': ag.grade_agreement([x['grades'] for x in a], [y['grades'] for y in b], careers)}
        else:
            section[split] = ag.mapping_agreement(a, b)
    return section


# ---- build: final sets from adjudicated labels ----

def adjudicated(name):
    """Final label per id: the annotators' shared label where they agree, else the adjudicator's."""
    A, B = annotations('A', name), annotations('B', name)
    decisions = {}
    for path in sorted((GOLD / 'adjudication').glob(f'{name}_*.json')):
        for r in read_json(path):
            decisions[r['id']] = r
    return A, B, decisions


def owner_status(final):
    marks = final.get('shared_owner_marks') or {}
    if not marks:
        return None
    valid = sum(v == 'valid' for v in marks.values())
    return 'multiple_valid' if valid >= 2 else 'single_valid' if valid == 1 else 'none_valid'


def mapping_final(a, b, decision, union=False):
    """(record, source) or (None, reason) for one mapping item.

    mapping_v1 items agree only on an identical label, acceptable set and owner marks. Student-input
    labels (`union`; they feed only the report-only M8) also agree on the same label and owner marks
    with different acceptable sets, taking their union: a selection is then gold-wrong only when both
    annotators reject it."""
    if decision is not None:
        if decision.get('drop') or decision.get('confidence') != 'high':
            return None, 'dropped: no confident adjudication'
        return decision, 'adjudicated'
    same_marks = (a.get('shared_owner_marks') or {}) == (b.get('shared_owner_marks') or {})
    if a['label'] == b['label'] and same_marks and set(a['acceptable']) == set(b['acceptable']):
        return a, 'agreed'
    if union and a['label'] == b['label'] and same_marks:
        preferred = a.get('preferred') if a.get('preferred') == b.get('preferred') else None
        return ({**a, 'acceptable': sorted(set(a['acceptable']) | set(b['acceptable'])), 'preferred': preferred},
                'agreed (union of acceptable sets)')
    return None, 'dropped: disagreement not adjudicated'


def mapping_record(final):
    status = owner_status(final)
    label = 'no_concept' if status == 'none_valid' else final['label']
    acceptable = [] if label == 'no_concept' else sorted(set(final['acceptable']))
    return {'label': label, 'acceptable': acceptable,
            'preferred': final.get('preferred') if label != 'no_concept' else None,
            **({'shared_owner_status': status} if status else {}),
            'rationale': final.get('note', '')}


def grade_three(r):
    return {c for c, g in r['grades'].items() if g == 3}


def profile_needs_adjudication(a, b):
    """Sufficiency differs, the grade-3 sets differ, or some career's grades differ by two or more."""
    careers = set(a['grades']) | set(b['grades'])
    return (a['sufficiency'] != b['sufficiency'] or grade_three(a) != grade_three(b)
            or any(abs(a['grades'].get(c, 0) - b['grades'].get(c, 0)) >= 2 for c in careers))


def merged_profile(a, b):
    """Agreed profiles: grades one level apart take the lower (conservative) grade; reason codes and
    plausible careers are the union of both annotators'."""
    careers = set(a['grades']) | set(b['grades'])
    grades = {c: min(a['grades'].get(c, 0), b['grades'].get(c, 0)) for c in careers}
    return {'sufficiency': a['sufficiency'], 'reasons': sorted(set(a.get('reasons', [])) | set(b.get('reasons', []))),
            'grades': {c: g for c, g in grades.items() if g},
            'plausible_careers': sorted(set(a.get('plausible_careers', [])) | set(b.get('plausible_careers', []))),
            'note': a.get('note', '')}


def mapping_needs_adjudication(a, b, union=False):
    return mapping_final(a, b, None, union)[0] is None


def adjudication_packages():
    """What the adjudicator sees: the task, both annotations (unattributed order), nothing else."""
    data = read_json(GOLD / 'assembled.json')
    # Mapping tasks as the annotators saw them, including any shared-name owners.
    seen = {t['id']: t for path in sorted((GOLD / 'packages').glob('*.json')) if not path.name.startswith('relabel_')
            for t in read_json(path) if 'id' in t}
    sections = (('profiles', data['students'], lambda r: {'id': r['id'], 'wordings': r['wordings']}, profile_needs_adjudication),
                ('mapping', data['mapping'], lambda r: seen[r['id']], mapping_needs_adjudication),
                ('inputs', data['student_inputs'], lambda r: seen[r['id']],
                 lambda a, b: mapping_needs_adjudication(a, b, union=True)))
    for name, records, task, needs in sections:
        A, B = annotations('A', name), annotations('B', name)
        if not A or not B:
            continue
        pending = [{**task(r), 'annotation_1': A[r['id']], 'annotation_2': B[r['id']]}
                   for r in records if r['id'] in A and r['id'] in B and needs(A[r['id']], B[r['id']])]
        size = 120
        for k in range(0, len(pending), size):
            write_json(GOLD / 'adjudication_packages' / f'{name}_{k // size + 1:02d}.json', pending[k:k + size])
        print(name, len(pending), 'to adjudicate')


def build(out=None):
    out = Path(out) if out else DATA_DIR / 'eval_sets'
    data = read_json(GOLD / 'assembled.json')
    counts = Counter()
    A, B, D = adjudicated('mapping')
    mapping = []
    for r in data['mapping']:
        final, source = mapping_final(A[r['id']], B[r['id']], D.get(r['id']))
        counts['mapping ' + source] += 1
        if final is None:
            continue
        mapping.append({'id': r['id'], 'input': r['input'], 'category': r['category'], 'domain': r['domain'],
                        **mapping_record(final), 'split': r['split'], 'group': r['group']})

    IA, IB, ID = adjudicated('inputs')
    input_labels = {}
    for r in data['student_inputs']:
        final, source = mapping_final(IA[r['id']], IB[r['id']], ID.get(r['id']), union=True)
        counts['inputs ' + source] += 1
        if final is not None:
            input_labels[key(r['input'])] = mapping_record(final)

    PA, PB, PD = adjudicated('profiles')
    students = []
    for p in data['students']:
        a, b, d = PA[p['id']], PB[p['id']], PD.get(p['id'])
        if d is not None:
            if d.get('drop') or d.get('confidence') != 'high':
                counts['profiles dropped'] += 1
                continue
            final = d
            counts['profiles adjudicated'] += 1
        elif profile_needs_adjudication(a, b):
            counts['profiles dropped: disagreement not adjudicated'] += 1
            continue
        else:
            final = merged_profile(a, b)
            counts['profiles agreed'] += 1
        labels = {key(t): input_labels.get(key(t)) for w in p['wordings'] for t in w}
        students.append({'id': p['id'], 'family': p['family'], 'split': p['split'], 'wordings': p['wordings'],
                         'wording_kind': p['wording_kind'], **({'subtype': p['subtype']} if p.get('subtype') else {}),
                         'relevant': {c: g for c, g in sorted(final['grades'].items()) if g},
                         'sufficiency': final['sufficiency'], 'reasons': sorted(final.get('reasons', [])),
                         'plausible_careers': final.get('plausible_careers', []),
                         'input_labels': {k: v for k, v in labels.items() if v is not None},
                         'rationale': final.get('note', '')})
    write_json(out / 'mapping_v1.json', mapping)
    write_json(out / 'students_v1.json', students)
    if out == DATA_DIR / 'eval_sets':
        write_json(GOLD / 'build_counts.json', dict(sorted(counts.items())))
    print(dict(sorted(counts.items())))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('step', choices=('assemble', 'packages', 'agreement', 'relabel-packages', 'adjudication-packages', 'build'))
    step = parser.parse_args(argv).step
    globals()[step.replace('-', '_')]()
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
