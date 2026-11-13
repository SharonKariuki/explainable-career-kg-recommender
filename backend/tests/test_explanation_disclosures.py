"""Explanation disclosures (Measured Matching C5, #161): every wording change, its fidelity rule,
and the C4 completeness criterion."""
from dataclasses import replace

import pytest

from recommender import evidence
from recommender.explanation import NEAR_TIE, ExplanationGenerator
from recommender.explanation_quality import completeness
from recommender.fidelity import check_fidelity

E10 = ['Hugging Face', 'Solidity', 'eMASS', 'Microsoft Azure Data Factory']
NETWORK = ['ICT network routing', 'forecast future ICT network needs', 'design computer network', 'TCP/IP']


@pytest.fixture(scope='module')
def engine():
    from recommender.engine import get_engine
    return get_engine()


def ranked(engine, skills):
    matches, recs = engine.rank(skills, top_k=None)
    return matches, recs, evidence.assess(engine, matches, recs)


def explain(*args, **kwargs):
    return ExplanationGenerator().explain(*args, **kwargs)


def with_close_runner_up(matches, query):
    """The reading of `query` as it reads once a margin threshold flags it (C3 sets the value)."""
    return [replace(m, uncertain=True, uncertainty_reasons=('close_runner_up',)) if m.query == query else m
            for m in matches]


def contribution_of(recommendation, query):
    return next(c for c in recommendation.skill_contributions if c.query == query)


def test_without_readings_or_evidence_the_text_is_as_before(engine):
    matches, recs, _ = ranked(engine, ['Python', 'statistics', 'machine learning'])
    assert explain(recs[0]).sentences == explain(recs[0], (), None).sentences
    assert explain(recs[0]).sentences[0].startswith(f'{recs[0].title} is a ')


def test_a_close_second_reading_is_disclosed_and_passes_fidelity(engine):
    matches, recs, assessment = ranked(engine, NETWORK)
    flagged = with_close_runner_up(matches, 'TCP/IP')
    reading = next(m for m in flagged if m.query == 'TCP/IP')
    r = next(r for r in recs if any(c.query == 'TCP/IP' for c in r.skill_contributions))
    x = explain(r, flagged, assessment)
    c = contribution_of(r, 'TCP/IP')
    sentence = (f"Your 'TCP/IP' was read as {c.skill_label}, but it is almost as close to "
                f'{reading.runner_up_label}, so treat that part with caution.')
    assert sentence in x.sentences
    assert check_fidelity(x, r, flagged).passed
    assert completeness(x, r, flagged)['C4_uncertain_matches_disclosed'] is True


def test_a_runner_up_name_is_allowed_only_in_its_caution_sentence(engine):
    matches, recs, assessment = ranked(engine, NETWORK)
    flagged = with_close_runner_up(matches, 'TCP/IP')
    reading = next(m for m in flagged if m.query == 'TCP/IP')
    r = next(r for r in recs if any(c.query == 'TCP/IP' for c in r.skill_contributions))
    x = explain(r, flagged, assessment)
    assert not check_fidelity(x, r).passed                               # without the readings it is not permitted
    stray = replace(x, sentences=x.sentences + (f'You may also know {reading.runner_up_label}.',))
    report = check_fidelity(stray, r, flagged)
    assert not report.passed and any(reading.runner_up_label in v for v in report.violations)


def test_a_shared_name_is_disclosed(engine):
    matches, recs, assessment = ranked(engine, ['Linear algebra', 'statistics', 'R'])
    shared = next(m for m in matches if m.query == 'Linear algebra')
    assert 'shared_name' in shared.uncertainty_reasons
    r = next(r for r in recs if any(c.query == 'Linear algebra' for c in r.skill_contributions))
    x = explain(r, matches, assessment)
    label = contribution_of(r, 'Linear algebra').skill_label
    assert (f"Your 'Linear algebra' matches the name of more than one skill here; it was read as {label}, "
            'so treat that part with caution.') in x.sentences
    assert check_fidelity(x, r, matches).passed
    assert completeness(x, r, matches)['C4_uncertain_matches_disclosed'] is True


def test_an_undisclosed_flag_fails_the_C4_criterion(engine):
    matches, recs, assessment = ranked(engine, ['Linear algebra', 'statistics', 'R'])
    r = next(r for r in recs if any(c.query == 'Linear algebra' for c in r.skill_contributions))
    bare = explain(r)                                                     # generated without the readings
    assert completeness(bare, r, matches)['C4_uncertain_matches_disclosed'] is False


def test_insufficient_evidence_replaces_the_fit_label(engine):
    matches, recs, assessment = ranked(engine, ['Python', 'SQL'])
    assert assessment['insufficient'] is True
    x = explain(recs[0], matches, assessment, rank=1)
    assert x.sentences[0] == (f'{recs[0].title} ranks 1 for your skills (score {recs[0].score:.2f}), '
                              'but your profile has too little specific information to judge fit.')
    assert not any(w in x.text for w in ('strong match', 'good match', 'possible match'))
    assert x.sentences[-1] == assessment['evidence']['advice']
    assert check_fidelity(x, recs[0], matches).passed
    assert completeness(x, recs[0], matches)['C1_fit_and_score'] is True


def test_skills_spread_across_areas_are_not_called_too_little(engine):
    matches, recs, assessment = ranked(engine, E10)
    assessment = evidence.assess(engine, matches, recs, evidence.FIXTURE_PARAMS)
    x = explain(recs[0], matches, assessment, rank=1)
    assert 'several different areas' in x.sentences[0] and 'too little' not in x.text


def test_near_tie_is_disclosed_only_when_flagged(engine):
    matches, recs, assessment = ranked(engine, NETWORK)
    assert NEAR_TIE in explain(recs[1], matches, assessment, 2, near_tie=True).sentences
    assert NEAR_TIE not in explain(recs[1], matches, assessment, 2, near_tie=False).sentences


@pytest.mark.parametrize('skills', [['Python', 'SQL'], NETWORK, E10, ['HTML', 'CSS', 'JavaScript', 'React'],
                                    ['playing guitar', 'teamwork']])
def test_no_explanation_claims_job_readiness(engine, skills):
    matches, recs, assessment = ranked(engine, skills)
    for rank, r in enumerate(recs[:5], 1):
        text = explain(r, matches, assessment, rank, near_tie=rank > 1).text.lower()
        for claim in ('ready for', 'job-ready', 'qualified for', 'guarantee', 'you will get', 'you are hired'):
            assert claim not in text
        assert check_fidelity(explain(r, matches, assessment, rank), r, matches).passed


def api_client(username):
    from rest_framework.test import APIClient
    client = APIClient()
    token = client.post('/api/auth/register/', {'username': username, 'password': 'career-guide-2026'},
                        format='json').data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    client.put('/api/profile/', {'skills': ['Python', 'SQL']}, format='json')
    return client


def test_the_api_shows_the_insufficient_wording_only_when_enabled(db, settings):
    settings.EXPLAIN_INSUFFICIENT_EVIDENCE = True
    client = api_client('c5-on')
    data = client.get('/api/recommendations/?top=3').data
    assert data['insufficient'] is True
    first = data['recommendations'][0]
    assert first['summary'].endswith('too little specific information to judge fit.')
    assert first['fit'] in ('strong', 'good', 'possible')                 # the fit field itself is unchanged
    detail = client.get(f"/api/recommendations/{first['career_code']}/").data
    assert detail['explanation'][0] == first['summary']


def test_by_default_the_api_reports_evidence_but_keeps_the_fit_wording(db):
    client = api_client('c5-off')
    data = client.get('/api/recommendations/?top=3').data
    assert data['insufficient'] is True and data['evidence']['reasons']    # still reported
    first = data['recommendations'][0]
    assert ' match for your skills (score ' in first['summary'] and 'too little' not in first['summary']
