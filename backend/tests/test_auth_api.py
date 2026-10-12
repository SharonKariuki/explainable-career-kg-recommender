import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

PASSWORD = 'career-guide-2026'


@pytest.fixture
def client():
    return APIClient()


def register(client, username='amina', password=PASSWORD):
    return client.post('/api/auth/register/', {'username': username, 'password': password}, format='json')


def test_register_returns_a_token(client):
    response = register(client)
    assert response.status_code == 201
    assert response.data['username'] == 'amina'
    assert Token.objects.filter(key=response.data['token'], user__username='amina').exists()


def test_register_rejects_a_taken_username_and_a_weak_password(client):
    register(client)
    assert register(client, username='AMINA').status_code == 400
    weak = register(client, username='brian', password='123')
    assert weak.status_code == 400 and 'password' in str(weak.data).lower()


def test_login_returns_the_users_token(client):
    token = register(client).data['token']
    response = client.post('/api/auth/login/', {'username': 'amina', 'password': PASSWORD}, format='json')
    assert response.status_code == 200 and response.data['token'] == token


def test_login_rejects_a_wrong_password(client):
    register(client)
    response = client.post('/api/auth/login/', {'username': 'amina', 'password': 'wrong-password'}, format='json')
    assert response.status_code == 400 and 'token' not in response.data


def test_protected_endpoints_need_a_valid_token(client):
    assert client.get('/api/auth/me/').status_code == 401
    client.credentials(HTTP_AUTHORIZATION='Token not-a-real-token')
    assert client.get('/api/auth/me/').status_code == 401


def test_logout_revokes_the_token(client):
    token = register(client).data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    assert client.get('/api/auth/me/').data['username'] == 'amina'
    assert client.post('/api/auth/logout/').status_code == 204
    assert client.get('/api/auth/me/').status_code == 401


def test_a_stale_token_does_not_block_logging_in_again(client):
    token = register(client).data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    client.post('/api/auth/logout/')
    response = client.post('/api/auth/login/', {'username': 'amina', 'password': PASSWORD}, format='json')
    assert response.status_code == 200 and response.data['token'] != token
