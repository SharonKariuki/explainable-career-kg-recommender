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


def test_repeats_keep_the_first_spelling_in_its_place():
    assert SkillMatcher.clean(['Python', 'SQL', 'python', 'Git']) == ['Python', 'SQL', 'Git']
    assert SkillMatcher.clean(['a', 'B', 'A', 'b', 'c']) == ['a', 'B', 'c']


def test_every_matchable_label_belongs_to_a_graph_skill(matcher):
    assert len(matcher.texts) == len(matcher.node_ids) == len(matcher.matrix)
    assert all(matcher.kg.node(node)['kind'] == 'skill' for node in set(matcher.node_ids))


# ---- How each skill was read (Measured Matching, #158) ----

def read(matcher, query):
    [m] = matcher.match([query])
    return m


def test_runner_up_is_a_different_node_and_margin_is_the_gap(matcher):
    for m in matcher.match(['routing', 'TCP/IP', 'Python', 'Git', 'talking to customers']):
        assert m.runner_up_node_id and m.runner_up_node_id != m.node_id
        assert m.runner_up_label == matcher.kg.node(m.runner_up_node_id)['label']
        assert m.margin >= 0 and m.margin == pytest.approx(m.similarity - m.runner_up_similarity, abs=2e-4)


@pytest.mark.parametrize('query, selected', [
    ('AWK', None), ('CSS', None), ('css', None),                          # graph names owned by two nodes (any case)
    ('Linear algebra', 'onet:2.A.1.e'), ('Calculus', 'onet:2.A.1.e'),     # aliases whose target name has two owners
    ('Cypress', 'tool:Selenium'), ('Playwright', 'tool:Selenium'),
])
def test_shared_names_are_flagged_without_changing_the_selection(matcher, query, selected):
    m = read(matcher, query)
    assert 'shared_name' in m.uncertainty_reasons and m.uncertain
    assert m.shared_with and m.node_id not in m.shared_with
    assert set(m.shared_with) | {m.node_id} == set(matcher.owners[m.matched_text.casefold()])
    if selected:
        assert m.node_id == selected                      # the node chosen before #158


def test_alias_collisions_keep_every_owner(matcher):
    for alias in ('linear algebra', 'calculus', 'cypress', 'playwright'):
        assert len(matcher.owners[alias]) == 2


def test_a_confident_no_concept_input_is_reported_with_its_near_tie(matcher):
    m = read(matcher, 'TCP/IP')            # the graph has no TCP/IP concept; ipconfig wins narrowly
    assert m.node_label == 'ipconfig' and m.similarity >= LOW_CONFIDENCE_THRESHOLD and not m.low_confidence
    assert m.runner_up_label == 'netstat' and m.margin < 0.02
    assert 'close_runner_up' not in m.uncertainty_reasons          # the margin rule is off until C3 calibrates it
    calibrated = SkillMatcher(matcher.kg, margin_threshold=0.03)
    assert 'close_runner_up' in read(calibrated, 'TCP/IP').uncertainty_reasons


def test_a_clear_wrong_winner_is_not_caught_by_the_margin_rule():
    calibrated = SkillMatcher(get_graph(), margin_threshold=0.03)
    m = read(calibrated, 'routing')        # Route wins by 0.05 over ICT networking hardware: a clear winner
    assert m.node_label == 'Route' and m.margin > 0.03
    assert not m.uncertain and m.uncertainty_reasons == ()


def test_related_but_distinct_concepts_are_separate_and_confident(matcher):
    python, pandas = matcher.match(['Python', 'pandas'])
    assert python.node_id != pandas.node_id
    assert not python.uncertain and not pandas.uncertain


def test_a_weak_match_is_uncertain_below_threshold(matcher):
    m = read(matcher, 'playing guitar')
    assert m.low_confidence and m.uncertainty_reasons[0] == 'below_threshold' and m.uncertain


def test_uncertainty_never_feeds_the_ranking():
    from recommender.engine import RecommendationEngine
    kg = get_graph()
    skills = ['Git', 'Selenium', 'TCP/IP', 'routing', 'Linear algebra', 'Python']
    plain = RecommendationEngine(kg, SkillMatcher(kg)).rank(skills, top_k=None)[1]
    flagged = RecommendationEngine(kg, SkillMatcher(kg, margin_threshold=0.5)).rank(skills, top_k=None)[1]
    assert [(r.career_id, r.score, r.components) for r in plain] == [(r.career_id, r.score, r.components) for r in flagged]


# ---- Mapping candidate (release P3): unapproved, off in production ----

def test_filler_words_are_dropped_only_by_the_candidate():
    from recommender.matching import without_filler
    assert without_filler('data analysis stuff') == 'data analysis'
    assert without_filler('Networking things') == 'Networking'
    assert without_filler('stuff') == 'stuff'                       # nothing else left: keep the text


def test_the_production_matcher_does_not_use_the_candidate(matcher):
    from recommender.engine import get_engine
    from recommender.matching import skill_aliases
    assert get_engine().matcher.candidate is False and matcher.candidate is False
    production = set(skill_aliases()['alias'].str.casefold())
    assert 'oop' not in production and 'oop' in set(skill_aliases(candidate=True)['alias'].str.casefold())
    assert 'oop' not in {t.casefold() for t in get_engine().matcher.texts}
