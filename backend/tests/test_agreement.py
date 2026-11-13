"""Inter-annotator agreement (Measured Matching C3, #159); expected values worked out by hand."""
import pytest

from recommender import agreement as ag


def test_cohen_kappa_by_hand():
    # po = 0.8; marginals A: x 3, y 2; B: x 3, y 2 -> pe = 0.36 + 0.16 = 0.52
    a, b = list('xxxyy'), list('xxyxy')
    assert ag.cohen_kappa(a, b) == pytest.approx((0.6 - 0.52) / 0.48)
    assert ag.cohen_kappa(a, a) == 1.0
    assert ag.cohen_kappa(['x'] * 4, ['x'] * 4) == 1.0          # one class only: perfect agreement


def test_weighted_kappa_penalises_distance():
    a = [0, 1, 2, 3, 3]
    near, far = [0, 1, 2, 2, 3], [0, 1, 2, 0, 3]
    assert ag.weighted_kappa(a, a, (0, 1, 2, 3)) == 1.0
    assert ag.weighted_kappa(a, near, (0, 1, 2, 3)) > ag.weighted_kappa(a, far, (0, 1, 2, 3))


def test_jaccard_conventions():
    assert ag.jaccard([], []) == 1.0 and ag.jaccard(['a'], []) == 0.0
    assert ag.jaccard(['a', 'b'], ['b', 'c']) == pytest.approx(1 / 3)


def test_sufficiency_report_and_freeze():
    S, B, I = 'sufficient', 'borderline', 'insufficient'
    a = [S, S, S, S, I, I, I, I, B, S]
    b = [S, S, S, S, I, I, I, I, S, B]
    r = ag.sufficiency_agreement(a, b)
    assert r['3-class raw agreement'] == 0.8
    assert r['confusion (rows A, columns B)'][B][S] == 1 and r['confusion (rows A, columns B)'][S][B] == 1
    assert r['B->S raw agreement'] == 1.0 and r['B->I raw agreement'] == 0.8
    assert r['restricted n'] == 8 and r['restricted excluded pairs'] == {'B-S': 2}
    assert r['borderline rate either'] == 0.2
    assert r['freeze'] == (r['3-class kappa'] >= 0.6 and min(r['B->S kappa'], r['B->I kappa']) >= 0.6)


def test_grade_agreement_counts_both_empty_as_agreement():
    careers = ['c1', 'c2', 'c3']
    a = [{'c1': 3, 'c2': 1}, {}, {'c3': 2}]
    b = [{'c1': 3, 'c2': 2}, {}, {'c3': 3}]
    r = ag.grade_agreement(a, b, careers)
    assert r['pairs'] == 9 and r['profiles with both grade-3 sets empty'] == 1
    assert r['grade-3 Jaccard (mean)'] == pytest.approx((1 + 1 + 0) / 3)
    assert r['grade-3 Jaccard (mean, excluding both empty)'] == pytest.approx(0.5)


def test_mapping_agreement():
    a = [{'label': 'unambiguous', 'acceptable': ['n1'], 'preferred': 'n1'},
         {'label': 'unambiguous', 'acceptable': ['n1', 'n2'], 'preferred': 'n1'},
         {'label': 'no_concept', 'acceptable': [], 'preferred': None},
         {'label': 'ambiguous', 'acceptable': ['n3', 'n4'], 'preferred': 'n3'}]
    b = [{'label': 'unambiguous', 'acceptable': ['n1'], 'preferred': 'n1'},
         {'label': 'unambiguous', 'acceptable': ['n2'], 'preferred': 'n2'},
         {'label': 'no_concept', 'acceptable': [], 'preferred': None},
         {'label': 'unambiguous', 'acceptable': ['n3'], 'preferred': 'n3'}]
    r = ag.mapping_agreement(a, b)
    assert r['class raw agreement'] == 0.75 and r['both unambiguous'] == 2
    assert r['acceptable Jaccard (mean, both unambiguous)'] == pytest.approx(0.75)
    assert r['preferred exact agreement (both unambiguous)'] == 0.5
    assert r['freeze acceptable'] is True
