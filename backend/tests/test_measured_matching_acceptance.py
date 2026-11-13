"""Measured Matching acceptance checks that need the whole system (#162): AC3 and AC11."""
import pytest
from rest_framework.test import APIClient


@pytest.fixture(scope='module')
def engine():
    from recommender.engine import get_engine
    return get_engine()


def test_AC3_every_shared_name_and_alias_collision_is_flagged(engine):
    shared = sorted(name for name, owners in engine.matcher.owners.items() if len(owners) > 1)
    assert len(shared) >= 48                                # 44 shared names plus the 4 alias collisions
    for name in ('linear algebra', 'calculus', 'cypress', 'playwright'):
        assert name in shared
    for m in engine.matcher.match(shared):
        assert 'shared_name' in m.uncertainty_reasons and m.uncertain, m.query
        assert m.node_id in engine.matcher.owners[m.query.casefold()]


@pytest.mark.django_db
def test_AC11_evidence_is_identical_for_every_top_the_detail_and_repeated_requests():
    client = APIClient()
    token = client.post('/api/auth/register/', {'username': 'ac11', 'password': 'career-guide-2026'},
                        format='json').data['token']
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    client.put('/api/profile/', {'skills': ['Cisco IOS', 'OSPF', 'VLANs', 'Wireshark', 'Python']}, format='json')
    first = client.get('/api/recommendations/?top=1').data
    seen = [(first['insufficient'], first['evidence'])]
    for top in (5, 10, 24, 50, 5, 5, 5):                    # every top, then three repeated requests
        data = client.get(f'/api/recommendations/?top={top}').data
        seen.append((data['insufficient'], data['evidence']))
    detail = client.get(f"/api/recommendations/{first['recommendations'][0]['career_code']}/").data
    seen.append((detail['insufficient'], detail['evidence']))
    assert all(s == seen[0] for s in seen)
