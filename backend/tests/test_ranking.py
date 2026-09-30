import pytest

from recommender.ranking import get_ranker


@pytest.fixture(scope='module')
def ranker():
    return get_ranker()


@pytest.mark.parametrize('skills, expected', [
    (['Python', 'machine learning', 'statistics'], 'Data Scientists'),
    (['HTML', 'CSS', 'JavaScript'], 'Web Developers'),
    (['penetration testing', 'Kali Linux', 'network security'], 'Penetration Testers'),
    (['Java', 'software design patterns', 'unit testing'], 'Software Developers'),
])
def test_clear_profiles_rank_their_career_first(ranker, skills, expected):
    _, recommendations = ranker.rank(skills)
    assert recommendations[0].title == expected


def test_results_are_sorted_and_limited(ranker):
    _, recommendations = ranker.rank(['Python', 'SQL', 'Linux'], top_k=5)
    assert len(recommendations) == 5
    scores = [r.score for r in recommendations]
    assert scores == sorted(scores, reverse=True)
    assert all(0 < s <= 1 for s in scores)


def test_contributions_explain_the_whole_score(ranker):
    _, recommendations = ranker.rank(['Python', 'machine learning', 'statistics'])
    for r in recommendations:
        assert r.contributions
        assert sum(c.contribution for c in r.contributions) == pytest.approx(r.score)
        assert {c.query for c in r.contributions} <= {'Python', 'machine learning', 'statistics'}


def test_only_careers_linked_to_a_matched_skill_are_returned(ranker):
    matches, recommendations = ranker.rank(['Solidity'])
    [match] = matches
    assert {r.career_id for r in recommendations} == set(ranker.kg.careers_requiring(match.node_id))


def test_empty_profile_returns_nothing(ranker):
    assert ranker.rank([]) == ([], [])
