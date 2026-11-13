"""Gold-mapping runner (Measured Matching C1, #157): loading locks, metric arithmetic, readings."""
import json

import pytest

from recommender import evaluation, mapping_eval as me
from recommender.evaluation import LockedSetError
from recommender.results import normalised_hash


def item(id, label, acceptable, split='development', category='paraphrase', **extra):
    return {'id': id, 'input': id, 'category': category, 'label': label, 'acceptable': acceptable,
            'split': split, 'group': extra.pop('group', id), **extra}


def reading(node, sim=0.9, low=False, runner_up='Z', margin=0.2, reasons=None):
    return {'node_id': node, 'similarity': sim, 'low_confidence': low, 'runner_up_node_id': runner_up,
            'margin': margin, 'reasons': reasons if reasons is not None else (['below_threshold'] if low else [])}


# Hand-built split; every expected value below is worked out by hand.
ITEMS = [
    item('u1', 'unambiguous', ['A']),
    item('u2', 'unambiguous', ['A']),
    item('u3', 'unambiguous', ['A']),
    item('u4', 'unambiguous', ['A']),
    item('s1', 'unambiguous', ['A', 'A2'], shared_owner_status='multiple_valid'),
    item('a1', 'ambiguous', ['A', 'B'], category='ambiguous'),
    item('a2', 'ambiguous', ['A', 'B'], category='ambiguous'),
    item('n1', 'no_concept', [], category='no_concept'),
    item('n2', 'no_concept', [], category='no_concept'),
]
READINGS = {
    'u1': reading('A'),                                      # correct, not flagged
    'u2': reading('B', runner_up='A', margin=0.01),          # wrong, close candidate, not flagged
    'u3': reading('B', sim=0.5, low=True, margin=0.3),       # wrong, flagged (low confidence)
    'u4': reading('A', sim=0.55, low=True),                  # correct but flagged: false uncertainty
    's1': reading('A', reasons=['shared_name']),             # correct; justified shared-name warning
    'a1': reading('C'),                                      # ambiguous, wrong, not flagged
    'a2': reading('A', sim=0.5, low=True),                   # ambiguous, flagged
    'n1': reading('X', sim=0.7),                             # no concept, confident
    'n2': reading('X', sim=0.5, low=True),                   # no concept, flagged
}
flagged = lambda r: r['low_confidence'] or 'shared_name' in r['reasons']


def p(metrics, name):
    return round(metrics[name].p, 4)


def test_metric_arithmetic_on_a_hand_built_split():
    metrics, counts, _ = me.evaluate(ITEMS, READINGS, flagged=flagged, delta=0.05)
    assert p(metrics, 'M1 exact concept accuracy') == 0.6                 # u1, u4, s1 of 5
    assert p(metrics, 'M2 top-two accuracy') == 0.8                       # + u2 via its runner-up
    assert p(metrics, 'M3 ambiguous recall') == 0.5                       # a2 of a1, a2
    assert p(metrics, 'M4 no-concept recall') == 0.5                      # n2
    assert p(metrics, 'M4 no-concept precision') == 0.2                   # n2 of 5 flagged
    assert p(metrics, 'M4 high-similarity no-concept') == 0.5             # n1
    assert p(metrics, 'M5 wrong-mapping recall') == 0.5                   # u3 of u2, u3
    assert p(metrics, 'M5 close-candidate recall') == 0.0                 # u2 not flagged
    assert metrics['M5 clear-winner recall'].n == 0                        # u3 is below 0.60, so not a clear winner
    assert p(metrics, 'M6 false uncertainty (gate, C*)') == 0.5           # u4 of u1, u4 (s1 justified, excluded)
    assert p(metrics, 'M6 false uncertainty (all, C)') == round(2 / 3, 4)  # u4, s1 of u1, u4, s1
    assert p(metrics, 'M7 confidently incorrect (primary)') == round(3 / 9, 4)      # u2, a1, n1 of all 9
    assert p(metrics, 'M7 confidently incorrect (conditional)') == 0.6              # of E = u2, u3, a1, n1, n2
    assert counts['justified shared-name warnings'] == 1
    assert counts['items'] == 9 and counts['wrong (W)'] == 2


def test_default_flag_is_todays_low_confidence():
    metrics, counts, _ = me.evaluate(ITEMS, READINGS)
    assert counts['justified shared-name warnings'] == 0                  # shared_name is not a flag before C2
    assert p(metrics, 'M6 false uncertainty (all, C)') == round(1 / 3, 4)
    assert metrics['M7 confidently incorrect (primary)'].p == metrics['M7 current behaviour (primary)'].p


def test_clustered_items_share_a_group():
    paired = [dict(i, group='g' + i['id'][-1]) for i in ITEMS]
    metrics, counts, _ = me.evaluate(paired, READINGS, flagged=flagged)
    assert counts['groups'] < counts['items']
    assert metrics['M1 exact concept accuracy'].clusters < metrics['M1 exact concept accuracy'].n


def test_validation_catches_bad_items():
    bad = [item('x', 'unambiguous', ['nope']), item('y', 'no_concept', ['A']), item('y', 'weird', []),
           item('z1', 'unambiguous', ['A'], group='g'), item('z2', 'unambiguous', ['A'], split='test', group='g')]
    problems = ' | '.join(me.validate_items(bad, {'A'}))
    assert 'unknown node ids' in problems and 'no_concept item has no acceptable' in problems
    assert 'duplicate id' in problems and 'label must be' in problems and 'spans splits' in problems


@pytest.fixture
def gold(tmp_path, monkeypatch):
    path = tmp_path / 'mapping_v1.json'
    path.write_text(json.dumps([item('d1', 'unambiguous', ['A']), item('v1', 'unambiguous', ['A'], split='validation'),
                                item('t1', 'unambiguous', ['A'], split='test')]), encoding='utf-8')
    monkeypatch.setattr(me, 'FROZEN', {'mapping_v1.json': None})
    return path


def test_unfrozen_set_reads_only_the_development_split_on_request(gold):
    with pytest.raises(me.UnfrozenSetError):
        me.load_items('development', gold)
    with pytest.raises(me.UnfrozenSetError):
        me.load_items('validation', gold, allow_unfrozen=True)
    assert [i['id'] for i in me.load_items('development', gold, allow_unfrozen=True)] == ['d1']


def test_test_split_is_locked_even_when_frozen(gold, monkeypatch):
    monkeypatch.setattr(me, 'FROZEN', {'mapping_v1.json': normalised_hash(gold)})
    with pytest.raises(LockedSetError):
        me.load_items('test', gold)
    assert [i['id'] for i in me.load_items('validation', gold)] == ['v1']
    monkeypatch.setattr(evaluation, 'git_state', lambda: {'commit': 'x', 'clean': True, 'changes': []})
    with evaluation.open_test_sets():
        assert [i['id'] for i in me.load_items('test', gold)] == ['t1']


def test_a_changed_frozen_file_is_refused(gold, monkeypatch):
    monkeypatch.setattr(me, 'FROZEN', {'mapping_v1.json': '0' * 64})
    with pytest.raises(me.UnfrozenSetError):
        me.load_items('validation', gold)


# ---- Readings against the real matcher (evaluation side only) ----

@pytest.fixture(scope='module')
def engine():
    from recommender.engine import get_engine
    return get_engine()


def test_readings_report_runner_up_margin_and_alias_owners(engine):
    owners = me.name_owners(engine.kg)
    assert len(owners['linear algebra']) == 2 and len(owners['cypress']) == 2   # every owner of an alias target
    found = {r['query']: r for r in me.readings(engine.matcher, ['routing', 'Linear algebra', 'Python'], owners)}
    production = {m.query: m.node_id for m in engine.matcher.match(['routing', 'Linear algebra', 'Python'])}
    for q, r in found.items():
        assert r['node_id'] == production[q]                        # selection is the production matcher's
        assert r['runner_up_node_id'] != r['node_id']
        assert r['margin'] == pytest.approx(r['similarity'] - r['runner_up_similarity'], abs=2e-4)
    assert found['routing']['node_label'] == 'Route' and found['routing']['margin'] == pytest.approx(0.05, abs=0.005)
    assert found['Linear algebra']['shared_with'] and not found['Python']['shared_with']
