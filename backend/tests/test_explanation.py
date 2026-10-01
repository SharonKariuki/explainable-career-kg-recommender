from recommender.engine import ProximityPath, Recommendation, ScoreComponents, SkillContribution
from recommender.explanation import ExplanationGenerator


def contribution(label, query=None, weight=1.0, similarity=1.0, low=False, share=0.2):
    return SkillContribution(
        query=query or label, skill_id=f'tool:{label}', skill_label=label, match_similarity=similarity,
        low_confidence=low, edge_weight=weight, idf=1.0, coverage_share=share,
    )


def recommendation(contributions=(), paths=(), coverage=0.5, similarity=0.42, proximity=0.9, score=0.65):
    return Recommendation(
        career_id='career:15-2051.00', title='Data Scientists', domain='data science', score=score,
        components=ScoreComponents(coverage, similarity, proximity),
        skill_contributions=tuple(contributions), proximity_paths=tuple(paths),
    )


def explain(r):
    return ExplanationGenerator().explain(r)


def test_requirements_are_grouped_by_level_with_the_users_own_words():
    r = recommendation([
        contribution('statistics', weight=0.8),
        contribution('Structured query language SQL', query='sql', weight=1.0),
        contribution('machine learning', weight=0.2),
    ])
    text = explain(r).text
    assert "statistics and Structured query language SQL (your 'sql') as core requirements" in text
    assert 'machine learning as a supporting skill' in text


def test_only_the_top_three_are_listed_but_the_rest_are_counted():
    r = recommendation([contribution(f'Skill{i}', share=0.1) for i in range(5)])
    x = explain(r)
    assert 'Skill3' not in x.text and 'plus 2 more of your skills' in x.text
    assert x.mentioned_skill_ids == ('tool:Skill0', 'tool:Skill1', 'tool:Skill2')


def test_low_confidence_matches_are_always_disclosed():
    r = recommendation([contribution(f'Skill{i}') for i in range(3)]
                       + [contribution('JamBoard', query='playing guitar', similarity=0.4, low=True)])
    x = explain(r)
    assert "Your 'playing guitar' was only loosely matched to JamBoard (similarity 0.40)" in x.text
    assert 'tool:JamBoard' in x.mentioned_skill_ids


def test_proximity_separates_the_users_skills_from_related_ones():
    mine = contribution('statistics')
    paths = [ProximityPath('tool:statistics', 'statistics', 0.4), ProximityPath('tool:SAS', 'SAS', 0.1)]
    text = explain(recommendation([mine], paths)).text
    assert 'connected mainly through your statistics, with further links through related skills such as SAS' in text


def test_careers_without_direct_skills_say_so():
    x = explain(recommendation(coverage=0.0))
    assert 'does not directly require any of the skills you listed' in x.text
    assert x.mentioned_skill_ids == ()


def test_quoted_components_appear_in_the_text():
    x = explain(recommendation([contribution('Python')], [ProximityPath('tool:Python', 'Python', 0.5)]))
    assert dict(x.quoted_components) == {
        'score': '0.65', 'coverage': '50%', 'profile_similarity': '0.42', 'graph_proximity': '0.90',
    }
    for _, value in x.quoted_components:
        assert value in x.text
