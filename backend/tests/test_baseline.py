import pytest

from recommender.baseline import KeywordBaseline, keyword_match
from recommender.graph import get_graph


@pytest.fixture(scope='module')
def baseline():
    return KeywordBaseline(get_graph())


def test_keyword_match_rules():
    assert keyword_match('python', 'python')
    assert keyword_match('sql', 'structured query language sql')
    assert keyword_match('microsoft excel', 'excel')
    assert keyword_match('r', 'r')
    assert not keyword_match('r', 'ruby')
    assert not keyword_match('teamwork', 'manage a team')


def test_exact_names_rank_the_career_that_requires_them(baseline):
    _, recommendations = baseline.rank(['Solidity', 'smart contract'])
    assert recommendations[0].title == 'Blockchain Engineers'
    assert recommendations[0].score == 1


def test_synonyms_are_not_understood(baseline):
    matches, recommendations = baseline.rank(['talking to customers'])
    assert matches[0].skill_ids == ()
    assert recommendations == []


def test_output_matches_the_engine_shape(baseline):
    matches, recommendations = baseline.rank(['Python', 'SQL', 'Linux'], top_k=5)
    assert [m.query for m in matches] == ['Python', 'SQL', 'Linux']
    assert len(recommendations) == 5
    assert all(0 < r.score <= 1 and r.career_id.startswith('career:') for r in recommendations)
    assert baseline.rank([]) == ((), [])
