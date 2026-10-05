from dataclasses import replace

import pytest

from recommender.engine import ProximityPath, Recommendation, ScoreComponents, SkillContribution, get_engine
from recommender.evaluation import validation_profiles
from recommender.explanation import ExplanationGenerator
from recommender.fidelity import check_fidelity


@pytest.fixture(scope='module')
def case():
    """A hand-built recommendation using real graph skills, and its explanation."""
    contributions = (
        SkillContribution('Python', 'tool:Python', 'Python', 1.0, False, 1.0, 1.0, 0.3),
        SkillContribution('sql', 'tool:Structured query language SQL', 'Structured query language SQL',
                          1.0, False, 1.0, 1.0, 0.2),
    )
    r = Recommendation(
        career_id='career:15-1242.00', title='Database Administrators', domain='data science', score=0.61,
        components=ScoreComponents(0.5, 0.33, 0.8), skill_contributions=contributions,
        proximity_paths=(ProximityPath('tool:Python', 'Python', 0.3),),
    )
    return r, ExplanationGenerator().explain(r)


def with_text(explanation, extra):
    return replace(explanation, sentences=explanation.sentences + (extra,))


def test_a_faithful_explanation_passes(case):
    r, x = case
    assert check_fidelity(x, r).passed


def test_naming_a_skill_outside_the_components_fails(case):
    r, x = case
    report = check_fidelity(with_text(x, 'It also builds on your Kubernetes experience.'), r)
    assert not report.passed
    assert any('Kubernetes' in v for v in report.violations)


def test_claiming_a_skill_outside_the_components_fails(case):
    r, x = case
    report = check_fidelity(replace(x, mentioned_skill_ids=x.mentioned_skill_ids + ('tool:Docker',)), r)
    assert not report.passed


def test_misquoting_a_component_fails(case):
    r, x = case
    quoted = tuple(('coverage', '90%') if c == 'coverage' else (c, v) for c, v in x.quoted_components)
    report = check_fidelity(replace(x, quoted_components=quoted), r)
    assert not report.passed
    assert any('coverage' in v for v in report.violations)


def test_quoting_words_the_user_did_not_declare_fails(case):
    r, x = case
    report = check_fidelity(with_text(x, "Your 'cloud' background helps."), r)
    assert not report.passed


def test_skill_words_inside_the_career_title_are_not_violations(case):
    r, x = case
    assert 'Database Administrators' in x.text  # "Database" is also a skill name
    assert check_fidelity(x, r).passed


def test_generated_explanations_are_faithful_on_a_batch_of_profiles():
    engine, generator = get_engine(), ExplanationGenerator()
    profiles = validation_profiles(engine.kg)[::12]
    checked = 0
    for p in profiles:
        for r in engine.rank(p.skills, top_k=5)[1]:
            report = check_fidelity(generator.explain(r), r)
            assert report.passed, (p.skills, r.title, report.violations)
            checked += 1
    assert checked >= 100
