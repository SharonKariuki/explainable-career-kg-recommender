import pytest

from recommender.engine import get_engine
from recommender.skills_gap import DEFAULT_LIMIT, get_skills_gap


@pytest.fixture(scope='module')
def ranked():
    matches, recommendations = get_engine().rank(['Python', 'statistics', 'machine learning'], top_k=3)
    return matches, recommendations


@pytest.fixture(scope='module')
def module():
    return get_skills_gap()


def test_declared_skills_never_appear_as_gaps(module, ranked):
    matches, recommendations = ranked
    have = {m.node_id for m in matches}
    for r in recommendations:
        assert not {g.skill_id for g in module.gaps(r, matches, limit=None)} & have


def test_every_gap_is_a_requirement_of_the_career(module, ranked):
    matches, recommendations = ranked
    kg = module.kg
    for r in recommendations:
        required = kg.skills_of(r.career_id)
        for g in module.gaps(r, matches, limit=None):
            assert g.edge_weight == required[g.skill_id]
            assert set(g.sources) == kg.graph.edges[r.career_id, g.skill_id]['sources']


def test_gaps_are_ordered_by_priority_and_limited(module, ranked):
    matches, recommendations = ranked
    gaps = module.gaps(recommendations[0], matches)
    assert len(gaps) == DEFAULT_LIMIT
    assert all(g.priority == pytest.approx(g.edge_weight ** 2 * g.idf) for g in gaps)
    priorities = [g.priority for g in gaps]
    assert priorities == sorted(priorities, reverse=True)


def test_the_full_gap_is_everything_required_but_not_declared(module, ranked):
    matches, recommendations = ranked
    r = recommendations[0]
    required = set(module.kg.skills_of(r.career_id))
    have = {m.node_id for m in matches}
    assert {g.skill_id for g in module.gaps(r, matches, limit=None)} == required - have


def test_distinctive_skills_outrank_ubiquitous_ones_of_equal_weight(module, ranked):
    matches, recommendations = ranked
    gaps = module.gaps(recommendations[0], matches, limit=None)
    full_weight = [g for g in gaps if g.edge_weight == 1.0]
    most_common = min(full_weight, key=lambda g: g.idf)
    most_distinctive = max(full_weight, key=lambda g: g.idf)
    order = [g.skill_id for g in gaps]
    assert order.index(most_distinctive.skill_id) < order.index(most_common.skill_id)


def test_data_scientists_gap_names_core_data_science_tools(module, ranked):
    matches, recommendations = ranked
    assert recommendations[0].title == 'Data Scientists'
    top = {g.label for g in module.gaps(recommendations[0], matches)}
    assert {'NumPy', 'pandas', 'Scikit-learn'} <= top
