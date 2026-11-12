"""The optional background (interests, field of study, experience) on the profile and in the ranking."""

from dataclasses import replace

import pytest
from rest_framework.test import APIClient

from recommender.engine import DEFAULT_PARAMS, get_engine
from recommender.explanation import ExplanationGenerator
from recommender.fidelity import check_fidelity

PASSWORD = 'career-guide-2026'
SKILLS = ['Python', 'SQL', 'Linux']
DATA_BACKGROUND = 'I enjoy finding patterns in data and building statistical models to make predictions.'


@pytest.fixture(scope='module')
def engine():
    return get_engine()


def test_without_a_background_the_ranking_is_unchanged(engine):
    _, plain = engine.rank(SKILLS)
    _, blank = engine.rank(SKILLS, background='   ')
    assert [(r.career_id, r.score) for r in plain] == [(r.career_id, r.score) for r in blank]
    assert all(r.components.background_similarity is None for r in plain)


def test_weight_zero_matches_the_skills_only_ranking(engine):
    _, plain = engine.rank(SKILLS)
    _, zero = engine.rank(SKILLS, params=replace(DEFAULT_PARAMS, background_weight=0.0), background=DATA_BACKGROUND)
    assert [r.career_id for r in plain] == [r.career_id for r in zero]
    assert [r.score for r in plain] == pytest.approx([r.score for r in zero])


def test_background_is_blended_into_the_score(engine):
    _, ranked = engine.rank(SKILLS, background=DATA_BACKGROUND)
    p = DEFAULT_PARAMS
    for r in ranked:
        c = r.components
        assert 0 <= c.background_similarity <= 1
        skills_score = (p.coverage_weight * c.coverage + p.similarity_weight * c.profile_similarity
                        + p.proximity_weight * c.graph_proximity)
        assert r.score == pytest.approx((1 - p.background_weight) * skills_score + p.background_weight * c.background_similarity)


def test_the_career_closest_to_the_background_moves_up(engine):
    _, plain = engine.rank(SKILLS, top_k=None)
    _, with_background = engine.rank(SKILLS, top_k=None, background=DATA_BACKGROUND)
    closest = max(with_background, key=lambda r: r.components.background_similarity).career_id
    before = [r.career_id for r in plain].index(closest)
    after = [r.career_id for r in with_background].index(closest)
    assert after < before


def test_explanations_with_a_background_stay_faithful(engine):
    _, ranked = engine.rank(SKILLS, top_k=5, background=DATA_BACKGROUND)
    for r in ranked:
        explanation = ExplanationGenerator().explain(r)
        assert 'Your interests, studies and experience' in explanation.text
        assert 'Your background counts for' in explanation.text
        assert check_fidelity(explanation, r).passed


def signed_in(username):
    client = APIClient()
    token = client.post('/api/auth/register/', {'username': username, 'password': PASSWORD}, format='json').data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    return client


@pytest.mark.django_db
def test_background_fields_are_saved_and_trimmed():
    client = signed_in('wanjiru')
    response = client.put('/api/profile/', {
        'skills': SKILLS, 'education_level': 'undergraduate', 'field_of_study': ' Statistics ',
        'interests': 'Data and puzzles', 'experience': '',
    }, format='json')
    assert response.status_code == 200
    profile = client.get('/api/profile/').data
    assert profile['education_level'] == 'undergraduate' and profile['field_of_study'] == 'Statistics'
    assert profile['interests'] == 'Data and puzzles' and profile['experience'] == ''


@pytest.mark.django_db
def test_saving_only_skills_keeps_the_background():
    client = signed_in('otieno')
    client.put('/api/profile/', {'skills': SKILLS, 'interests': 'Data and puzzles'}, format='json')
    client.put('/api/profile/', {'skills': SKILLS + ['Excel']}, format='json')
    profile = client.get('/api/profile/').data
    assert profile['interests'] == 'Data and puzzles' and 'Excel' in profile['skills']


@pytest.mark.django_db
def test_invalid_background_is_rejected():
    client = signed_in('akinyi')
    assert client.put('/api/profile/', {'education_level': 'phd-in-everything'}, format='json').status_code == 400
    assert client.put('/api/profile/', {'interests': 'x' * 1001}, format='json').status_code == 400


@pytest.mark.django_db
def test_recommendations_use_the_saved_background():
    client = signed_in('kamau')
    client.put('/api/profile/', {'skills': SKILLS, 'interests': DATA_BACKGROUND}, format='json')
    top = client.get('/api/recommendations/?top=3').data['recommendations'][0]
    assert top['components']['background_similarity'] is not None
    detail = client.get(f"/api/recommendations/{top['career_code']}/").data
    assert detail['weights']['background'] == DEFAULT_PARAMS.background_weight
    assert any('Your interests, studies and experience' in s for s in detail['explanation'])


@pytest.mark.django_db
def test_without_a_background_the_detail_has_no_background_weight():
    client = signed_in('njeri')
    client.put('/api/profile/', {'skills': SKILLS}, format='json')
    top = client.get('/api/recommendations/?top=1').data['recommendations'][0]
    assert top['components']['background_similarity'] is None
    assert client.get(f"/api/recommendations/{top['career_code']}/").data['weights']['background'] is None
