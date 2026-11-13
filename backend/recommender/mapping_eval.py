"""Skill-mapping evaluation against the gold mapping set (Measured Matching C1, #157).

Measures whether each student phrasing was read as the right concept, separately from any
career result. The production matcher selects the concept; this module only observes it:
the runner-up (the best-scoring name of a different node), the margin to it, and the nodes
that share the selected name are computed here, on the evaluation side, from the matcher's
own index. Which readings count as flagged is a parameter. Until C2 adds uncertainty to the
matcher, the default is today's behaviour: a reading is flagged when it is `low_confidence`.

Metrics (plan revision 3 R5, revision 4 C1, revision 6 C3), each a Kish-Wilson proportion
with the item's `group` as cluster:

  M1 exact concept accuracy     M2 top-two accuracy          M3 ambiguous-input detection
  M4 no-concept detection       M5 incorrect-mapping detection (close-candidate / clear-winner)
  M6 false uncertainty (gate: excluding justified shared-name warnings; also including them)
  M7 confidently incorrect (primary over all items; conditional over the error population)

The gold set is loaded only once frozen by sha256 (FROZEN), except a development split may
be read from an unfrozen draft with `allow_unfrozen`. The test split needs open_test_sets().

Usage (from backend/):
    python -m recommender.mapping_eval --run NAME --split development [--allow-unfrozen] [--delta D]
"""

import argparse
import json
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

from pipeline import DATA_DIR
from recommender.eval_stats import kish_wilson
from recommender.evaluation import check_test_set
from recommender.results import normalised_hash

MAPPING_FILE = DATA_DIR / 'eval_sets' / 'mapping_v1.json'
# sha256 (line endings normalised) of the frozen file; None until it is reviewed and frozen.
FROZEN = {'mapping_v1.json': None}
SPLITS = ('development', 'validation', 'test')
CATEGORIES = ('exact', 'acronym', 'paraphrase', 'everyday', 'ambiguous', 'no_concept')
LABELS = ('unambiguous', 'ambiguous', 'no_concept')
OWNER_STATUS = ('multiple_valid', 'single_valid', 'none_valid')
LOW_SIMILARITY = 0.60


class UnfrozenSetError(RuntimeError):
    pass


# ---- Loading ----

def validate_items(items, node_ids):
    """Problems with the gold items (empty when valid). `node_ids` is the set of graph skill nodes."""
    problems, seen = [], set()
    for i, item in enumerate(items):
        where = item.get('id', f'#{i}')
        for field in ('id', 'input', 'category', 'label', 'acceptable', 'split', 'group'):
            if field not in item:
                problems.append(f'{where}: missing {field}')
        if item.get('id') in seen:
            problems.append(f'{where}: duplicate id')
        seen.add(item.get('id'))
        if item.get('split') not in SPLITS:
            problems.append(f'{where}: split must be one of {SPLITS}')
        if item.get('category') not in CATEGORIES:
            problems.append(f'{where}: category must be one of {CATEGORIES}')
        if item.get('label') not in LABELS:
            problems.append(f'{where}: label must be one of {LABELS}')
        unknown = [n for n in item.get('acceptable', []) if n not in node_ids]
        if unknown:
            problems.append(f'{where}: unknown node ids {unknown}')
        if item.get('label') == 'unambiguous' and not item.get('acceptable'):
            problems.append(f'{where}: an unambiguous item needs at least one acceptable node')
        if item.get('label') == 'no_concept' and item.get('acceptable'):
            problems.append(f'{where}: a no_concept item has no acceptable node')
        if item.get('shared_owner_status') not in (None, *OWNER_STATUS):
            problems.append(f'{where}: shared_owner_status must be one of {OWNER_STATUS}')
    groups = defaultdict(set)
    for item in items:
        groups[item.get('group')].add(item.get('split'))
    problems += [f'group {g}: spans splits {sorted(s)}' for g, s in groups.items() if len(s) > 1]
    return problems


def load_items(split, path=MAPPING_FILE, allow_unfrozen=False, node_ids=None):
    """Items of one split. Refuses an unfrozen file (unless a development draft is allowed),
    a file that no longer matches its frozen hash, and the test split outside open_test_sets()."""
    if split not in SPLITS:
        raise ValueError(f'split must be one of {SPLITS}')
    if split == 'test':
        check_test_set('mapping-v1-test')
    expected = FROZEN.get(path.name)
    if expected is None:
        if not (allow_unfrozen and split == 'development'):
            raise UnfrozenSetError(f'{path.name} is not frozen; only its development split can be read, '
                                   'with allow_unfrozen')
    elif normalised_hash(path) != expected:
        raise UnfrozenSetError(f'{path.name} no longer matches its frozen sha256')
    items = json.loads(path.read_text(encoding='utf-8'))
    if node_ids is not None:
        problems = validate_items(items, node_ids)
        if problems:
            raise ValueError(f'{len(problems)} problems in {path.name}: ' + '; '.join(problems[:5]))
    return [i for i in items if i['split'] == split]


# ---- Readings (evaluation side; the production matcher is unchanged) ----

def name_owners(kg):
    """casefold(name) -> sorted node ids owning it, keeping every owner of an alias target."""
    from recommender.matching import graph_skill_names, skill_aliases

    names = graph_skill_names(kg)
    owners = defaultdict(set)
    for node, label in zip(names['node_id'], names['label']):
        owners[label.casefold()].add(node)
    for alias, target in zip(*skill_aliases()[['alias', 'target']].T.values):
        owners[alias.casefold()] |= owners.get(target.casefold(), set())
    return {k: tuple(sorted(v)) for k, v in owners.items()}


def readings(matcher, queries, owners=None):
    """One reading per cleaned query: the matcher's selection plus runner-up, margin and shared owners.

    The selection comes from `matcher.match`, exactly as in production. The runner-up is the
    best-scoring index name of any other node, computed from the same scores.
    """
    from pipeline.embeddings import encode

    matches = matcher.match(queries)
    if not matches:
        return []
    vectors = encode([m.query for m in matches])
    scores = vectors @ matcher.matrix.T
    ids = np.array(matcher.node_ids)
    out = []
    for m, row in zip(matches, scores):
        if ids[int(row.argmax())] != m.node_id:
            raise AssertionError(f'evaluation-side argmax disagrees with the matcher for {m.query!r}')
        other = np.where(ids != m.node_id, row, -np.inf)
        j = int(other.argmax())
        shared = [n for n in (owners or {}).get(m.matched_text.casefold(), ()) if n != m.node_id]
        reasons = ['below_threshold'] if m.low_confidence else []
        out.append({
            'query': m.query, 'node_id': m.node_id, 'node_label': m.node_label, 'matched_text': m.matched_text,
            'similarity': m.similarity, 'low_confidence': m.low_confidence,
            'runner_up_node_id': str(ids[j]), 'runner_up_text': matcher.texts[j],
            'runner_up_similarity': round(float(row[j]), 4),
            'margin': round(m.similarity - float(row[j]), 4) + 0.0,   # + 0.0: an exact tie reads 0.0, not -0.0
            'shared_with': shared, 'reasons': reasons,
        })
    return out


def current_flagged(reading):
    """Today's behaviour, the default until C2: only low-confidence readings are flagged."""
    return bool(reading['low_confidence'])


# ---- Metrics ----

def _proportion(rows, positive, include):
    by_group = defaultdict(list)
    for item, reading in rows:
        if include(item, reading):
            by_group[item['group']].append(positive(item, reading))
    return kish_wilson(by_group)


def evaluate(items, readings_by_input, flagged=current_flagged, delta=None):
    """All mapping metrics for one split. `readings_by_input` maps an item's input to its reading."""
    rows = [(item, readings_by_input[item['input']]) for item in items]
    ok = lambda i, r: r['node_id'] in i['acceptable']
    U = lambda i, r: i['label'] == 'unambiguous'
    A = lambda i, r: i['label'] == 'ambiguous'
    N = lambda i, r: i['label'] == 'no_concept'
    C = lambda i, r: U(i, r) and ok(i, r)
    W = lambda i, r: U(i, r) and not ok(i, r)
    E = lambda i, r: W(i, r) or (A(i, r) and not ok(i, r)) or N(i, r)
    F = lambda i, r: flagged(r)
    justified = lambda i, r: F(i, r) and r['reasons'] == ['shared_name'] and i.get('shared_owner_status') == 'multiple_valid'
    C_star = lambda i, r: C(i, r) and not justified(i, r)
    any_item = lambda i, r: True

    metrics = {
        'M1 exact concept accuracy': _proportion(rows, ok, U),
        'M2 top-two accuracy': _proportion(rows, lambda i, r: ok(i, r) or r['runner_up_node_id'] in i['acceptable'], U),
        'M3 ambiguous recall': _proportion(rows, F, A),
        'M3 share of flags on ambiguous': _proportion(rows, A, F),
        'M4 no-concept recall': _proportion(rows, F, N),
        'M4 no-concept precision': _proportion(rows, N, F),
        'M4 false-positive rate (C*)': _proportion(rows, F, C_star),
        'M4 high-similarity no-concept': _proportion(rows, lambda i, r: r['similarity'] >= LOW_SIMILARITY and not F(i, r), N),
        'M5 wrong-mapping recall': _proportion(rows, F, W),
        'M6 false uncertainty (gate, C*)': _proportion(rows, F, C_star),
        'M6 false uncertainty (all, C)': _proportion(rows, F, C),
        'M7 confidently incorrect (primary)': _proportion(rows, lambda i, r: E(i, r) and not F(i, r), any_item),
        'M7 confidently incorrect (conditional)': _proportion(rows, lambda i, r: not F(i, r), E),
        'M7 current behaviour (primary)': _proportion(rows, lambda i, r: E(i, r) and not r['low_confidence'], any_item),
    }
    if delta is not None:
        close = lambda i, r: W(i, r) and r['margin'] < delta
        clear = lambda i, r: W(i, r) and r['margin'] >= delta and r['similarity'] >= LOW_SIMILARITY
        metrics['M5 close-candidate recall'] = _proportion(rows, F, close)
        metrics['M5 clear-winner recall'] = _proportion(rows, F, clear)
    counts = {
        'items': len(rows), 'groups': len({i['group'] for i, _ in rows}),
        'unambiguous': sum(U(*x) for x in rows), 'ambiguous': sum(A(*x) for x in rows), 'no_concept': sum(N(*x) for x in rows),
        'wrong (W)': sum(W(*x) for x in rows), 'justified shared-name warnings': sum(justified(*x) for x in rows),
        'unjustified shared-name warnings': sum(1 for i, r in rows if C(i, r) and F(i, r) and 'shared_name' in r['reasons']
                                                and i.get('shared_owner_status') == 'single_valid'),
    }
    by_category = {c: _proportion(rows, ok, lambda i, r, c=c: U(i, r) and i['category'] == c) for c in CATEGORIES}
    return metrics, counts, by_category


def metrics_frame(metrics):
    return pd.DataFrame([{'metric': name, **vars(est)} for name, est in metrics.items()]).round(4)


def main(argv=None):
    from recommender.engine import get_engine
    from recommender.results import configuration, parse_run, run_started, write_csv, write_manifest

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--run', required=True)
    parser.add_argument('--split', choices=SPLITS, required=True)
    parser.add_argument('--allow-unfrozen', action='store_true')
    parser.add_argument('--delta', type=float)
    args = parser.parse_args(argv)
    folder = parse_run(__doc__.splitlines()[0], ['--run', args.run])
    started = run_started(__spec__.name, argv if argv is not None else sys.argv[1:])
    engine = get_engine()
    items = load_items(args.split, allow_unfrozen=args.allow_unfrozen, node_ids=set(engine.kg.skills()))
    found = {r['query']: r for r in readings(engine.matcher, sorted({i['input'] for i in items}), name_owners(engine.kg))}
    metrics, counts, by_category = evaluate(items, found, delta=args.delta)
    write_csv(metrics_frame(metrics), folder, 'mapping_metrics.csv')
    write_csv(metrics_frame(by_category).rename(columns={'metric': 'category'}), folder, 'mapping_by_category.csv')
    write_csv(pd.DataFrame(found.values()), folder, 'mapping_readings.csv')
    write_manifest(folder, started, {f'mapping-v1-{args.split}': {'items': counts['items'], 'groups': counts['groups']}},
                   {**configuration(None), 'flagged': 'low_confidence (current behaviour)', 'delta': args.delta})
    print(metrics_frame(metrics).to_string(index=False))
    print(json.dumps(counts, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
