import pytest

from recommender.graph import get_graph
from recommender.matching import LOW_CONFIDENCE_THRESHOLD, SkillMatcher


@pytest.fixture(scope='module')
def matcher():
    return SkillMatcher(get_graph())


def test_exact_skill_names_match_their_node(matcher):
    by_query = {m.query: m for m in matcher.match(['Python', 'SQL', 'machine learning'])}
    assert by_query['Python'].node_id == 'tool:Python'
    assert by_query['SQL'].node_label == 'Structured query language SQL'
    assert by_query['machine learning'].node_label == 'machine learning'
    assert all(m.similarity > 0.99 and not m.low_confidence for m in by_query.values())


def test_paraphrases_match_by_meaning(matcher):
    [match] = matcher.match(['talking to customers'])
    assert match.node_label == 'communicate with customers'
    assert not match.low_confidence


def test_unrelated_input_keeps_nearest_node_but_is_flagged(matcher):
    [match] = matcher.match(['playing guitar'])
    assert match.node_id in matcher.kg.graph
    assert match.similarity < LOW_CONFIDENCE_THRESHOLD
    assert match.low_confidence


def test_blank_and_repeated_skills_are_dropped(matcher):
    matches = matcher.match(['Python', ' python ', '', '   ', 'Git'])
    assert [m.query for m in matches] == ['Python', 'Git']
    assert matcher.match([]) == []


def test_every_matchable_label_belongs_to_a_graph_skill(matcher):
    assert len(matcher.texts) == len(matcher.node_ids) == len(matcher.matrix)
    assert all(matcher.kg.node(node)['kind'] == 'skill' for node in set(matcher.node_ids))
