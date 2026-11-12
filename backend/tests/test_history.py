"""Recommendation history: snapshots on save, listing, detail and owner-only access."""

import pytest
from rest_framework.test import APIClient

from core.models import Recommendation, RecommendationRun, SkillGap

pytestmark = pytest.mark.django_db

PASSWORD = 'career-guide-2026'
DATA_SKILLS = ['Python', 'machine learning', 'statistics']


def signed_in(username):
    client = APIClient()
    token = client.post('/api/auth/register/', {'username': username, 'password': PASSWORD}, format='json').data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    return client


def test_saving_a_profile_stores_a_snapshot_with_explanations_and_gaps():
    client = signed_in('amina')
    client.put('/api/profile/', {'skills': DATA_SKILLS}, format='json')
    run = RecommendationRun.objects.get()
    assert run.skills == DATA_SKILLS and run.background == ''
    recommendations = list(run.recommendations.all())
    assert len(recommendations) == 10 and recommendations[0].title == 'Data Scientists'
    assert [r.rank for r in recommendations] == list(range(1, 11))
    assert recommendations[0].explanation.sentences[0].startswith('Data Scientists is a')
    assert SkillGap.objects.filter(recommendation=recommendations[0]).exists()


def test_the_snapshot_matches_what_the_api_serves():
    client = signed_in('amina')
    client.put('/api/profile/', {'skills': DATA_SKILLS}, format='json')
    served = client.get('/api/recommendations/?top=10').data['recommendations']
    stored = Recommendation.objects.order_by('rank')
    assert [(r.career_code, round(r.score, 6)) for r in stored] == [(s['career_code'], round(s['score'], 6)) for s in served]


def test_saving_an_unchanged_profile_adds_no_snapshot():
    client = signed_in('amina')
    client.put('/api/profile/', {'skills': DATA_SKILLS}, format='json')
    client.put('/api/profile/', {'skills': DATA_SKILLS}, format='json')
    assert RecommendationRun.objects.count() == 1
    client.put('/api/profile/', {'interests': 'Finding patterns in data'}, format='json')
    assert RecommendationRun.objects.count() == 2
    assert RecommendationRun.objects.first().background == 'Finding patterns in data'


def test_an_empty_profile_stores_nothing():
    signed_in('amina').put('/api/profile/', {'skills': []}, format='json')
    assert not RecommendationRun.objects.exists()


def test_history_lists_runs_newest_first_and_shows_rank_changes():
    client = signed_in('amina')
    client.put('/api/profile/', {'skills': ['HTML', 'CSS']}, format='json')
    client.put('/api/profile/', {'skills': DATA_SKILLS}, format='json')
    runs = client.get('/api/history/').data['runs']
    assert len(runs) == 2 and runs[0]['skills'] == DATA_SKILLS
    assert runs[0]['changed'] is True and runs[1]['changed'] is False
    detail = client.get(f"/api/history/{runs[0]['id']}/").data
    assert detail['previous_id'] == runs[1]['id']
    first = detail['recommendations'][0]
    assert first['title'] == 'Data Scientists' and first['explanation'] and first['skill_gaps']
    assert 'previous_rank' in first


def test_history_is_owner_only_and_deleted_with_the_account():
    amina, baraka = signed_in('amina'), signed_in('baraka')
    amina.put('/api/profile/', {'skills': DATA_SKILLS}, format='json')
    run_id = RecommendationRun.objects.get().id
    assert baraka.get('/api/history/').data['runs'] == []
    assert baraka.get(f'/api/history/{run_id}/').status_code == 404
    assert amina.delete('/api/auth/me/', {'confirm': 'amina'}, format='json').status_code == 204
    assert not RecommendationRun.objects.exists() and not Recommendation.objects.exists()
