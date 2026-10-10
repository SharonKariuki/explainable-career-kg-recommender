import pytest

from recommender.evaluate import GRAPH_ONLY, SYSTEMS, Systems, bootstrap_interval, metrics
from recommender.graph import get_graph


@pytest.fixture(scope='module')
def systems():
    return Systems(get_graph())


@pytest.mark.parametrize('system', SYSTEMS)
def test_every_system_ranks_careers(systems, system):
    ranked = systems.rank(system, ['Python', 'machine learning', 'statistics'])
    assert ranked and set(ranked) <= set(systems.careers)
    assert len(ranked) == len(set(ranked))


def test_sbert_only_ranks_every_career(systems):
    assert sorted(systems.rank('sbert_only', ['building websites'])) == systems.careers


def test_graph_only_needs_exact_names(systems):
    assert systems.rank('graph_only', ['Solidity'])[0] == 'career:15-1299.07'
    assert systems.rank('graph_only', ['writing smart contracts for crypto']) == []


def test_graph_only_drops_profile_similarity():
    assert GRAPH_ONLY.similarity_weight == 0
    assert GRAPH_ONLY.coverage_weight + GRAPH_ONLY.proximity_weight == pytest.approx(1)


def test_metrics_and_interval():
    assert metrics(['a', 'b', 'c'], {'b'}) == {'p@1': 0, 'p@3': pytest.approx(1 / 3), 'r@3': 1, 'r@5': 1, 'mrr': 0.5}
    low, high = bootstrap_interval([0.2] * 50)
    assert low == high == pytest.approx(0.2)
