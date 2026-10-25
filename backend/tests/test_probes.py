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
    'teamwork': "v1: 'teamwork' -> manage a team 0.651; Penetration Testers first",
    'generic-pair': 'v1: Blockchain Engineers first (total edge weight 71, the smallest)',
    'size-bias': 'v1: correlation 0.73',
    'public-speaking': "v1: 'public speaking' -> Speaking 0.564, uncertain",
    'explanation-context': 'v1: team management and the near-tie with Software Developers go unmentioned',
    'insufficient-signal': 'v1: all 24 careers ranked',
}


@pytest.fixture(scope='module')
def results():
    return {r.name: r for r in run_probes(get_engine())}


def test_every_probe_records_what_it_saw_and_the_change_it_needs(results):
    assert [p.name for p in PROBES] == list(results) == list(BASELINE_FAILURES)
    assert all(r.observed and r.change_needed for r in results.values())


@pytest.mark.parametrize('name', [
    pytest.param(name, marks=pytest.mark.xfail(strict=True, raises=AssertionError, reason=reason))
    for name, reason in BASELINE_FAILURES.items()
])
def test_probe(results, name):
    assert results[name].passed, results[name].observed
