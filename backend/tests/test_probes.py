"""Regression probes (recommender/probes.py) against the current engine.

Every probe fails on the v1 baseline and needs a production change, so each
is an expected failure in strict mode: when a change makes one pass, its
test reports XPASS and fails until the mark is removed, after which the
probe guards the fix.
"""

import pytest

from recommender.engine import get_engine
from recommender.probes import PROBES, run_probes

BASELINE_FAILURES = {
    'unrelated-hobby': "v1: 'cooking' -> Chef (a configuration tool) at 0.711; Information Security Engineers 0.582",
    'generic-pair': 'v1: Blockchain Engineers first (total edge weight 71, the smallest)',
    'size-bias': 'v1: correlation 0.73',
    'explanation-context': 'v1: team management and the near-tie with Software Developers go unmentioned',
    'insufficient-signal': 'v1: all 24 careers ranked',
}
# Fixed by the skill aliases (recommender/skill_aliases.csv); they must keep passing.
FIXED = ('teamwork', 'public-speaking')


@pytest.fixture(scope='module')
def results():
    return {r.name: r for r in run_probes(get_engine())}


def test_every_probe_records_what_it_saw_and_the_change_it_needs(results):
    assert [p.name for p in PROBES] == list(results)
    assert set(results) == set(BASELINE_FAILURES) | set(FIXED)
    assert all(r.observed and r.change_needed for r in results.values())


@pytest.mark.parametrize('name', [
    pytest.param(name, marks=pytest.mark.xfail(strict=True, raises=AssertionError, reason=reason))
    for name, reason in BASELINE_FAILURES.items()
])
def test_probe(results, name):
    assert results[name].passed, results[name].observed


@pytest.mark.parametrize('name', FIXED)
def test_fixed_probe(results, name):
    assert results[name].passed, results[name].observed
