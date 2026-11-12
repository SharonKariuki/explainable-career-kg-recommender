"""The skill aliases: valid targets, matched by the engine, invisible to the evaluation sets."""

import pandas as pd
import pytest

from recommender import matching
from recommender.engine import get_engine
from recommender.graph import get_graph
from recommender.matching import graph_skill_names, matcher_names, skill_aliases


def test_every_alias_names_a_skill_the_graph_has():
    names = set(graph_skill_names(get_graph())['label'])
    aliases = skill_aliases()
    assert not aliases['alias'].str.casefold().duplicated().any()
    assert set(aliases['target']) <= names


def test_an_unknown_target_is_refused(monkeypatch):
    monkeypatch.setattr(matching, 'skill_aliases', lambda path=None: pd.DataFrame({'alias': ['X'], 'target': ['no such skill']}))
    with pytest.raises(ValueError, match='no such skill'):
        matcher_names(get_graph())


def test_aliases_reach_the_matcher_but_not_the_names_evaluation_sets_are_written_from():
    kg = get_graph()
    assert 'SIEM' in set(matcher_names(kg)['label'])
    assert 'SIEM' not in set(graph_skill_names(kg)['label'])


@pytest.mark.parametrize('declared, expected', [
    ('SIEM', 'IBM QRadar SIEM'),
    ('CompTIA A+', 'repair ICT devices'),
    ('K8s', 'Kubernetes'),
    ('Neon', 'PostgreSQL'),
    ('Problem solving', 'Complex Problem Solving'),
])
def test_job_posting_terms_match_their_skill_with_confidence(declared, expected):
    [match] = get_engine().matcher.match([declared])
    assert match.node_label == expected and not match.low_confidence
