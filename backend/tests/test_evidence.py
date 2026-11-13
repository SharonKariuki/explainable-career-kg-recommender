"""Evidence sufficiency (Measured Matching C4, #160): constructed tests E1-E11 (plan revision 4
§C6, revision 5 §C6.1), the threshold constraints, and independence from top_k.

E1-E5 and E10-E11 run the real engine with the fixture thresholds; E6-E8 use a small fake
graph so that boundaries can be set exactly. E9 checks the ranking is untouched.
"""
from dataclasses import dataclass, replace
from types import SimpleNamespace

import pytest

from recommender import evidence as ev
from recommender.matching import SkillMatch

F = ev.FIXTURE_PARAMS


# ---- Constraints (Q19) ----

def test_fixture_and_default_thresholds_satisfy_the_constraints():
    for params in (ev.FIXTURE_PARAMS, ev.DEFAULT_PARAMS):
        params.check()
        assert params.w_min > ev.NEVER_CORE_MAX and params.cap < params.W_min and params.G_min >= 2


@pytest.mark.parametrize('change', [{'w_min': 1.58}, {'cap': 4.0}, {'G_min': 1}])
def test_thresholds_outside_the_constraints_are_refused(change):
    with pytest.raises(ValueError):
        replace(F, **change).check()


# ---- A small fake graph for exact boundaries ----

@dataclass(frozen=True)
class Contribution:
    skill_id: str


def fake_engine(weights):
    """Skills with chosen raw weights; careers given per test through their contributions."""
    engine = SimpleNamespace(_evidence_raw_weights=dict(weights))
    return engine


def reading(node, uncertain=False, sim=0.9):
    return SkillMatch(query=node, node_id=node, node_label=node, matched_text=node, similarity=sim,
                      low_confidence=sim < 0.6, uncertain=uncertain,
                      uncertainty_reasons=('close_runner_up',) if uncertain else ())


def career(code, skills, score):
    return SimpleNamespace(career_id=f'career:{code}', score=score,
                           skill_contributions=tuple(Contribution(s) for s in skills))


def assess(weights, readings, careers, params=F):
    return ev.assess(fake_engine(weights), readings, careers, params)


def test_E6_close_call_alone_never_makes_a_profile_insufficient():
    w = {'a': 2.5, 'b': 2.5, 'c': 2.0}
    careers = [career('X', 'abc', 0.80), career('Y', 'abc', 0.795), career('Z', 'ab', 0.79)]
    result = assess(w, [reading(s) for s in 'abc'], careers)
    assert result['evidence']['close_call'] is True and result['evidence']['close_alternatives'] == 3
    assert result['insufficient'] is False


def test_E7_flips_exactly_at_w_min():
    careers = [career('X', 'ab', 0.5)]
    below = assess({'a': F.w_min - 1e-9, 'b': 3.0}, [reading('a'), reading('b')], careers)
    at = assess({'a': F.w_min, 'b': 3.0}, [reading('a'), reading('b')], careers)
    assert below['evidence']['meaningful_concepts'] == 1 and below['insufficient'] is True
    assert at['evidence']['meaningful_concepts'] == 2 and at['insufficient'] is False


def test_E7_flips_exactly_at_G_min_and_W_min():
    w = {'a': 2.0, 'b': 2.0, 'c': 2.0}
    one = assess(w, [reading('a')], [career('X', 'abc', 0.5)])
    two = assess(w, [reading('a'), reading('b')], [career('X', 'abc', 0.5)])
    assert one['evidence']['supported_concepts'] == F.G_min - 1 and one['insufficient'] is True
    assert two['evidence']['supported_concepts'] == F.G_min and two['evidence']['supported_weight'] == F.W_min
    assert two['insufficient'] is False                               # weight exactly W_min suffices
    light = assess({'a': 1.7, 'b': 1.7}, [reading('a'), reading('b')], [career('X', 'ab', 0.5)])
    assert light['evidence']['supported_concepts'] == 2 and light['insufficient'] is True   # 3.4 < W_min


def test_E8_a_weight_above_cap_counts_at_cap_and_never_suffices_alone():
    result = assess({'a': 9.0}, [reading('a')], [career('X', 'a', 0.9)])
    assert result['evidence']['supported_weight'] == F.cap < F.W_min
    assert result['insufficient'] is True


def test_uncertain_readings_are_not_evidence():
    w = {'a': 2.5, 'b': 2.5}
    result = assess(w, [reading('a'), reading('b', uncertain=True)], [career('X', 'ab', 0.5)])
    assert result['evidence']['confident_concepts'] == 1 and result['insufficient'] is True


def test_support_is_counted_within_one_career_not_across_careers():
    w = {'a': 3.0, 'b': 3.0}
    result = assess(w, [reading('a'), reading('b')], [career('X', 'a', 0.6), career('Y', 'b', 0.5)])
    assert result['evidence']['meaningful_concepts'] == 2 and result['evidence']['supported_concepts'] == 1
    assert result['insufficient'] is True and result['evidence']['reasons'] == ['skills_spread_across_areas']


def test_best_supported_career_need_not_be_the_top_ranked():
    w = {'a': 2.5, 'b': 2.5}
    result = assess(w, [reading('a'), reading('b')], [career('X', 'a', 0.9), career('Y', 'ab', 0.4)])
    assert result['evidence']['best_supported_career'] == 'Y' and result['insufficient'] is False


# ---- Real engine: E1-E5, E10, E11, and E9 invariance ----

E1 = ['ADP Workforce Now', 'Anti-Trojan software', '3D graphics software', 'Arping', 'Adobe Distiller']
E2 = ['eMASS', 'Hugging Face', 'keep up to date on product knowledge', 'Microsoft Azure Data Factory',
      'Operational Data Store ODS software']
E5 = ['ICT network routing', 'forecast future ICT network needs', 'design computer network']
E10 = ['Hugging Face', 'Solidity', 'eMASS', 'Microsoft Azure Data Factory']
E11 = ['Solidity', 'smart contract', 'eMASS', 'MITRE ATT&CK']
CASES = {'E1': E1, 'E2': E2, 'E3': ['Solidity'], 'E4': ['Solidity', 'Python', 'SQL'], 'E5': E5, 'E10': E10, 'E11': E11}


@pytest.fixture(scope='module')
def engine():
    from recommender.engine import get_engine
    return get_engine()


@pytest.fixture(scope='module', params=['fixture', 'calibrated'])
def results(engine, request):
    """E1-E5, E10, E11 under the fixture thresholds and again under the calibrated ones (AC12)."""
    params = F if request.param == 'fixture' else ev.DEFAULT_PARAMS
    out = {}
    for name, skills in CASES.items():
        matches, ranked = engine.rank(skills, top_k=None)
        out[name] = ev.assess(engine, matches, ranked, params)
        out[name]['params'] = params
    return out


def test_E1_rare_never_core_tools_are_insufficient(results):
    e = results['E1']['evidence']
    assert e['supported_concepts'] <= 1 and results['E1']['insufficient'] is True


def test_E2_rare_core_skills_from_different_careers_are_insufficient(results):
    e = results['E2']['evidence']
    assert e['meaningful_concepts'] == 5 and e['supported_concepts'] == 1 and results['E2']['insufficient'] is True


def test_E3_one_rare_core_skill_alone_is_insufficient(results):
    e = results['E3']['evidence']
    p = results['E3']['params']
    assert e['supported_weight'] <= p.cap < p.W_min and results['E3']['insufficient'] is True


def test_E4_generic_skills_add_nothing(results):
    assert results['E4']['evidence']['supported_weight'] == results['E3']['evidence']['supported_weight']
    assert results['E4']['insufficient'] is True


def test_E5_two_or_more_concepts_of_one_career_are_sufficient(results):
    e = results['E5']['evidence']
    assert e['supported_concepts'] >= 2 and e['supported_weight'] >= results['E5']['params'].W_min
    assert e['best_supported_career'] == '15-1244.00' and results['E5']['insufficient'] is False


def test_E10_specific_skills_spread_across_areas(results):
    e = results['E10']['evidence']
    assert results['E10']['insufficient'] is True and e['reasons'][0] == 'skills_spread_across_areas'
    assert 'too little' not in e['advice'] and 'too general' not in e['advice']


def test_E11_two_skills_in_one_area_suffice(results):
    assert results['E11']['insufficient'] is False
    assert results['E11']['evidence']['best_supported_career'] == '15-1212.00'


def test_E9_evidence_never_changes_the_ranking(engine):
    from core import services
    for skills in CASES.values():
        plain_matches, plain = engine.rank(skills, top_k=None)
        matches, ranked, _ = services.rank_with_evidence(skills)
        assert [(r.career_id, r.score, r.components) for r in ranked] == \
               [(r.career_id, r.score, r.components) for r in plain]
        assert [m.node_id for m in matches] == [m.node_id for m in plain_matches]


def test_evidence_is_the_same_for_every_top_k():
    from core import services
    skills = E5 + ['Python', 'SQL', 'JavaScript']          # reaches every career
    _, everything, first = services.rank_with_evidence(skills, top_k=1)
    total = len(services.rank_with_evidence(skills)[1])
    for k in (5, 10, 24, 50, None):
        _, ranked, assessed = services.rank_with_evidence(skills, top_k=k)
        assert assessed == first
        assert len(ranked) == (min(k, total) if k else total)


def test_gold_wrong_selections_follow_the_input_labels():
    from recommender.student_report import gold_wrong
    labels = {'tcp/ip': {'label': 'no_concept', 'acceptable': []},
              'routing': {'label': 'unambiguous', 'acceptable': ['esco:route']},
              'python': {'label': 'unambiguous', 'acceptable': ['tool:Python']}}
    matches = [reading('tool:ipconfig'), reading('tool:Route'), reading('tool:Python'), reading('tool:Unlabelled')]
    matches = [replace(m, query=q) for m, q in zip(matches, ['TCP/IP', 'routing', 'Python', 'something'])]
    assert gold_wrong(matches, labels) == {'tool:ipconfig', 'tool:Route'}
