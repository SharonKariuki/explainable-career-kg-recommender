import pytest

from recommender.engine import ProximityPath, Recommendation, ScoreComponents, SkillContribution
from recommender.explanation import ExplanationGenerator
from recommender.explanation_quality import completeness, readability, score, syllables


def contribution(label, query=None, low=False):
    return SkillContribution(query or label, f'tool:{label}', label, 0.5 if low else 1.0, low, 1.0, 1.0, 0.2)


def recommendation(contributions):
    return Recommendation(
        career_id='career:15-1254.00', title='Web Developers', domain='software engineering', score=0.6,
        components=ScoreComponents(0.4, 0.3, 0.7), skill_contributions=tuple(contributions),
        proximity_paths=(ProximityPath('tool:Node.js', 'Node.js', 0.3),),
    )


@pytest.mark.parametrize('word, expected', [
    ('skill', 1), ('graph', 1), ('profile', 2), ('similarity', 5), ('role', 1), ('table', 2), ('core', 1),
])
def test_syllable_estimate(word, expected):
    assert syllables(word) == expected


def test_readability_measures_and_jargon():
    plain = readability(['The role needs your skills.', 'You know them well.'])
    assert plain['avg_sentence_words'] == 4.5 and plain['max_sentence_words'] == 5
    assert plain['fk_grade'] < 3 and plain['jargon'] == ''
    assert readability(['The node has a high idf.'])['jargon'] == 'idf node'


def test_skill_names_are_not_counted_as_jargon():
    assert readability(['Your Node.js skills help.'], names=['Node.js'])['jargon'] == ''


def test_a_generated_explanation_is_complete():
    r = recommendation([contribution('JavaScript'), contribution('use markup languages', 'html'),
                        contribution('JamBoard', 'playing guitar', low=True)])
    result = score(ExplanationGenerator().explain(r), r)
    assert result['completeness'] == 1.0
    assert result['C3_users_own_words'] and result['C4_uncertain_matches_disclosed']
    assert result['jargon'] == ''


def test_criteria_that_do_not_apply_are_not_counted():
    r = recommendation([contribution('JavaScript')])
    criteria = completeness(ExplanationGenerator().explain(r), r)
    assert criteria['C3_users_own_words'] is None and criteria['C4_uncertain_matches_disclosed'] is None


def test_an_explanation_missing_a_component_loses_completeness():
    r = recommendation([contribution('JavaScript')])
    x = ExplanationGenerator().explain(r)
    broken = type(x)(x.career_id, x.title, x.sentences[:2], x.mentioned_skill_ids,
                     tuple(q for q in x.quoted_components if q[0] != 'profile_similarity'))
    result = score(broken, r)
    assert not result['C5_all_three_components'] and result['completeness'] < 1
