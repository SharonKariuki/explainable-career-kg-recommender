import hashlib

import pytest

from recommender.explanation import requirement_level
from recommender.graph import IMPORTANCE_CUTOFF, KnowledgeGraphManager, esco_node_ids, read

DATA_SCIENTISTS = 'career:15-2051.00'
SOFTWARE_DEVELOPERS = 'career:15-1252.00'
USER_SUPPORT = 'career:15-1232.00'
WEB_DEVELOPERS = 'career:15-1254.00'


@pytest.fixture(scope='module')
def kg():
    return KnowledgeGraphManager.load()


def test_node_and_edge_counts(kg):
    # Pinned to the committed dataset; update deliberately if the dataset changes.
    assert len(kg.careers()) == len(read('occupations.csv')) == 24
    assert len(kg.skills()) == 2030
    assert kg.graph.number_of_edges() == 8583


def test_no_orphan_nodes(kg):
    assert [node for node, degree in kg.graph.degree() if degree == 0] == []


def test_edges_join_a_career_to_a_skill(kg):
    for a, b in kg.graph.edges:
        assert {kg.node(a)['kind'], kg.node(b)['kind']} == {'career', 'skill'}


def test_edge_weights_are_in_range(kg):
    for *_, data in kg.graph.edges(data=True):
        assert 0 < data['weight'] <= 1
        assert data['sources'] <= {'onet_skill', 'onet_tool', 'esco'}


def test_rated_skills_below_cutoff_are_left_out(kg):
    rated = read('onet_skills.csv')
    low = rated[rated['importance'] < IMPORTANCE_CUTOFF].iloc[0]
    career, skill = f'career:{low.onet_soc_code}', f'onet:{low.element_id}'
    assert not kg.graph.has_edge(career, skill) or 'onet_skill' not in kg.graph.edges[career, skill]['sources']


def test_merged_esco_skill_shares_the_onet_node(kg):
    python_uri = read('esco_skills.csv').set_index('label').loc['Python (computer programming)', 'skill_uri']
    assert esco_node_ids()[python_uri] == 'tool:Python'
    assert 'esco' in kg.graph.edges[SOFTWARE_DEVELOPERS, 'tool:Python']['sources']


def test_traversal_from_python_reaches_expected_occupations(kg):
    reached = kg.traverse(['tool:Python'], max_depth=1)
    careers = {node for node, depth in reached.items() if depth == 1}
    assert {DATA_SCIENTISTS, SOFTWARE_DEVELOPERS} <= careers
    assert all(kg.node(node)['kind'] == 'career' for node in careers)


def test_traversal_respects_the_depth_limit(kg):
    assert kg.traverse(['tool:Python'], max_depth=0) == {'tool:Python': 0}
    reached = kg.traverse(['tool:Python'], max_depth=2)
    assert max(reached.values()) == 2
    assert all(kg.node(node)['kind'] == 'skill' for node, depth in reached.items() if depth == 2)


def test_traversal_ignores_unknown_start_nodes(kg):
    assert kg.traverse(['tool:Not A Real Tool'], max_depth=3) == {}


def career_edges(kg):
    for a, b, data in kg.graph.edges(data=True):
        yield (a, b, data) if kg.node(a)['kind'] == 'career' else (b, a, data)


def test_edge_weights_are_pinned(kg):
    # Requirement labels read each source's weight; the weights careers are scored by must not move.
    rows = sorted((career, skill, f"{data['weight']:.6f}") for career, skill, data in career_edges(kg))
    assert hashlib.sha256(repr(rows).encode()).hexdigest() == (
        '07b9c58b5097dec8654acd560c4ca0d65536328c30ab6a2a289c23049e710be0')


def test_each_source_keeps_its_own_weight(kg):
    for *_, data in kg.graph.edges(data=True):
        assert set(data['source_weights']) == data['sources']
        assert max(data['source_weights'].values()) == data['weight']


@pytest.mark.parametrize('career, skill, label', [
    (USER_SUPPORT, 'tool:Cascading style sheets CSS', 'Important'),            # Hot Technology only
    (USER_SUPPORT, 'tool:Structured query language SQL', 'Core requirement'),  # In Demand
    (WEB_DEVELOPERS, 'tool:Cascading style sheets CSS', 'Core requirement'),   # In Demand
])
def test_requirement_labels_follow_the_source_that_set_them(kg, career, skill, label):
    assert requirement_level(kg.requirement_weight(career, skill))[1] == label


def test_only_in_demand_tools_make_a_tool_alone_core(kg):
    for career, skill, data in career_edges(kg):
        weights = data['source_weights']
        core = any(w >= 0.75 for source, w in weights.items() if source != 'onet_tool')             or weights.get('onet_tool', 0) >= 1.0
        assert (requirement_level(kg.requirement_weight(career, skill))[1] == 'Core requirement') == core
