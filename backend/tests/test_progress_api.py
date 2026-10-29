import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

PASSWORD = 'career-guide-2026'
NUMPY = 'tool:NumPy'


def signed_in(username='amina'):
    client = APIClient()
    token = client.post('/api/auth/register/', {'username': username, 'password': PASSWORD}, format='json').data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    return client


def put(client, skill_id, status):
    return client.put('/api/progress/', {'skill_id': skill_id, 'status': status}, format='json')


def test_progress_moves_from_learning_to_done_and_back_to_todo():
    client = signed_in()
    assert client.get('/api/progress/').data['skills'] == []
    response = put(client, NUMPY, 'learning')
    assert response.status_code == 200
    assert [(s['skill_id'], s['label'], s['status']) for s in response.data['skills']] == [(NUMPY, 'NumPy', 'learning')]
    assert put(client, NUMPY, 'done').data['skills'][0]['status'] == 'done'
    assert put(client, NUMPY, 'todo').data['skills'] == []


def test_progress_rejects_unknown_skills_and_statuses():
    client = signed_in()
    assert put(client, 'tool:Not a real tool', 'learning').status_code == 400
    assert put(client, 'career:15-2051.00', 'learning').status_code == 400  # a career, not a skill
    assert put(client, NUMPY, 'mastered').status_code == 400


def test_progress_belongs_to_its_owner():
    put(signed_in('amina'), NUMPY, 'done')
    assert signed_in('brian').get('/api/progress/').data['skills'] == []
