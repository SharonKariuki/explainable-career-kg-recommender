"""The React application in a real browser, end to end (student-ready release).

The API runs on pytest-django's live server against the test database; `vite preview` serves the
production build (frontend/dist, from `npm run build`) and proxies /api to it, as in deployment.
Playwright drives Chromium through a student's journey on a desktop and a phone-sized viewport:
sign-up, an empty profile, an invalid skill, a thin profile (whose top match must not be called
strong or good), a specific profile, a career's explanation and skills plan, history, an API error,
account deletion and the refused sign-in afterwards. Uncaught page errors fail the test.

Skipped when Playwright, Node or the production build is not available. Screenshots go to
BROWSER_EVIDENCE_DIR when it is set.
"""
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

playwright = pytest.importorskip('playwright.sync_api')

FRONTEND = Path(__file__).resolve().parents[2] / 'frontend'
VITE = FRONTEND / 'node_modules' / 'vite' / 'bin' / 'vite.js'
PASSWORD = 'career-guide-2026'
THIN = ['Python', 'SQL']
SPECIFIC = ['ICT network routing', 'Cisco IOS', 'design computer network', 'forecast future ICT network needs']

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(shutil.which('node') is None or not VITE.exists() or not (FRONTEND / 'dist').exists(),
                       reason='needs Node, frontend/node_modules and a production build (npm run build)'),
]


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@pytest.fixture
def app(live_server):
    """The production build served on a free port, proxying /api to the live API server."""
    port = free_port()
    env = {**os.environ, 'API_PROXY_TARGET': live_server.url}
    server = subprocess.Popen(['node', str(VITE), 'preview', '--port', str(port), '--strictPort', '--host', '127.0.0.1'],
                              cwd=FRONTEND, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                socket.create_connection(('127.0.0.1', port), timeout=0.5).close()
                break
            except OSError:
                time.sleep(0.2)
        else:
            pytest.fail('vite preview did not start')
        yield f'http://127.0.0.1:{port}'
    finally:
        server.terminate()
        server.wait(timeout=20)


def shot(page, name):
    folder = os.environ.get('BROWSER_EVIDENCE_DIR')
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(folder) / f'{name}.png'), full_page=True)


def no_horizontal_scroll(page):
    return page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')


def sign_up(page, url, username):
    page.goto(f'{url}/#/signup')
    page.get_by_label('Username').fill(username)
    page.get_by_label('Password').fill(PASSWORD)
    page.get_by_role('button', name='Create account').click()
    page.wait_for_url('**/#/welcome')


def set_skills(page, url, skills):
    page.goto(f'{url}/#/profile')
    box = page.get_by_placeholder('Add a skill, e.g. SQL')
    box.wait_for()
    remove = page.get_by_role('button', name='Remove ')
    while remove.count():
        remove.first.click()
    for skill in skills:
        box.fill(skill)
        box.press('Enter')
    page.get_by_role('button', name='Save and see my careers').click()
    page.wait_for_url('**/#/matches')
    page.locator('li.card.result').first.wait_for()


@pytest.mark.parametrize('viewport', ['desktop', 'mobile'])
def test_a_student_journey_in_the_browser(app, viewport):
    errors = []
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        options = ({'viewport': {'width': 1280, 'height': 860}} if viewport == 'desktop' else
                   {'viewport': {'width': 390, 'height': 844}, 'is_mobile': True, 'has_touch': True,
                    'device_scale_factor': 3})
        page = browser.new_context(**options).new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        username = f'student-{viewport}'

        # Sign up and land on the welcome page.
        sign_up(page, app, username)
        shot(page, f'{viewport}-01-welcome')

        # An empty profile: matches point the student to their profile instead of failing.
        page.goto(f'{app}/#/matches')
        page.get_by_text('You have not listed any skills yet').wait_for()
        assert page.get_by_role('link', name='Add your skills').is_visible()
        shot(page, f'{viewport}-02-empty')

        # Invalid input is prevented: a skill longer than 100 characters cannot be typed, and a
        # 31st skill is refused with a visible message (the API's limits are 100 and 30).
        page.goto(f'{app}/#/profile')
        box = page.get_by_placeholder('Add a skill, e.g. SQL')
        box.fill('x' * 101)
        assert len(box.input_value()) == 100
        box.fill('')
        for i in range(31):
            box.fill(f'skill {i}')
            box.press('Enter')
        page.get_by_text('You can list up to 30 skills.').wait_for()
        shot(page, f'{viewport}-03-invalid')

        # A thin, generic profile: the top match is shown only as a possible match.
        set_skills(page, app, THIN)
        top = page.locator('li.card.result').first
        assert 'Possible match' in top.inner_text()
        assert 'Strong match' not in top.inner_text() and 'Good match' not in top.inner_text()
        shot(page, f'{viewport}-04-thin-profile')

        # A specific networking profile keeps a confident label.
        set_skills(page, app, SPECIFIC)
        top = page.locator('li.card.result').first
        assert 'Network' in top.inner_text() and ('Strong match' in top.inner_text() or 'Good match' in top.inner_text())
        assert no_horizontal_scroll(page)
        shot(page, f'{viewport}-05-matches')

        # A career's explanation and skills plan.
        top.get_by_role('link').first.click()
        page.wait_for_url('**/#/careers/*')
        page.get_by_role('tab', name='Why it fits').click() if page.get_by_role('tab', name='Why it fits').count() \
            else page.get_by_role('link', name='Why it fits').first.click()
        page.wait_for_url('**/fit')
        page.get_by_text('How this match was calculated').click()
        page.get_by_text('Full explanation').wait_for()
        text = page.locator('main').inner_text()
        assert 'match for your skills (score' in text                       # the explanation's first sentence
        assert 'not a percentage, a measure of how qualified you are' in text  # no job-readiness claim
        shot(page, f'{viewport}-06-why-it-fits')
        page.goto(page.url.replace('/fit', '/plan'))
        page.wait_for_timeout(500)
        assert page.locator('main').inner_text().strip()
        assert no_horizontal_scroll(page)
        shot(page, f'{viewport}-07-skills-plan')

        # History lists the saved profiles.
        page.goto(f'{app}/#/history')
        page.get_by_text('Network', exact=False).first.wait_for()
        shot(page, f'{viewport}-08-history')

        # An API failure shows an error instead of a blank page.
        page.route('**/api/recommendations/**', lambda route: route.fulfill(status=500, body='{}'))
        page.goto(f'{app}/#/matches')
        page.get_by_role('alert').first.wait_for()
        shot(page, f'{viewport}-09-api-error')
        page.unroute('**/api/recommendations/**')

        # Delete the account; signing in again is refused.
        page.goto(f'{app}/#/settings')
        page.get_by_role('button', name='Delete account…').click()
        page.get_by_label(f'Type {username} to confirm').fill(username)
        page.get_by_role('button', name='Delete my account').click()
        page.wait_for_url('**/#/**')
        page.goto(f'{app}/#/signin')
        page.get_by_label('Username').fill(username)
        page.get_by_label('Password').fill(PASSWORD)
        page.get_by_role('button', name='Sign in').click()
        page.get_by_role('alert').first.wait_for()
        shot(page, f'{viewport}-10-deleted')
        browser.close()
    assert errors == []
