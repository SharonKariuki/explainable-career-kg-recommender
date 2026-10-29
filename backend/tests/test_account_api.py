import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from core.models import SavedCareer

pytestmark = pytest.mark.django_db

PASSWORD = 'career-guide-2026'
NEW_PASSWORD = 'pathways-to-tech-27'


def signed_in(username='amina'):
    client = APIClient()
    token = client.post('/api/auth/register/', {'username': username, 'password': PASSWORD}, format='json').data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    return client


def change_password(client, current, new):
    return client.post('/api/auth/password/', {'current_password': current, 'new_password': new}, format='json')


def test_me_describes_the_account():
    data = signed_in().get('/api/auth/me/').data
    assert data['username'] == 'amina' and data['has_password'] and not data['google']


def test_updating_the_email():
    client = signed_in()
    assert client.patch('/api/auth/me/', {'email': 'amina@example.com'}, format='json').data['email'] == 'amina@example.com'
    assert client.patch('/api/auth/me/', {'email': 'not-an-email'}, format='json').status_code == 400


def test_changing_the_password_needs_the_current_one_and_replaces_the_token():
    client = signed_in()
    wrong = change_password(client, 'nope', NEW_PASSWORD)
    assert wrong.status_code == 400 and 'current_password' in wrong.data
    assert change_password(client, PASSWORD, '123').status_code == 400

    response = change_password(client, PASSWORD, NEW_PASSWORD)
    assert response.status_code == 200
    assert client.get('/api/auth/me/').status_code == 401  # the old token no longer works
    client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
    assert client.get('/api/auth/me/').status_code == 200
    login = APIClient().post('/api/auth/login/', {'username': 'amina', 'password': NEW_PASSWORD}, format='json')
    assert login.status_code == 200


def test_an_account_without_a_password_can_set_one():
    user = get_user_model().objects.create_user('kamau', 'kamau@example.com')  # as Google sign-in creates them
    client = APIClient()
    client.force_authenticate(user)
    assert client.get('/api/auth/me/').data['has_password'] is False
    assert client.post('/api/auth/password/', {'new_password': NEW_PASSWORD}, format='json').status_code == 200


def test_deleting_the_account_needs_the_username_and_removes_everything():
    client = signed_in()
    client.put('/api/saved/15-2051.00/')
    assert client.delete('/api/auth/me/', {'confirm': 'someone'}, format='json').status_code == 400
    assert client.delete('/api/auth/me/', {'confirm': 'amina'}, format='json').status_code == 204
    assert not get_user_model().objects.filter(username='amina').exists()
    assert not SavedCareer.objects.exists()
