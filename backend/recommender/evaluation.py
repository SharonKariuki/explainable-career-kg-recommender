"""Synthetic evaluation profiles and ranking metrics.

A synthetic profile is a handful of skills sampled from one career's required
skills; that career is the correct answer. To read like user input rather
than a copy of the graph, each skill is written under one of its other names
when it has any (an ESCO alternative label, or the O*NET name of a merged
ESCO skill) and is sometimes lower-cased.

Validation and test sets come from different fixed seeds, so parameters are
tuned on one and reported on the other. Test seeds are locked: the
generators refuse them outside open_test_sets(). Roles, provenance and
hashes of every set: docs/evaluation_protocol.md.
"""

import dataclasses
import hashlib
import json
import math
import random
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable

from recommender.matching import graph_skill_names
from recommender.results import git_state

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
    check_seed(seed)
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


# Held-out synonyms: for every skill with another name, one of those names is
# hidden from the matcher and used as the profile's wording, so the skill can
# only be recognised by meaning. Names that differ from a remaining name only
# in case are never chosen, since the SBERT model ignores case.
HELD_OUT_SEED = 3
NOISY_SEED = 4
NOISY_MIN_EDGE_WEIGHT = 0.5
# Tuning uses its own hidden names and profiles, independent of the test set.
VALIDATION_HELD_OUT_SEED = 6
NOISY_VALIDATION_SEED = 5

# Only the final evaluation may load test sets, and only from a clean working
# tree, so every test result maps to a commit.
TEST_SEEDS = frozenset({TEST_SEED, HELD_OUT_SEED, NOISY_SEED})
_test_access = False


class LockedSetError(RuntimeError):
    pass


def check_seed(seed):
    if seed in TEST_SEEDS and not _test_access:
        raise LockedSetError(f'seed {seed} belongs to a test set; load it inside open_test_sets()')


@contextmanager
def open_test_sets():
    """Unlock the test sets for the body of a with-block; refuses a dirty working tree."""
    global _test_access
    state = git_state()
    if not state['clean']:
        raise LockedSetError('test sets need a clean working tree (commit first); uncommitted: '
                             + '; '.join(state['changes'][:5]))
    previous, _test_access = _test_access, True
    try:
        yield
    finally:
        _test_access = previous


def held_out_names(kg, seed=HELD_OUT_SEED):
    check_seed(seed)
    rng = random.Random(seed)
    names = graph_skill_names(kg).groupby('node_id')['label'].apply(list)
    held = {}
    for node, labels in sorted(names.items()):
        primary = kg.node(node)['label']
        others = [n for n in labels if n != primary]
        candidates = [n for n in others if sum(m.casefold() == n.casefold() for m in labels) == 1]
        if candidates:
            held[node] = rng.choice(sorted(candidates))
    return held


def noisy_profiles(kg, held, seed=NOISY_SEED, sizes=PROFILE_SIZES, per_size=PROFILES_PER_SIZE):
    """Profiles written only with held-out names, from each career's requirements."""
    check_seed(seed)
    rng = random.Random(seed)
    profiles = []
    for career in sorted(kg.careers()):
        pool = sorted((s, w) for s, w in kg.skills_of(career).items() if w >= NOISY_MIN_EDGE_WEIGHT and s in held)
        for size in sizes:
            for n in range(per_size):
                skill_ids = sample_without_replacement(rng, pool, size)
                profiles.append(Profile(
                    profile_id=f'noisy-{career}-{size}-{n}',
                    career_id=career,
                    size=size,
                    skills=tuple(held[s] for s in skill_ids),
                    skill_ids=tuple(skill_ids),
                ))
    return profiles


def noisy_validation(kg):
    """(hidden names, profiles) for tuning on unseen wording."""
    held = held_out_names(kg, VALIDATION_HELD_OUT_SEED)
    return held, noisy_profiles(kg, held, seed=NOISY_VALIDATION_SEED)


def noisy_test(kg):
    """(hidden names, profiles) for the final evaluation on unseen wording."""
    held = held_out_names(kg)
    return held, noisy_profiles(kg, held)


# Profiles in everyday words, each with the careers that should rank first.
# Written before any results were seen.
HAND_WRITTEN = (
    (('building websites', 'making pages look nice', 'JS'), ('Web Developers', 'Web and Digital Interface Designers')),
    (('designing app screens', 'sketching layouts', 'colour and typography'), ('Web and Digital Interface Designers',)),
    (('writing code', 'fixing bugs', 'Java'), ('Software Developers', 'Computer Programmers')),
    (('making mobile apps', 'Kotlin', 'Swift'), ('Software Developers',)),
    (('finding bugs before release', 'writing test cases', 'automating tests'),
     ('Software Quality Assurance Analysts and Testers',)),
    (('crunching numbers', 'charts and dashboards', 'Excel'), ('Business Intelligence Analysts', 'Data Scientists')),
    (('predictive models', 'python', 'statistics'), ('Data Scientists',)),
    (('surveys and sampling', 'hypothesis testing', 'R'), ('Statisticians',)),
    (('training neural networks', 'research papers', 'maths'),
     ('Computer and Information Research Scientists', 'Data Scientists')),
    (('managing databases', 'backups', 'SQL queries'), ('Database Administrators',)),
    (('designing database schemas', 'data modelling', 'SQL'), ('Database Architects', 'Database Administrators')),
    (('ETL pipelines', 'data warehouse', 'reporting'), ('Data Warehousing Specialists', 'Business Intelligence Analysts')),
    (('ethical hacking', 'finding vulnerabilities', 'Kali'), ('Penetration Testers',)),
    (('protecting company networks', 'firewalls', 'security policies'),
     ('Information Security Analysts', 'Information Security Engineers')),
    (('investigating cyber crime', 'recovering deleted files', 'evidence handling'), ('Digital Forensics Analysts',)),
    (('setting up servers', 'managing user accounts', 'Windows Server'), ('Network and Computer Systems Administrators',)),
    (('designing networks', 'routers and switches', 'cloud networking'), ('Computer Network Architects',)),
    (('helping people with computer problems', 'resetting passwords', 'good with people'),
     ('Computer User Support Specialists',)),
    (('fixing network outages', 'troubleshooting connections', 'cabling'), ('Computer Network Support Specialists',)),
    (('planning IT projects', 'managing a team', 'budgets and deadlines'), ('Information Technology Project Managers',)),
    (('smart contracts', 'crypto', 'Solidity'), ('Blockchain Engineers',)),
    (('cloud architecture', 'AWS', 'designing large systems'), ('Computer Systems Engineers/Architects',)),
    (('understanding business needs', 'writing requirements', 'process diagrams'), ('Computer Systems Analysts',)),
    (('writing scripts to automate tasks', 'Python', 'legacy code'), ('Computer Programmers', 'Software Developers')),
    (('machine learning', 'deep learning', 'computer vision'),
     ('Computer and Information Research Scientists', 'Data Scientists')),
    (('incident response', 'monitoring for attacks', 'SIEM'), ('Information Security Analysts',)),
    (('encryption', 'secure system design', 'identity management'),
     ('Information Security Engineers', 'Information Security Analysts')),
    (('user research', 'prototyping', 'Figma'), ('Web and Digital Interface Designers',)),
    (('React', 'APIs', 'databases'), ('Web Developers', 'Software Developers')),
    (('statistics', 'business reports', 'Power BI'), ('Business Intelligence Analysts',)),
)


@dataclass(frozen=True)
class LabelledProfile:
    profile_id: str
    skills: tuple
    relevant: frozenset  # career ids that count as correct


def hand_written_profiles(kg):
    by_title = {kg.node(c)['label']: c for c in kg.careers()}
    unknown = {t for _, titles in HAND_WRITTEN for t in titles} - set(by_title)
    if unknown:
        raise ValueError(f'Unknown career titles: {sorted(unknown)}')
    return [
        LabelledProfile(f'hand-{i}', skills, frozenset(by_title[t] for t in titles))
        for i, (skills, titles) in enumerate(HAND_WRITTEN)
    ]


@dataclass(frozen=True)
class ProfileSet:
    role: str       # development, validation or test
    load: Callable  # kg -> profiles, or (hidden names, profiles) for the noisy sets


PROFILE_SETS = {
    'synthetic-validation': ProfileSet('validation', validation_profiles),
    'noisy-validation': ProfileSet('validation', noisy_validation),
    'synthetic-test': ProfileSet('test', test_profiles),
    'noisy-test': ProfileSet('test', noisy_test),
    'hand-v1': ProfileSet('development', hand_written_profiles),  # tested in the v1 report, then used to diagnose
}


def canonical(value):
    if dataclasses.is_dataclass(value):
        return {f.name: canonical(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {str(k): canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (set, frozenset)):
        return sorted(canonical(v) for v in value)
    if isinstance(value, (list, tuple)):
        return [canonical(v) for v in value]
    return value


def set_hash(content):
    """sha256 of a profile set's canonical JSON (profile order kept, sets and dicts sorted)."""
    text = json.dumps(canonical(content), sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(text.encode()).hexdigest()


def describe_sets(sets, roles=None):
    """{name: role, size and hash} for a run manifest; roles come from PROFILE_SETS unless given."""
    roles = roles or {}

    def profiles(content):  # the noisy sets are (hidden names, profiles)
        is_pair = isinstance(content, tuple) and len(content) == 2 and isinstance(content[0], dict)
        return content[1] if is_pair else content
    return {
        name: {'role': roles.get(name) or PROFILE_SETS[name].role,
               'profiles': len(profiles(content)),
               'sha256': set_hash(content)}
        for name, content in sets.items()
    }


def matching_accuracy(matcher, profiles, threshold):
    """How often each profile skill is matched to the exact skill it was sampled from."""
    pairs = [(text, skill) for p in profiles for text, skill in zip(p.skills, p.skill_ids)]
    matched = {m.query: m for m in matcher.match([text for text, _ in pairs])}
    rows = [(matched[text].node_id == skill, matched[text].similarity) for text, skill in pairs]
    confident = [ok for ok, sim in rows if sim >= threshold]
    uncertain = [ok for ok, sim in rows if sim < threshold]
    return {
        'skills': len(rows),
        'correct': sum(ok for ok, _ in rows) / len(rows),
        'uncertain_share': len(uncertain) / len(rows),
        'correct_when_confident': sum(confident) / len(confident) if confident else None,
        'correct_when_uncertain': sum(uncertain) / len(uncertain) if uncertain else None,
    }


# Model selection uses validation sets only: the primary metric decides, and a
# candidate that fails any guardrail is rejected (docs/evaluation_protocol.md).
SELECTION_METRIC = 'nDCG@5'
SELECTION_GUARDRAILS = ('candidate rate', 'known-answer probes', 'validation MRR')


def precision_at_k(ranked, relevant, k):
    return len(set(ranked[:k]) & set(relevant)) / k


def recall_at_k(ranked, relevant, k):
    return len(set(ranked[:k]) & set(relevant)) / len(relevant)


def reciprocal_rank(ranked, relevant):
    for position, item in enumerate(ranked, 1):
        if item in relevant:
            return 1 / position
    return 0.0


def ndcg_at_k(ranked, grades, k):
    """nDCG with linear gains: {career: grade} labels; 0 when nothing is recommended."""
    dcg = sum(grades.get(item, 0) / math.log2(position + 1) for position, item in enumerate(ranked[:k], 1))
    ideal = sum(g / math.log2(position + 1)
                for position, g in enumerate(sorted(grades.values(), reverse=True)[:k], 1))
    return dcg / ideal if ideal else 0.0
