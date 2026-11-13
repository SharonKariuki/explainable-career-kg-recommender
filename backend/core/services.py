"""The recommender, loaded once per server process and shared by every request.

Loading the knowledge graph and the SBERT model takes about 20 seconds, so it
happens at startup (warm_up) rather than on a user's first request. After
that, ranking a profile takes well under a second.
"""

from dataclasses import asdict

from recommender import evidence, presentation
from recommender.engine import DEFAULT_PARAMS, get_engine
from recommender.explanation import ExplanationGenerator, fit_level, requirement_level, requirement_of
from recommender.skills_gap import get_skills_gap


def warm_up():
    get_engine()
    get_skills_gap()


def career_code(career_id):
    return career_id.split(':', 1)[1]


def rank(skills, top_k=None, background=''):
    """(matches, recommendations) for a list of declared skills and optional background text, best first."""
    return get_engine().rank(skills, top_k=top_k, background=background)


def rank_with_evidence(skills, top_k=None, background=''):
    """(matches, recommendations, assessment). The evidence is computed on the complete
    ranking before it is cut to top_k, so it is the same for every top_k (#160)."""
    engine = get_engine()
    matches, ranked = engine.rank(skills, top_k=None, background=background)
    assessment = evidence.assess(engine, matches, ranked)
    return matches, (ranked[:top_k] if top_k else ranked), assessment


def match_summary(match):
    """How one declared skill was read. The first four keys are the original contract; the rest
    (Measured Matching, #158) are additive diagnostics and do not affect the ranking."""
    m = match
    runner_up = None if m.runner_up_node_id is None else {
        'skill_id': m.runner_up_node_id, 'skill': m.runner_up_label,
        'matched_text': m.runner_up_text, 'similarity': m.runner_up_similarity,
    }
    return {
        'query': m.query,
        'skill': m.node_label,
        'similarity': m.similarity,
        'low_confidence': m.low_confidence,
        'skill_id': m.node_id,
        'matched_text': m.matched_text,
        'runner_up': runner_up,
        'margin': m.margin,
        'shared_with': list(m.shared_with),
        'uncertain': m.uncertain,
        'uncertainty_reasons': list(m.uncertainty_reasons),
    }


def explain(recommendation, rank_position, matches=(), assessment=None, ranked=()):
    """The explanation the API shows: with the readings, evidence and near-tie disclosures (#161)."""
    from django.conf import settings

    from recommender.explanation_quality import near_tie_with_top
    near_tie = bool(assessment and ranked and near_tie_with_top(assessment, ranked, recommendation))
    # The insufficient-evidence wording is shown only when enabled (see settings.EXPLAIN_INSUFFICIENT_EVIDENCE).
    shown = assessment if settings.EXPLAIN_INSUFFICIENT_EVIDENCE else None
    fit = presentation.shown_fit(get_engine().kg, matches, recommendation) if matches else None
    return ExplanationGenerator().explain(recommendation, matches, shown, rank_position, near_tie, display=fit)


def recommendation_summary(recommendation, rank_position, matches=(), assessment=None, ranked=()):
    r = recommendation
    explanation = explain(r, rank_position, matches, assessment, ranked)
    return {
        'rank': rank_position,
        'career_code': career_code(r.career_id),
        'title': r.title,
        'domain': r.domain,
        'score': r.score,
        'components': asdict(r.components),
        'summary': explanation.sentences[0],
        'fit': fit_level(r.score),
        # The label to show: strong or good only when enough specific skills support it (release safety rule).
        **dict(zip(('fit_shown', 'evidence_support'),
                   presentation.shown_fit(get_engine().kg, matches, r) if matches else (fit_level(r.score), 0))),
        'reason': explanation.reason,
        'matched_skills': [matched_skill(c) for c in r.skill_contributions],
    }


def matched_skill(contribution):
    """One of the user's skills the career requires, as the match card shows it."""
    c = contribution
    return {
        'skill_id': c.skill_id,
        'label': c.skill_label,
        'query': c.query,
        'requirement': requirement_of(c)[1],
        'low_confidence': c.low_confidence,
    }


def with_requirement(item):
    """Add the plain label ('Core requirement', 'Important', 'Supporting') for its requirement weight."""
    weight = item.get('requirement_weight')
    return {**item, 'requirement': requirement_level(item['edge_weight'] if weight is None else weight)[1]}


def contribution_detail(contribution, matches):
    """A skill contribution as the detail endpoint shows it, with how its skill was read (#160)."""
    reading = next((m for m in matches if m.query == contribution.query and m.node_id == contribution.skill_id), None)
    return {
        **with_requirement(asdict(contribution)),
        'uncertain': bool(reading and reading.uncertain),
        'uncertainty_reasons': list(reading.uncertainty_reasons) if reading else [],
        'runner_up_skill': reading.runner_up_label if reading else None,
    }


def recommendation_detail(recommendation, rank_position, matches, assessment=None, ranked=()):
    r = recommendation
    explanation = explain(r, rank_position, matches, assessment, ranked)
    p = DEFAULT_PARAMS
    return {
        **recommendation_summary(r, rank_position, matches, assessment, ranked),
        'weights': {
            'coverage': p.coverage_weight,
            'profile_similarity': p.similarity_weight,
            'graph_proximity': p.proximity_weight,
            # Share of the whole score, used only when the profile has background text.
            'background': p.background_weight if r.components.background_similarity is not None else None,
        },
        'explanation': list(explanation.sentences),
        'skill_contributions': [contribution_detail(c, matches) for c in r.skill_contributions],
        'proximity_paths': [asdict(p) for p in r.proximity_paths],
        'skills_gap': [with_requirement(asdict(g)) for g in get_skills_gap().gaps(r, matches)],
    }


# ---- Career catalogue: every career in the graph, whatever the user's skills ----

SHOWN_REQUIREMENTS = 12
SHOWN_TOOLS = 12


def kg():
    return get_engine().kg


def career_node_id(code):
    """The graph node for an O*NET-SOC code, or None when there is no such career."""
    node = f'career:{code}'
    return node if node in kg().graph and kg().node(node)['kind'] == 'career' else None


def requirement_item(career, skill, weight, have):
    node = kg().node(skill)
    return {
        'skill_id': skill,
        'label': node['label'],
        'skill_type': node['skill_type'],
        'edge_weight': weight,
        'requirement': requirement_level(kg().requirement_weight(career, skill))[1],
        'have': skill in have,
    }


def career_summary(career):
    node = kg().node(career)
    required = kg().skills_of(career)
    return {
        'career_code': career_code(career),
        'title': node['label'],
        'domain': node['domain'],
        'description': node['description'],
        'skill_count': sum(1 for s in required if kg().node(s)['skill_type'] != 'tool'),
        'tool_count': sum(1 for s in required if kg().node(s)['skill_type'] == 'tool'),
    }


def catalogue():
    """Every career, by title."""
    return sorted((career_summary(c) for c in kg().careers()), key=lambda c: c['title'])


def career_profile(career, matches=()):
    """What a career requires, most important first, marking skills the user's matches cover.

    Skills are ordered as the skills gap orders them (edge weight squared times
    IDF), so core requirements distinctive to this career lead.
    """
    idf = get_engine().idf
    have = {m.node_id for m in matches}
    required = kg().skills_of(career)
    ordered = sorted(required, key=lambda s: (-required[s] ** 2 * idf[s], kg().node(s)['label']))
    skills = [s for s in ordered if kg().node(s)['skill_type'] != 'tool']
    tools = [s for s in ordered if kg().node(s)['skill_type'] == 'tool']
    return {
        **career_summary(career),
        'requirements': [requirement_item(career, s, required[s], have) for s in skills[:SHOWN_REQUIREMENTS]],
        'tools': [requirement_item(career, s, required[s], have) for s in tools[:SHOWN_TOOLS]],
        # Every required skill the user has, which the top lists above may leave out.
        'your_skills': [requirement_item(career, s, required[s], have) for s in ordered if s in have],
    }


def skill_label(skill_id):
    """The label of a graph skill node, or None when there is no such skill."""
    graph = kg().graph
    if skill_id not in graph or graph.nodes[skill_id]['kind'] != 'skill':
        return None
    return graph.nodes[skill_id]['label']


SKILL_SUGGESTIONS = 8


def search_skills(query, limit=SKILL_SUGGESTIONS):
    """Skill names containing the query, names that start with it first, then the
    ones more careers require, so common skills come before obscure tools."""
    q = query.strip().casefold()
    if not q:
        return []
    graph = kg().graph
    found = {}
    for node, data in graph.nodes(data=True):
        if data['kind'] != 'skill':
            continue
        label = data['label']
        position = label.casefold().find(q)
        if position < 0:
            continue
        key = label.casefold()
        careers = graph.degree(node)
        if key not in found or careers > found[key][1]:
            found[key] = (label, careers, position != 0)
    ranked = sorted(found.values(), key=lambda f: (f[2], -f[1], len(f[0]), f[0]))
    return [{'label': label, 'careers': careers} for label, careers, _ in ranked[:limit]]
