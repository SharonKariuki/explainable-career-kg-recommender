import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core import serializers

pytestmark = pytest.mark.django_db

CLIENT_ID = 'test-client.apps.googleusercontent.com'
CLAIMS = {'sub': '1001', 'email': 'amina@gmail.com', 'email_verified': True}


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def google(settings, monkeypatch):
    """Stands in for Google: the credential string names the claims it carries."""
    settings.GOOGLE_CLIENT_ID = CLIENT_ID
    tokens = {'good': CLAIMS, 'unverified': {**CLAIMS, 'sub': '1002', 'email_verified': False}}

    def verify(credential, request, audience):
        assert audience == CLIENT_ID
        if credential not in tokens:
            raise ValueError('Token used too late')
        return tokens[credential]

    monkeypatch.setattr(serializers.id_token, 'verify_oauth2_token', verify)
    return tokens


def google_login(client, credential='good'):
    return client.post('/api/auth/google/', {'credential': credential}, format='json')


def test_first_google_sign_in_creates_an_account(client, google):
    response = google_login(client)
    assert response.status_code == 200 and response.data['username'] == 'amina'
    user = get_user_model().objects.get(username='amina')
    assert user.email == 'amina@gmail.com' and not user.has_usable_password()
    assert Token.objects.filter(key=response.data['token'], user=user).exists()


def test_signing_in_again_returns_the_same_account(client, google):
    token = google_login(client).data['token']
    assert google_login(client).data['token'] == token
    assert get_user_model().objects.count() == 1


def test_google_sign_in_never_takes_over_a_password_account_with_that_email(client, google):
    client.post('/api/auth/register/', {
        'username': 'amina', 'email': 'amina@gmail.com', 'password': 'career-guide-2026',
    }, format='json')
    response = google_login(client)
    assert response.data['username'] == 'amina2'
    assert not hasattr(get_user_model().objects.get(username='amina'), 'google_account')


def test_google_sign_in_rejects_bad_and_unverified_tokens(client, google):
    assert google_login(client, 'forged').status_code == 400
    assert google_login(client, 'unverified').status_code == 400
    assert get_user_model().objects.count() == 0


def test_google_sign_in_is_off_without_a_client_id(client, settings):
    settings.GOOGLE_CLIENT_ID = ''
    response = google_login(client)
    assert response.status_code == 400 and 'not set up' in str(response.data)
