"""The administrators' site: access, the system report and the data catalogue."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from core.report import system_report

pytestmark = pytest.mark.django_db

PASSWORD = 'career-guide-2026'


def admin_client(client):
    get_user_model().objects.create_superuser('admin', 'admin@example.com', PASSWORD)
    client.login(username='admin', password=PASSWORD)
    return client


def make_user(username, skills, saved=()):
    api = APIClient()
    token = api.post('/api/auth/register/', {'username': username, 'password': PASSWORD}, format='json').data['token']
    api.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    api.put('/api/profile/', {'skills': skills}, format='json')
    for code in saved:
        api.put(f'/api/saved/{code}/')


def test_admin_pages_need_a_staff_login(client):
    for url in ('/admin/', '/admin/report/', '/admin/catalogue/'):
        response = client.get(url)
        assert response.status_code == 302 and '/admin/login/' in response['Location']
    get_user_model().objects.create_user('student', password=PASSWORD)
    client.login(username='student', password=PASSWORD)
    assert client.get('/admin/report/').status_code == 302


def test_admins_manage_users_and_their_data(client):
    client = admin_client(client)
    make_user('amina', ['Python', 'SQL'])
    index = client.get('/admin/').content.decode()
    assert 'System report' in index and 'Careers and skills' in index
    for url in ('/admin/auth/user/', '/admin/core/skillprofile/', '/admin/core/savedcareer/',
                '/admin/core/skillprogress/', '/admin/core/googleaccount/'):
        assert client.get(url).status_code == 200, url
    assert 'amina' in client.get('/admin/core/skillprofile/').content.decode()


def test_the_report_counts_users_profiles_and_choices(client):
    make_user('amina', ['Python', 'machine learning', 'statistics'], saved=['15-2051.00'])
    make_user('baraka', ['Python', 'basket weaving'])
    report = system_report()
    assert report['users']['total'] == 2 and report['users']['last_7_days'] == 2
    assert report['profiles'] == {'with_skills': 2, 'cold_start': 2, 'cold_start_limit': 3, 'mean_skills': 2.5}
    assert ('Data Scientists', 1) in report['first_choice'] and len(report['first_choice']) == 2
    assert report['saved'] == [('Data Scientists', 1)]
    assert report['declared'][0] == ('Python', 2)
    assert [u['skill'] for u in report['unmatched']] == ['basket weaving']


def test_report_and_catalogue_pages_render(client):
    client = admin_client(client)
    make_user('amina', ['Python', 'SQL'])
    report = client.get('/admin/report/').content.decode()
    assert 'Cold-start profiles' in report and 'Skills with no close match' in report
    catalogue = client.get('/admin/catalogue/').content.decode()
    assert 'Data Scientists' in catalogue and 'read-only' in catalogue
