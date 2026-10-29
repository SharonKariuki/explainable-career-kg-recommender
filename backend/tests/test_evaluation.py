import itertools
import math
import random

import pytest

from recommender.evaluation import (
    MIN_EDGE_WEIGHT, PROFILE_SIZES, PROFILES_PER_SIZE, hand_written_profiles, held_out_names, noisy_profiles,
    chance_hit_at_k, chance_precision_at_1, chance_reciprocal_rank, graded_disclosure, graded_metrics,
    graded_summary, hit_at_k, ndcg_at_k, noisy_validation,
    open_test_sets, precision_at_k, recall_at_k, reciprocal_rank,
    test_profiles as make_test_profiles, validation_profiles,
)
from recommender.graph import get_graph
from recommender.matching import SkillMatcher


@pytest.fixture(scope='module')
def kg():
    return get_graph()


@pytest.fixture(scope='module')
def validation(kg):
    return validation_profiles(kg)


@pytest.fixture
def unlocked(monkeypatch):
    """Test sets opened as the final evaluation opens them, with the working tree treated as clean."""
    monkeypatch.setattr('recommender.evaluation.git_state', lambda: {'commit': 'x', 'clean': True, 'changes': []})
    with open_test_sets():
        yield


def test_every_career_gets_profiles_at_every_size(kg, validation):
    assert len(validation) == len(kg.careers()) * len(PROFILE_SIZES) * PROFILES_PER_SIZE
    for p in validation:
        assert len(p.skills) == len(p.skill_ids) == p.size
        assert len(set(p.skill_ids)) == p.size


def test_profile_skills_are_core_requirements_of_their_career(kg, validation):
    for p in validation:
        required = kg.skills_of(p.career_id)
        assert all(required[s] >= MIN_EDGE_WEIGHT for s in p.skill_ids)


def test_profiles_are_reproducible_and_sets_differ(kg, validation, unlocked):
    assert validation_profiles(kg) == validation
    test = make_test_profiles(kg)
    assert {(p.career_id, p.skills) for p in validation}.isdisjoint({(p.career_id, p.skills) for p in test})


def test_some_skills_are_written_differently_from_the_node_label(kg, validation):
    rewritten = sum(s != kg.node(i)['label'] for p in validation for s, i in zip(p.skills, p.skill_ids))
    assert rewritten > 0


def test_held_out_names_are_hidden_from_the_matcher(kg, unlocked):
    held = held_out_names(kg)
    matcher = SkillMatcher(kg, hidden_names=held.values())
    indexed = {t.casefold() for t in matcher.texts}
    assert len(held) > 500
    assert not {n.casefold() for n in held.values()} & indexed
    assert all(kg.node(node)['label'] != name for node, name in held.items())


def test_noisy_profiles_use_only_held_out_names(kg, unlocked):
    held = held_out_names(kg)
    profiles = noisy_profiles(kg, held)
    assert len(profiles) == len(kg.careers()) * len(PROFILE_SIZES) * PROFILES_PER_SIZE
    assert noisy_profiles(kg, held) == profiles
    for p in profiles:
        assert p.skills == tuple(held[s] for s in p.skill_ids)
        assert all(kg.skills_of(p.career_id)[s] >= 0.5 for s in p.skill_ids)


def test_noisy_validation_is_independent_of_the_noisy_test_set(kg, unlocked):
    test_held = held_out_names(kg)
    val_held, val_profiles = noisy_validation(kg)
    test_profiles_ = noisy_profiles(kg, test_held)
    # Skills with a single alternative name are hidden in both, so overlap is
    # small but not zero: fewer than 1% of profiles may coincide.
    assert sum(test_held[n] != val_held.get(n) for n in test_held) > len(test_held) / 2
    shared = {p.skills for p in val_profiles} & {p.skills for p in test_profiles_}
    assert len(shared) < len(val_profiles) / 100


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


def test_ndcg():
    ranked = ['a', 'b', 'c', 'd']
    assert ndcg_at_k(ranked, {'a': 1}, 5) == 1
    assert ndcg_at_k(ranked, {'c': 1}, 5) == pytest.approx(0.5)  # 1 / log2(4)
    assert ndcg_at_k(ranked, {'d': 1}, 3) == 0
    assert ndcg_at_k([], {'a': 3}, 5) == 0
    # graded: the ideal order puts grade 3 first
    assert ndcg_at_k(['b', 'a'], {'a': 3, 'b': 1}, 2) == pytest.approx((1 + 3 / math.log2(3)) / (3 + 1 / math.log2(3)))


def test_hit_at_k():
    ranked = ['a', 'b', 'c', 'd']
    assert hit_at_k(ranked, {'c', 'x'}, 3) == 1
    assert hit_at_k(ranked, {'d'}, 3) == 0
    assert hit_at_k([], {'a'}, 5) == 0


@pytest.mark.parametrize('n_relevant', [1, 2, 3])
def test_chance_levels_match_every_ordering(n_relevant):
    items, relevant = range(6), set(range(n_relevant))
    orders = list(itertools.permutations(items))
    mean = lambda f: sum(f(list(o)) for o in orders) / len(orders)
    assert chance_precision_at_1(n_relevant, 6) == pytest.approx(mean(lambda o: precision_at_k(o, relevant, 1)))
    assert chance_reciprocal_rank(n_relevant, 6) == pytest.approx(mean(lambda o: reciprocal_rank(o, relevant)))
    for k in (1, 3):
        assert chance_hit_at_k(n_relevant, 6, k) == pytest.approx(mean(lambda o: hit_at_k(o, relevant, k)))


GRADES = {'own': 3, 'twin': 2, 'related': 1}
OTHERS = [f'c{i}' for i in range(21)]


def test_graded_precision_pairs_grade_two_with_strict_grade_three():
    twin_first = graded_metrics(['twin', 'own', *OTHERS], GRADES, 24)
    assert (twin_first['p@1'], twin_first['p@1_grade3']) == (1, 0)
    assert twin_first['mrr'] == 1 and twin_first['mrr_grade3'] == 0.5 and twin_first['hit@3'] == 1
    related_first = graded_metrics(['related', 'own', *OTHERS], GRADES, 24)
    assert (related_first['p@1'], related_first['p@1_grade3'], related_first['mrr']) == (0, 0, 1)
    empty = graded_metrics([], GRADES, 24)
    assert empty['candidate_rate'] == 0 and empty['p@1'] == empty['mrr'] == empty['ndcg@5'] == 0
    assert twin_first['chance_p@1'] == 2 / 24 and twin_first['chance_p@1_grade3'] == 1 / 24
    assert twin_first['chance_mrr'] == pytest.approx(chance_reciprocal_rank(3, 24))


def test_sparse_grade_two_is_disclosed_and_bounds_the_gap():
    """As in the tasks-v1 test split: one profile in 120 has a grade-2 label."""
    rows = [graded_metrics(['related', 'own', *OTHERS], {'own': 3, 'related': 1}, 24) for _ in range(119)]
    rows.append(graded_metrics(['twin', 'own', *OTHERS], GRADES, 24))
    summary = graded_summary(rows)
    assert summary['grade_2_profiles'] == 1 and summary['p@1_gap_bound'] == pytest.approx(1 / 120)
    assert summary['p@1'] - summary['p@1_grade3'] == pytest.approx(1 / 120)
    text = graded_disclosure('tasks-v1 test', summary)
    assert '120 profiles, 1 with a grade-2 label' in text and '1/120 = 0.008' in text
    assert 'No claim about near-identical tasks' in text


def test_without_grade_two_the_two_precisions_agree():
    rows = [graded_metrics(r, {'own': 3, 'related': 1}, 24) for r in (['own'], ['related', 'own'], [])]
    summary = graded_summary(rows)
    assert summary['grade_2_profiles'] == 0 and summary['p@1'] == summary['p@1_grade3']


def test_the_gap_never_exceeds_the_grade_two_share():
    rng = random.Random(0)
    careers = [f'c{i}' for i in range(24)]
    for _ in range(50):
        rows = []
        for _ in range(30):
            labelled = rng.sample(careers, 4)
            grades = {labelled[0]: 3, labelled[1]: rng.choice([2, 1]), labelled[2]: 1}
            rows.append(graded_metrics(rng.sample(careers, 24), grades, 24))
        summary = graded_summary(rows)
        assert 0 <= summary['p@1'] - summary['p@1_grade3'] <= summary['p@1_gap_bound'] + 1e-12


def test_chance_with_nothing_relevant_is_zero():
    assert chance_reciprocal_rank(0, 24) == 0
