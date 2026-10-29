"""The recommender, loaded once per server process and shared by every request.

Loading the knowledge graph and the SBERT model takes about 20 seconds, so it
happens at startup (warm_up) rather than on a user's first request. After
that, ranking a profile takes well under a second.
"""

from dataclasses import asdict

from recommender.engine import DEFAULT_PARAMS, get_engine
from recommender.explanation import ExplanationGenerator, requirement_level
from recommender.skills_gap import get_skills_gap


def warm_up():
    get_engine()
    get_skills_gap()


def career_code(career_id):
    return career_id.split(':', 1)[1]


def rank(skills, top_k=None):
    """(matches, recommendations) for a list of declared skills, best first."""
    return get_engine().rank(skills, top_k=top_k)


def match_summary(match):
    return {
        'query': match.query,
        'skill': match.node_label,
        'similarity': match.similarity,
        'low_confidence': match.low_confidence,
    }


def recommendation_summary(recommendation, rank_position):
    r = recommendation
    explanation = ExplanationGenerator().explain(r)
    return {
        'rank': rank_position,
        'career_code': career_code(r.career_id),
        'title': r.title,
        'domain': r.domain,
        'score': r.score,
        'components': asdict(r.components),
        'summary': explanation.sentences[0],
    }


def with_requirement(item):
    """Add the plain label ('Core requirement', 'Important', 'Supporting') for its edge weight."""
    return {**item, 'requirement': requirement_level(item['edge_weight'])[1]}


def recommendation_detail(recommendation, rank_position, matches):
    r = recommendation
    explanation = ExplanationGenerator().explain(r)
    p = DEFAULT_PARAMS
    return {
        **recommendation_summary(r, rank_position),
        'weights': {
            'coverage': p.coverage_weight,
            'profile_similarity': p.similarity_weight,
            'graph_proximity': p.proximity_weight,
        },
        'explanation': list(explanation.sentences),
        'skill_contributions': [with_requirement(asdict(c)) for c in r.skill_contributions],
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


def requirement_item(skill, weight, have):
    node = kg().node(skill)
    return {
        'skill_id': skill,
        'label': node['label'],
        'skill_type': node['skill_type'],
        'edge_weight': weight,
        'requirement': requirement_level(weight)[1],
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
        'requirements': [requirement_item(s, required[s], have) for s in skills[:SHOWN_REQUIREMENTS]],
        'tools': [requirement_item(s, required[s], have) for s in tools[:SHOWN_TOOLS]],
        # Every required skill the user has, which the top lists above may leave out.
        'your_skills': [requirement_item(s, required[s], have) for s in ordered if s in have],
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
