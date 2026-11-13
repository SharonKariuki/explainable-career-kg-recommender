"""Student-profile runner (Measured Matching C1, #157): loading locks, career and sufficiency metrics."""
import json

import pytest

from recommender import evaluation, student_eval as se
from recommender.evaluation import LockedSetError
from recommender.results import normalised_hash

CAREERS = [f'15-{i:04d}.00' for i in range(24)]


def profile(id, family='web', split='development', sufficiency='sufficient', wordings=None, relevant=None):
    return {'id': id, 'family': family, 'split': split, 'sufficiency': sufficiency,
            'wordings': wordings or [['HTML', 'CSS'], ['web pages', 'styling']],
            'relevant': relevant or {CAREERS[0]: 3, CAREERS[1]: 2}}


def fake_rank(skills):
    """Career 0 first for the first wording style, career 2 first otherwise."""
    order = [f'career:{c}' for c in CAREERS]
    return order if 'HTML' in skills else [order[2], *order[:2], *order[3:]]


def test_validation_catches_bad_profiles():
    bad = [profile('a', wordings=[['x']]), profile('a', sufficiency='maybe'), profile('b', relevant={'99-9999.00': 3}),
           {**profile('c'), 'reasons': ['I9']}]
    problems = ' | '.join(se.validate_profiles(bad, set(CAREERS)))
    for text in ('at least two wordings', 'duplicate id', 'sufficiency must be', 'invalid grades', 'unknown reason codes'):
        assert text in problems


def test_career_metrics_average_wordings_within_a_profile_first():
    rows = se.career_rows([profile('p1'), profile('p2')], fake_rank)
    assert len(rows) == 4
    assert [r['p@1'] for r in rows] == [1.0, 0.0, 1.0, 0.0]       # career 2 is not relevant
    summary = se.summarise_careers(rows)['all']
    point, low, high = summary['p@1']
    assert point == 0.5 and summary['profiles'] == 2 and summary['status'] == 'exploratory'
    assert se.summarise_careers(rows, by='family')['web']['status'] == 'exploratory'


def test_wording_agreement_is_per_profile():
    rows = se.career_rows([profile('p1'), profile('p2', wordings=[['HTML'], ['HTML', 'Git']])], fake_rank)
    point, _, _ = se.wording_agreement(rows)
    assert point == 0.5                                              # p1 disagrees, p2 agrees


def test_sufficiency_waits_for_c4():
    assert se.sufficiency([profile('p1')]) == {'available': False, 'reason': 'evidence sufficiency is implemented in C4'}


def test_sufficiency_gates_use_profiles_as_clusters_and_report_borderline_both_ways():
    profiles = [profile('s1'), profile('s2'), profile('i1', sufficiency='insufficient'),
                profile('i2', sufficiency='insufficient'), profile('b1', sufficiency='borderline')]
    predict = lambda skills: 'web pages' in skills          # every profile's second wording
    result = se.sufficiency(profiles, predict)
    recall = result['AC9 insufficient recall']
    assert recall.n == 4 and recall.clusters == 2 and recall.p == 0.5   # second wording of i1, i2 predicted insufficient
    assert result['AC10 false insufficient'].p == 0.5
    assert result['borderline_profiles'] == 1
    assert result['AC9 with borderline as insufficient'].clusters == 3
    assert result['AC10 with borderline as sufficient'].clusters == 3


def test_evidence_contamination_counts():
    units = [{'profile': 'p1', 'support': ['a', 'b'], 'gold_wrong': ['b'], 'insufficient': False, 'insufficient_without_wrong': True},
             {'profile': 'p1', 'support': ['a'], 'gold_wrong': [], 'insufficient': True, 'insufficient_without_wrong': True},
             {'profile': 'p2', 'support': ['c'], 'gold_wrong': ['d'], 'insufficient': False, 'insufficient_without_wrong': False}]
    m8 = se.evidence_contamination(units)
    assert m8['M8a contamination'].p == pytest.approx(1 / 3) and m8['M8b decision flips'].p == pytest.approx(1 / 3)
    assert m8['M8c wrong but meaningful (count)'] == 1


@pytest.fixture
def students(tmp_path, monkeypatch):
    path = tmp_path / 'students_v1.json'
    path.write_text(json.dumps([profile('d'), profile('v', split='validation'), profile('t', split='test')]), encoding='utf-8')
    monkeypatch.setattr(se, 'FROZEN', {'students_v1.json': None})
    return path


def test_unfrozen_profiles_only_development_on_request(students):
    with pytest.raises(se.UnfrozenSetError):
        se.load_profiles('development', students)
    with pytest.raises(se.UnfrozenSetError):
        se.load_profiles('validation', students, allow_unfrozen=True)
    assert [p['id'] for p in se.load_profiles('development', students, allow_unfrozen=True)] == ['d']


def test_student_test_split_is_locked(students, monkeypatch):
    monkeypatch.setattr(se, 'FROZEN', {'students_v1.json': normalised_hash(students)})
    with pytest.raises(LockedSetError):
        se.load_profiles('test', students)
    monkeypatch.setattr(evaluation, 'git_state', lambda: {'commit': 'x', 'clean': True, 'changes': []})
    with evaluation.open_test_sets():
        assert [p['id'] for p in se.load_profiles('test', students)] == ['t']
