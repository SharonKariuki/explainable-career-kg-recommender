import time

import pytest

from recommender.engine import DEFAULT_PARAMS, EngineParams, get_engine


@pytest.fixture(scope='module')
def engine():
    return get_engine()


@pytest.mark.parametrize('skills, expected', [
    (['Python', 'machine learning', 'statistics'], 'Data Scientists'),
    (['penetration testing', 'Kali Linux', 'network security'], 'Penetration Testers'),
    (['Java', 'software design patterns', 'unit testing'], 'Software Developers'),
])
def test_clear_profiles_rank_their_career_first(engine, skills, expected):
    _, recommendations = engine.rank(skills)
    assert recommendations[0].title == expected


def test_front_end_skills_rank_the_two_web_careers_first(engine):
    # Both web careers require all three skills; the designers' O*NET
    # description is semantically closer, so either order is reasonable.
    _, recommendations = engine.rank(['HTML', 'CSS', 'JavaScript'])
    assert {r.title for r in recommendations[:2]} == {'Web Developers', 'Web and Digital Interface Designers'}


def test_score_is_the_weighted_sum_of_stored_components(engine):
    _, recommendations = engine.rank(['Python', 'SQL', 'Linux'])
    p = DEFAULT_PARAMS
    for r in recommendations:
        c = r.components
        assert 0 <= c.coverage <= 1 and 0 <= c.profile_similarity <= 1 and 0 <= c.graph_proximity <= 1
        assert r.score == pytest.approx(
            p.coverage_weight * c.coverage + p.similarity_weight * c.profile_similarity
            + p.proximity_weight * c.graph_proximity
        )
    scores = [r.score for r in recommendations]
    assert scores == sorted(scores, reverse=True)


def test_components_record_the_skills_behind_them(engine):
    _, recommendations = engine.rank(['Python', 'machine learning', 'statistics'])
    for r in recommendations:
        assert sum(s.coverage_share for s in r.skill_contributions) == pytest.approx(r.components.coverage)
        assert {s.query for s in r.skill_contributions} <= {'Python', 'machine learning', 'statistics'}
        required = engine.kg.skills_of(r.career_id)
        assert all(p.skill_id in required for p in r.proximity_paths)
        assert 0 < sum(p.share for p in r.proximity_paths) <= 1 + 1e-9


def test_low_confidence_matches_count_at_reduced_weight(engine):
    prepared = engine.prepare(['playing guitar'])
    [match] = prepared.matches
    full = EngineParams(low_confidence_weight=1.0)
    half = EngineParams(low_confidence_weight=0.5)
    matches, with_full = engine.score(prepared, full)
    _, with_half = engine.score(prepared, half)
    assert matches[0].low_confidence and matches[0].node_id == match.node_id
    coverage = {r.career_id: r.components.coverage for r in with_full}
    for r in with_half:
        assert r.components.coverage == pytest.approx(coverage[r.career_id] / 2)


def test_traversal_depth_controls_the_candidates(engine):
    prepared = engine.prepare(['Solidity'])
    _, direct = engine.score(prepared, EngineParams(max_depth=1))
    _, wider = engine.score(prepared, EngineParams(max_depth=3))
    [match] = prepared.matches
    assert {r.career_id for r in direct} == set(engine.kg.careers_requiring(match.node_id))
    assert {r.career_id for r in direct} < {r.career_id for r in wider}
    assert all(r.components.coverage == 0 for r in wider if r.career_id not in {d.career_id for d in direct})


def test_empty_profile_returns_nothing(engine):
    assert engine.rank([]) == ((), [])


def test_three_skill_profile_ranks_quickly_once_loaded(engine):
    start = time.perf_counter()
    engine.rank(['Python', 'Docker', 'AWS'])
    assert time.perf_counter() - start < 3
