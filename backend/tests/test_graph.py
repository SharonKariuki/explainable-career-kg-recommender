import pytest

from recommender.graph import IMPORTANCE_CUTOFF, KnowledgeGraphManager, esco_node_ids, read

DATA_SCIENTISTS = 'career:15-2051.00'
SOFTWARE_DEVELOPERS = 'career:15-1252.00'


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
