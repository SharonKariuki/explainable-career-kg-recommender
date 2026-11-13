"""The whole student journey over real HTTP (release readiness, P4).

pytest-django's live server runs the API on a real port against the test database, and every
call below goes through the network stack with token authentication, as the web app's calls do.
It covers each route the app uses, in the order a new student meets them.
"""
import pytest
import requests

pytestmark = pytest.mark.django_db(transaction=True)

PASSWORD = 'career-guide-2026'
SKILLS = ['Python', 'SQL', 'Tableau', 'statistics', 'Power BI']


def test_a_student_journey_over_http(live_server):
    api = f'{live_server.url}/api'
    s = requests.Session()

    # Sign up, and the session knows who you are.
    r = s.post(f'{api}/auth/register/', json={'username': 'achieng', 'password': PASSWORD}, timeout=60)
    assert r.status_code in (200, 201), r.text
    s.headers['Authorization'] = f"Token {r.json()['token']}"
    assert s.get(f'{api}/auth/me/', timeout=60).json()['username'] == 'achieng'

    # An empty profile has no recommendations yet.
    assert s.get(f'{api}/recommendations/', timeout=60).json()['recommendations'] == []

    # Autocomplete, then save skills and background.
    assert s.get(f'{api}/skills/', params={'q': 'pyth'}, timeout=60).json()['results']
    r = s.put(f'{api}/profile/', json={'skills': SKILLS, 'education_level': 'undergraduate',
                                      'field_of_study': 'Statistics', 'interests': 'dashboards and reporting'},
              timeout=60)
    assert r.status_code == 200 and r.json()['skills'] == SKILLS

    # Recommendations: ranked, explained, with the readings and the evidence report.
    data = s.get(f'{api}/recommendations/', params={'top': 5}, timeout=120).json()
    recs = data['recommendations']
    assert len(recs) == 5 and [r['rank'] for r in recs] == [1, 2, 3, 4, 5]
    assert recs[0]['domain'] == 'data science' and recs[0]['summary'] and recs[0]['reason']
    assert {m['query'] for m in data['matches']} == set(SKILLS)
    assert isinstance(data['insufficient'], bool) and data['evidence']['version'] == 'evidence-v1'
    for text in (r['summary'] for r in recs):                         # the default wording is unchanged
        assert 'too little specific information' not in text

    # One career in detail: explanation, contributions, gap.
    code = recs[0]['career_code']
    detail = s.get(f'{api}/recommendations/{code}/', timeout=120).json()
    assert detail['explanation'][0] == recs[0]['summary'] and detail['skills_gap'] and detail['skill_contributions']

    # The catalogue, and a career page marking the student's skills.
    catalogue = s.get(f'{api}/careers/', timeout=60).json()
    assert len(catalogue['careers']) == 24
    page = s.get(f'{api}/careers/{code}/', timeout=120).json()
    assert page['title'] == recs[0]['title'] and any(item['have'] for item in page['your_skills'])

    # Save it, see it saved, then remove it.
    assert s.put(f'{api}/saved/{code}/', timeout=60).status_code in (200, 201)
    assert [c['career_code'] for c in s.get(f'{api}/saved/', timeout=120).json()['careers']] == [code]
    assert s.delete(f'{api}/saved/{code}/', timeout=60).status_code == 204

    # Track progress on a gap skill.
    gap_skill = detail['skills_gap'][0]['skill_id']
    assert s.put(f'{api}/progress/', json={'skill_id': gap_skill, 'status': 'learning'},
                 timeout=60).status_code == 200
    assert gap_skill in {p['skill_id'] for p in s.get(f'{api}/progress/', timeout=60).json()['skills']}

    # History records the saved profile, and a run opens.
    runs = s.get(f'{api}/history/', timeout=60).json()['runs']
    assert runs
    assert s.get(f"{api}/history/{runs[0]['id']}/", timeout=60).status_code == 200

    # Change the password, sign out, sign back in with the new one.
    # The change issues a new token (anyone holding the old one is signed out), as the client expects.
    new_password = 'career-guide-2027'
    old = dict(s.headers)
    r = s.post(f'{api}/auth/password/', json={'current_password': PASSWORD, 'new_password': new_password}, timeout=60)
    assert r.status_code == 200 and r.json()['token']
    assert requests.get(f'{api}/profile/', headers=old, timeout=60).status_code == 401
    s.headers['Authorization'] = f"Token {r.json()['token']}"
    assert s.post(f'{api}/auth/logout/', timeout=60).status_code == 204
    assert requests.get(f'{api}/profile/', headers=s.headers, timeout=60).status_code == 401
    r = requests.post(f'{api}/auth/login/', json={'username': 'achieng', 'password': new_password}, timeout=60)
    assert r.status_code == 200 and r.json()['token']

    # Update the account, then delete it: the token stops working.
    s.headers['Authorization'] = f"Token {r.json()['token']}"
    assert s.patch(f'{api}/auth/me/', json={'name': 'Achieng O.'}, timeout=60).json()['name'] == 'Achieng O.'
    assert s.delete(f'{api}/auth/me/', json={'confirm': 'achieng'}, timeout=60).status_code == 204
    assert s.get(f'{api}/profile/', timeout=60).status_code == 401
