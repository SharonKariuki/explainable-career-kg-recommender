"""The optional full name: at registration, from Google, and edited in Settings."""

from unittest import mock

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

PASSWORD = 'career-guide-2026'


def register(**extra):
    client = APIClient()
    response = client.post('/api/auth/register/', {'username': 'amina', 'password': PASSWORD, **extra}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
    return client


def test_registration_keeps_the_full_name():
    client = register(name=' Amina Wanjiru ')
    assert client.get('/api/auth/me/').data['name'] == 'Amina Wanjiru'


def test_the_name_is_optional():
    assert register().get('/api/auth/me/').data['name'] == ''


def test_name_and_email_can_be_changed_together_or_alone():
    client = register(email='a@example.com')
    assert client.patch('/api/auth/me/', {'name': 'Amina W.'}, format='json').data['email'] == 'a@example.com'
    data = client.patch('/api/auth/me/', {'name': 'Amina Wanjiru', 'email': 'amina@example.com'}, format='json').data
    assert (data['name'], data['email']) == ('Amina Wanjiru', 'amina@example.com')
    assert client.patch('/api/auth/me/', {'name': 'x' * 151}, format='json').status_code == 400


@override_settings(GOOGLE_CLIENT_ID='test-client')
def test_google_sign_up_takes_the_name_from_google():
    claims = {'sub': '123', 'email': 'baraka@example.com', 'email_verified': True, 'name': 'Baraka Otieno'}
    with mock.patch('core.serializers.id_token.verify_oauth2_token', return_value=claims):
        token = APIClient().post('/api/auth/google/', {'credential': 'x'}, format='json').data['token']
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    assert client.get('/api/auth/me/').data['name'] == 'Baraka Otieno'
