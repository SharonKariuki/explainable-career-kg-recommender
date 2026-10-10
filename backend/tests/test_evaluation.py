import pytest

from recommender.evaluation import (
    MIN_EDGE_WEIGHT, PROFILE_SIZES, PROFILES_PER_SIZE, hand_written_profiles, held_out_names, noisy_profiles,
    precision_at_k, recall_at_k, reciprocal_rank, test_profiles as make_test_profiles, validation_profiles,
)
from recommender.graph import get_graph
from recommender.matching import SkillMatcher


@pytest.fixture(scope='module')
def kg():
    return get_graph()


@pytest.fixture(scope='module')
def validation(kg):
    return validation_profiles(kg)


def test_every_career_gets_profiles_at_every_size(kg, validation):
    assert len(validation) == len(kg.careers()) * len(PROFILE_SIZES) * PROFILES_PER_SIZE
    for p in validation:
        assert len(p.skills) == len(p.skill_ids) == p.size
        assert len(set(p.skill_ids)) == p.size


def test_profile_skills_are_core_requirements_of_their_career(kg, validation):
    for p in validation:
        required = kg.skills_of(p.career_id)
        assert all(required[s] >= MIN_EDGE_WEIGHT for s in p.skill_ids)


def test_profiles_are_reproducible_and_sets_differ(kg, validation):
    assert validation_profiles(kg) == validation
    test = make_test_profiles(kg)
    assert {(p.career_id, p.skills) for p in validation}.isdisjoint({(p.career_id, p.skills) for p in test})


def test_some_skills_are_written_differently_from_the_node_label(kg, validation):
    rewritten = sum(s != kg.node(i)['label'] for p in validation for s, i in zip(p.skills, p.skill_ids))
    assert rewritten > 0


def test_held_out_names_are_hidden_from_the_matcher(kg):
    held = held_out_names(kg)
    matcher = SkillMatcher(kg, hidden_names=held.values())
    indexed = {t.casefold() for t in matcher.texts}
    assert len(held) > 500
    assert not {n.casefold() for n in held.values()} & indexed
    assert all(kg.node(node)['label'] != name for node, name in held.items())


def test_noisy_profiles_use_only_held_out_names(kg):
    held = held_out_names(kg)
    profiles = noisy_profiles(kg, held)
    assert len(profiles) == len(kg.careers()) * len(PROFILE_SIZES) * PROFILES_PER_SIZE
    assert noisy_profiles(kg, held) == profiles
    for p in profiles:
        assert p.skills == tuple(held[s] for s in p.skill_ids)
        assert all(kg.skills_of(p.career_id)[s] >= 0.5 for s in p.skill_ids)


def test_hand_written_profiles_name_real_careers(kg):
    profiles = hand_written_profiles(kg)
    assert len(profiles) == 30
    assert all(p.relevant and p.relevant <= set(kg.careers()) for p in profiles)


def test_metrics():
    ranked = ['a', 'b', 'c', 'd']
    assert precision_at_k(ranked, {'b'}, 2) == 0.5
    assert precision_at_k(ranked, {'e'}, 3) == 0
    assert recall_at_k(ranked, {'b', 'e'}, 2) == 0.5
    assert recall_at_k(ranked, {'c'}, 3) == 1
    assert reciprocal_rank(ranked, {'c'}) == pytest.approx(1 / 3)
    assert reciprocal_rank(ranked, {'e'}) == 0
