"""System tests: realistic usage scenarios through the API, end to end."""

import time

import pytest
from rest_framework.test import APIClient

from recommender.engine import get_engine
from recommender.explanation import ExplanationGenerator
from recommender.fidelity import check_fidelity

pytestmark = pytest.mark.django_db

PASSWORD = 'career-guide-2026'


def new_user(username):
    client = APIClient()
    token = client.post('/api/auth/register/', {'username': username, 'password': PASSWORD}, format='json').data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    return client


def save(client, skills):
    response = client.put('/api/profile/', {'skills': skills}, format='json')
    assert response.status_code == 200
    return response.data['skills']


def test_a_new_users_full_journey():
    client = new_user('wanjiru')
    assert client.get('/api/recommendations/').data['recommendations'] == []

    save(client, ['Python', 'SQL', 'Tableau'])
    top = client.get('/api/recommendations/?top=5').data['recommendations']
    assert len(top) == 5 and top[0]['domain'] == 'data science'

    detail = client.get(f"/api/recommendations/{top[0]['career_code']}/").data
    assert detail['explanation'] and detail['skills_gap'] and detail['skill_contributions']

    assert client.post('/api/auth/logout/').status_code == 204
    assert client.get('/api/recommendations/').status_code == 401
    again = client.post('/api/auth/login/', {'username': 'wanjiru', 'password': PASSWORD}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Token {again.data['token']}")
    assert client.get('/api/profile/').data['skills'] == ['Python', 'SQL', 'Tableau']


def test_a_single_skill_still_gets_explained_recommendations():
    client = new_user('otieno')
    save(client, ['Kali Linux'])
    top = client.get('/api/recommendations/?top=3').data['recommendations']
    assert top[0]['title'] == 'Penetration Testers'
    assert client.get(f"/api/recommendations/{top[0]['career_code']}/").data['explanation']


def test_unrelated_skills_are_flagged_and_disclosed():
    client = new_user('achieng')
    save(client, ['cooking', 'playing guitar', 'Python'])
    data = client.get('/api/recommendations/').data
    uncertain = {m['query'] for m in data['matches'] if m['low_confidence']}
    assert 'playing guitar' in uncertain and 'Python' not in uncertain
    for item in data['recommendations'][:3]:
        detail = client.get(f"/api/recommendations/{item['career_code']}/").data
        for c in detail['skill_contributions']:
            if c['low_confidence']:
                assert any(f"'{c['query']}' was only loosely matched" in s for s in detail['explanation'])


def test_awkward_input_is_cleaned_not_rejected():
    client = new_user('kamau')
    skills = save(client, ['  C++ ', 'c++', 'Node.js', 'R', 'ASP.NET', 'Café management', ''])
    assert skills == ['C++', 'Node.js', 'R', 'ASP.NET', 'Café management']
    assert client.get('/api/recommendations/').status_code == 200


def test_changing_the_profile_changes_the_recommendations():
    client = new_user('njeri')
    save(client, ['Python', 'machine learning', 'statistics'])
    before = client.get('/api/recommendations/').data['recommendations'][0]['title']
    save(client, ['penetration testing', 'Kali Linux', 'Metasploit'])
    after = client.get('/api/recommendations/').data['recommendations'][0]['title']
    assert (before, after) == ('Data Scientists', 'Penetration Testers')


def test_a_full_profile_is_served_quickly():
    client = new_user('mutua')
    save(client, [
        'Python', 'Java', 'SQL', 'Docker', 'Kubernetes', 'AWS', 'Linux', 'Git', 'React', 'JavaScript',
        'HTML', 'CSS', 'machine learning', 'statistics', 'Tableau', 'Excel', 'networking', 'firewalls',
        'project management', 'Agile', 'testing', 'Selenium', 'C++', 'R', 'MongoDB', 'PostgreSQL',
        'communication', 'teamwork', 'problem solving', 'data visualisation',
    ])
    client.get('/api/recommendations/')  # warm
    start = time.perf_counter()
    data = client.get('/api/recommendations/?top=24').data
    assert time.perf_counter() - start < 2
    assert len(data['matches']) == 30 and data['recommendations']


@pytest.mark.parametrize('skills', [
    ['HTML', 'CSS', 'JavaScript'],
    ['good with people', 'fixing computers', 'Windows'],
    ['Solidity'],
])
def test_every_served_explanation_is_faithful(skills):
    client = new_user('fidelity')
    save(client, skills)
    served = client.get('/api/recommendations/?top=10').data['recommendations']
    _, ranked = get_engine().rank(skills, top_k=10)
    assert [s['title'] for s in served] == [r.title for r in ranked]
    for r in ranked:
        assert check_fidelity(ExplanationGenerator().explain(r), r).passed
