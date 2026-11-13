"""Evidence safety rule (student-ready release): a strong or good label needs specific support."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from recommender import presentation as pr
from recommender.explanation import ExplanationGenerator, fit_level
from recommender.fidelity import check_fidelity
from recommender.matching import SkillMatch


class FakeKG:
    def __init__(self, df):
        self.df = df

    def careers_requiring(self, s):
        return {f'career:{i}': 1.0 for i in range(self.df[s])}


def reading(node, sim=0.9, uncertain=False):
    return SkillMatch(query=node, node_id=node, node_label=node, matched_text=node, similarity=sim,
                      low_confidence=sim < 0.6, uncertain=uncertain)


def career(skills, score):
    return SimpleNamespace(score=score, skill_contributions=tuple(SimpleNamespace(skill_id=s) for s in skills))


P = pr.PresentationParams(max_careers=10, min_support=2)
KG = FakeKG({'a': 2, 'b': 3, 'generic': 24, 'c': 5})


def test_a_strong_score_keeps_its_label_only_with_two_specific_skills():
    assert pr.shown_fit(KG, [reading('a'), reading('b')], career('ab', 0.7), P) == ('strong', 2)
    assert pr.shown_fit(KG, [reading('a'), reading('generic')], career('a generic'.split(), 0.7), P) == ('possible', 1)


def test_uncertain_or_low_similarity_readings_are_not_support():
    assert pr.shown_fit(KG, [reading('a'), reading('b', uncertain=True)], career('ab', 0.5), P) == ('possible', 1)
    assert pr.shown_fit(KG, [reading('a'), reading('b', sim=0.55)], career('ab', 0.5), P) == ('possible', 1)


def test_a_possible_score_is_never_raised():
    assert pr.shown_fit(KG, [reading('a'), reading('b'), reading('c')], career('abc', 0.2), P) == ('possible', 3)


@pytest.fixture(scope='module')
def engine():
    from recommender.engine import get_engine
    return get_engine()


def test_generic_skills_are_shown_as_a_possible_match_with_a_reason(engine):
    matches, ranked = engine.rank(['Python', 'SQL'], top_k=None)
    top = ranked[0]
    shown = pr.shown_fit(engine.kg, matches, top)
    assert fit_level(top.score) in ('strong', 'good') and shown[0] == 'possible'
    x = ExplanationGenerator().explain(top, matches, rank=1, display=shown)
    assert x.sentences[0].startswith(f'{top.title} is a possible match for your skills')
    assert pr_sentence_in(x, shown[1])
    assert check_fidelity(x, top, matches).passed


def pr_sentence_in(explanation, support):
    from recommender.explanation import limited_evidence_sentence
    return limited_evidence_sentence(support) in explanation.sentences


def test_specific_skills_keep_the_label(engine):
    skills = ['ICT network routing', 'forecast future ICT network needs', 'design computer network']
    matches, ranked = engine.rank(skills, top_k=None)
    shown = pr.shown_fit(engine.kg, matches, ranked[0])
    assert shown == (fit_level(ranked[0].score), shown[1]) and shown[1] >= 2
    x = ExplanationGenerator().explain(ranked[0], matches, rank=1, display=shown)
    assert not any('possible direction' in s for s in x.sentences)


@pytest.mark.django_db
def test_the_api_and_history_report_the_shown_label():
    from rest_framework.test import APIClient
    client = APIClient()
    token = client.post('/api/auth/register/', {'username': 'thin', 'password': 'career-guide-2026'},
                        format='json').data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    client.put('/api/profile/', {'skills': ['Python', 'SQL']}, format='json')
    top = client.get('/api/recommendations/?top=3').data['recommendations'][0]
    assert top['fit'] in ('strong', 'good') and top['fit_shown'] == 'possible' and top['evidence_support'] <= 1
    assert top['summary'].startswith(f"{top['title']} is a possible match")
    detail = client.get(f"/api/recommendations/{top['career_code']}/").data
    assert detail['fit_shown'] == 'possible' and detail['explanation'][0] == top['summary']
    run = client.get('/api/history/').data['runs'][0]
    stored = client.get(f"/api/history/{run['id']}/").data
    first = next(r for r in stored['recommendations'] if r['career_code'] == top['career_code'])
    assert first['fit'] == 'possible'
