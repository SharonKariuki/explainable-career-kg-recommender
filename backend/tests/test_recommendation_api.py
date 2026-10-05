import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

PASSWORD = 'career-guide-2026'
DATA_SKILLS = ['Python', 'machine learning', 'statistics']


def signed_in(username='amina'):
    client = APIClient()
    token = client.post('/api/auth/register/', {'username': username, 'password': PASSWORD}, format='json').data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    return client


def test_a_new_user_starts_with_an_empty_profile():
    response = signed_in().get('/api/profile/')
    assert response.status_code == 200 and response.data['skills'] == []


def test_saving_skills_cleans_them():
    client = signed_in()
    response = client.put('/api/profile/', {'skills': [' Python ', 'python', '', 'SQL']}, format='json')
    assert response.status_code == 200 and response.data['skills'] == ['Python', 'SQL']
    assert client.get('/api/profile/').data['skills'] == ['Python', 'SQL']


def test_invalid_profiles_are_rejected():
    client = signed_in()
    assert client.put('/api/profile/', {'skills': 'Python'}, format='json').status_code == 400
    assert client.put('/api/profile/', {'skills': ['x' * 101]}, format='json').status_code == 400
    assert client.put('/api/profile/', {'skills': [f's{i}' for i in range(31)]}, format='json').status_code == 400


def test_recommendations_rank_the_saved_profile():
    client = signed_in()
    client.put('/api/profile/', {'skills': DATA_SKILLS}, format='json')
    response = client.get('/api/recommendations/?top=5')
    assert response.status_code == 200
    data = response.data
    assert data['skills'] == DATA_SKILLS
    assert [m['query'] for m in data['matches']] == DATA_SKILLS
    first = data['recommendations'][0]
    assert first['title'] == 'Data Scientists' and first['rank'] == 1 and first['career_code'] == '15-2051.00'
    assert set(first['components']) == {'coverage', 'profile_similarity', 'graph_proximity'}
    assert first['summary'].startswith('Data Scientists is')
    assert len(data['recommendations']) == 5


def test_an_empty_profile_has_no_recommendations():
    data = signed_in().get('/api/recommendations/').data
    assert data['matches'] == [] and data['recommendations'] == []


def test_top_must_be_a_sensible_number():
    client = signed_in()
    assert client.get('/api/recommendations/?top=abc').status_code == 400
    assert client.get('/api/recommendations/?top=0').status_code == 400


def test_detail_has_the_explanation_and_skills_gap():
    client = signed_in()
    client.put('/api/profile/', {'skills': DATA_SKILLS}, format='json')
    response = client.get('/api/recommendations/15-2051.00/')
    assert response.status_code == 200
    data = response.data
    assert data['title'] == 'Data Scientists' and data['rank'] == 1
    assert data['explanation'][0] == data['summary']
    weights = data['weights']
    assert sum(weights.values()) == pytest.approx(1)
    assert data['score'] == pytest.approx(sum(weights[k] * data['components'][k] for k in weights))
    assert {c['query'] for c in data['skill_contributions']} <= set(DATA_SKILLS)
    assert {c['requirement'] for c in data['skill_contributions']} <= {'Core requirement', 'Important', 'Supporting'}
    gap = [g['label'] for g in data['skills_gap']]
    assert 'NumPy' in gap and not set(gap) & {'Python', 'statistics', 'machine learning'}


def test_detail_for_a_career_not_recommended_is_404():
    client = signed_in()
    client.put('/api/profile/', {'skills': ['Solidity']}, format='json')
    assert client.get('/api/recommendations/15-2041.00/').status_code == 404
    assert client.get('/api/recommendations/not-a-career/').status_code == 404


def test_served_explanations_pass_the_fidelity_check():
    from recommender.engine import get_engine
    from recommender.explanation import ExplanationGenerator
    from recommender.fidelity import check_fidelity

    client = signed_in()
    client.put('/api/profile/', {'skills': ['HTML', 'CSS', 'playing guitar']}, format='json')
    served = client.get('/api/recommendations/?top=3').data['recommendations']
    _, ranked = get_engine().rank(['HTML', 'CSS', 'playing guitar'], top_k=3)
    for item, r in zip(served, ranked):
        assert item['title'] == r.title
        assert check_fidelity(ExplanationGenerator().explain(r), r).passed
