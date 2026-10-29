import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

PASSWORD = 'career-guide-2026'
DATA_SKILLS = ['Python', 'machine learning', 'statistics']
DATA_SCIENTISTS = '15-2051.00'


def signed_in(username='amina', skills=()):
    client = APIClient()
    token = client.post('/api/auth/register/', {'username': username, 'password': PASSWORD}, format='json').data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    if skills:
        client.put('/api/profile/', {'skills': list(skills)}, format='json')
    return client


def test_the_catalogue_lists_every_career_without_skills():
    data = signed_in().get('/api/careers/').data
    assert len(data['careers']) == 24
    titles = [c['title'] for c in data['careers']]
    assert titles == sorted(titles)
    first = data['careers'][0]
    assert first['match'] is None and first['saved'] is False
    assert first['skill_count'] > 0 and first['description']


def test_the_catalogue_carries_the_users_ranking():
    careers = signed_in(skills=DATA_SKILLS).get('/api/careers/').data['careers']
    by_code = {c['career_code']: c for c in careers}
    assert by_code[DATA_SCIENTISTS]['match']['rank'] == 1


def test_a_career_page_works_for_any_career():
    client = signed_in(skills=['Solidity'])
    data = client.get('/api/careers/15-2041.00/').data  # Statisticians, not among this user's matches
    assert data['title'] == 'Statisticians' and data['match'] is None
    assert data['requirements'] and data['tools']
    assert {r['requirement'] for r in data['requirements']} <= {'Core requirement', 'Important', 'Supporting'}
    assert all(t['skill_type'] == 'tool' for t in data['tools'])
    assert client.get('/api/careers/not-a-career/').status_code == 404


def test_a_career_page_marks_the_skills_the_user_has():
    data = signed_in(skills=DATA_SKILLS).get(f'/api/careers/{DATA_SCIENTISTS}/').data
    assert 'Python' in [r['label'] for r in data['your_skills']]
    assert all(r['have'] for r in data['your_skills'])
    marked = {r['skill_id'] for r in data['requirements'] + data['tools'] if r['have']}
    assert marked <= {r['skill_id'] for r in data['your_skills']}


def test_saving_and_unsaving_a_career():
    client = signed_in()
    assert client.put(f'/api/saved/{DATA_SCIENTISTS}/').status_code == 200
    assert client.put(f'/api/saved/{DATA_SCIENTISTS}/').status_code == 200  # saving twice keeps one
    saved = client.get('/api/saved/').data['careers']
    assert [c['career_code'] for c in saved] == [DATA_SCIENTISTS] and saved[0]['saved']
    assert client.get(f'/api/careers/{DATA_SCIENTISTS}/').data['saved'] is True
    assert client.delete(f'/api/saved/{DATA_SCIENTISTS}/').status_code == 204
    assert client.get('/api/saved/').data['careers'] == []
    assert client.put('/api/saved/not-a-career/').status_code == 404


def test_saved_careers_belong_to_their_owner():
    amina = signed_in('amina')
    amina.put(f'/api/saved/{DATA_SCIENTISTS}/')
    assert signed_in('brian').get('/api/saved/').data['careers'] == []


def test_skill_search_puts_names_starting_with_the_query_first():
    results = signed_in().get('/api/skills/?q=pyth').data['results']
    assert results[0]['label'] == 'Python' and len(results) <= 8
    assert all('pyth' in r['label'].lower() for r in results)
    assert signed_in('brian').get('/api/skills/?q=').data['results'] == []


def test_the_catalogue_needs_a_token():
    assert APIClient().get('/api/careers/').status_code == 401
