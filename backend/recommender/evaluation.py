"""Synthetic evaluation profiles and ranking metrics.

A synthetic profile is a handful of skills sampled from one career's required
skills; that career is the correct answer. To read like user input rather
than a copy of the graph, each skill is written under one of its other names
when it has any (an ESCO alternative label, or the O*NET name of a merged
ESCO skill) and is sometimes lower-cased.

Validation and test sets come from different fixed seeds, so parameters are
tuned on one and reported on the other.
"""

import random
from dataclasses import dataclass

from recommender.matching import graph_skill_names

PROFILE_SIZES = (2, 3, 5)
PROFILES_PER_SIZE = 5
VALIDATION_SEED = 1
TEST_SEED = 2

# Skills are drawn from a career's core requirements with probability
# proportional to edge weight. At 0.75 the pool keeps Hot Technology and In
# Demand tools, highly important O*NET skills and widely shared ESCO skills
# (38-159 per career), and drops obscure tools a user is unlikely to list.
MIN_EDGE_WEIGHT = 0.75
ALTERNATIVE_NAME_RATE = 0.5
LOWERCASE_RATE = 0.5


@dataclass(frozen=True)
class Profile:
    profile_id: str
    career_id: str
    size: int
    skills: tuple
    skill_ids: tuple


def generate_profiles(kg, seed, sizes=PROFILE_SIZES, per_size=PROFILES_PER_SIZE):
    rng = random.Random(seed)
    names = graph_skill_names(kg).groupby('node_id')['label'].apply(list).to_dict()

    profiles = []
    for career in sorted(kg.careers()):
        pool = sorted((s, w) for s, w in kg.skills_of(career).items() if w >= MIN_EDGE_WEIGHT)
        for size in sizes:
            for n in range(per_size):
                skill_ids = sample_without_replacement(rng, pool, size)
                skills = tuple(write_like_a_user(rng, kg.node(s)['label'], names.get(s, [])) for s in skill_ids)
                profiles.append(Profile(
                    profile_id=f'{seed}-{career}-{size}-{n}',
                    career_id=career,
                    size=size,
                    skills=skills,
                    skill_ids=tuple(skill_ids),
                ))
    return profiles


def sample_without_replacement(rng, weighted, k):
    items = list(weighted)
    chosen = []
    for _ in range(min(k, len(items))):
        pick = rng.choices(range(len(items)), weights=[w for _, w in items])[0]
        chosen.append(items.pop(pick)[0])
    return chosen


def write_like_a_user(rng, label, names):
    alternatives = [n for n in names if n != label]
    text = rng.choice(alternatives) if alternatives and rng.random() < ALTERNATIVE_NAME_RATE else label
    return text.lower() if rng.random() < LOWERCASE_RATE else text


def validation_profiles(kg):
    return generate_profiles(kg, VALIDATION_SEED)


def test_profiles(kg):
    return generate_profiles(kg, TEST_SEED)


def precision_at_k(ranked, relevant, k):
    return len(set(ranked[:k]) & set(relevant)) / k


def recall_at_k(ranked, relevant, k):
    return len(set(ranked[:k]) & set(relevant)) / len(relevant)


def reciprocal_rank(ranked, relevant):
    for position, item in enumerate(ranked, 1):
        if item in relevant:
            return 1 / position
    return 0.0
