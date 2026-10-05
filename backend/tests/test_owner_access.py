"""A user can only ever see or change their own profile and recommendations."""

import pytest
from rest_framework.test import APIClient

from core.models import SkillProfile

pytestmark = pytest.mark.django_db

PASSWORD = 'career-guide-2026'


def signed_in(username):
    client = APIClient()
    data = client.post('/api/auth/register/', {'username': username, 'password': PASSWORD}, format='json').data
    client.credentials(HTTP_AUTHORIZATION=f"Token {data['token']}")
    return client


@pytest.fixture
def amina():
    client = signed_in('amina')
    client.put('/api/profile/', {'skills': ['Python', 'machine learning', 'statistics']}, format='json')
    return client


@pytest.fixture
def brian():
    client = signed_in('brian')
    client.put('/api/profile/', {'skills': ['Kali Linux', 'penetration testing']}, format='json')
    return client


def test_each_user_sees_only_their_own_profile(amina, brian):
    assert amina.get('/api/profile/').data['skills'] == ['Python', 'machine learning', 'statistics']
    assert brian.get('/api/profile/').data['skills'] == ['Kali Linux', 'penetration testing']


def test_each_user_gets_recommendations_for_their_own_skills(amina, brian):
    assert amina.get('/api/recommendations/').data['recommendations'][0]['title'] == 'Data Scientists'
    assert brian.get('/api/recommendations/').data['recommendations'][0]['title'] == 'Penetration Testers'


def test_saving_a_profile_cannot_target_another_user(amina, brian):
    amina_id = SkillProfile.objects.get(user__username='amina').user_id
    brian.put('/api/profile/', {'skills': ['COBOL'], 'user': amina_id, 'user_id': amina_id}, format='json')
    assert SkillProfile.objects.get(user__username='amina').skills == ['Python', 'machine learning', 'statistics']
    assert SkillProfile.objects.get(user__username='brian').skills == ['COBOL']


def test_query_parameters_cannot_select_another_user(amina, brian):
    amina_id = SkillProfile.objects.get(user__username='amina').user_id
    for url in (f'/api/profile/?user={amina_id}', f'/api/recommendations/?user={amina_id}&username=amina'):
        assert 'machine learning' not in str(brian.get(url).data)


def test_a_career_only_another_user_was_recommended_is_not_found(amina, brian):
    # Statisticians is in Amina's recommendations but not reachable from Brian's skills.
    assert amina.get('/api/recommendations/15-2041.00/').status_code == 200
    assert brian.get('/api/recommendations/15-2041.00/').status_code == 404


def test_without_a_valid_token_nothing_is_visible(amina):
    anonymous = APIClient()
    for url in ('/api/profile/', '/api/recommendations/', '/api/recommendations/15-2051.00/'):
        assert anonymous.get(url).status_code == 401
    assert anonymous.put('/api/profile/', {'skills': ['x']}, format='json').status_code == 401


def test_a_logged_out_token_no_longer_works(amina):
    amina.post('/api/auth/logout/')
    assert amina.get('/api/profile/').status_code == 401
    assert amina.get('/api/recommendations/').status_code == 401
