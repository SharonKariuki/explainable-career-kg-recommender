"""Plain-language explanations built only from a recommendation's stored score components.

Every sentence is generated from one part of the Recommendation the engine
returned: the skill contributions behind Coverage, the ProfileSimilarity
value, the skills the GraphProximity random walk arrived through, and the
weighted sum that gives the score. Nothing else is consulted, so each claim
can be traced back to the score (see fidelity.py). Alongside the text, an
Explanation records the skills it names and the component values it quotes.
"""

from dataclasses import dataclass

from recommender.engine import DEFAULT_PARAMS

SHOWN_CONTRIBUTIONS = 3


@dataclass(frozen=True)
class Explanation:
    career_id: str
    title: str
    sentences: tuple
    mentioned_skill_ids: tuple
    quoted_components: tuple  # (component name, value as printed)

    @property
    def text(self):
        return ' '.join(self.sentences)


REQUIREMENT_LEVELS = (  # (minimum edge weight, label, singular, plural)
    (0.75, 'Core requirement', 'a core requirement', 'core requirements'),
    (0.5, 'Important', 'an important skill', 'important skills'),
    (0.0, 'Supporting', 'a supporting skill', 'supporting skills'),
)


def requirement_level(edge_weight):
    return next(level for level in REQUIREMENT_LEVELS if edge_weight >= level[0])


def requirement_groups(contributions):
    """'statistics and Python as core requirements and machine learning as a supporting skill'."""
    groups = []
    for level in REQUIREMENT_LEVELS:
        members = [name(c) for c in contributions if requirement_level(c.edge_weight) is level]
        if members:
            groups.append(f'{join(members)} as {level[2] if len(members) == 1 else level[3]}')
    return groups


def fit(score):
    if score >= 0.6:
        return 'a strong'
    if score >= 0.4:
        return 'a good'
    return 'a possible'


def similarity_phrase(value):
    if value >= 0.4:
        return 'closely match'
    if value >= 0.25:
        return 'relate to'
    return 'only loosely relate to'


def proximity_phrase(value):
    if value >= 0.7:
        return 'close to'
    if value >= 0.3:
        return 'within reach of'
    return 'some distance from'


def join(items):
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1]


def name(contribution):
    """The skill as the graph knows it, with the user's own words when they differ."""
    if contribution.query.casefold() == contribution.skill_label.casefold():
        return contribution.skill_label
    return f"{contribution.skill_label} (your '{contribution.query}')"


class ExplanationGenerator:
    def __init__(self, params=DEFAULT_PARAMS):
        self.params = params

    def explain(self, recommendation):
        r = recommendation
        c = r.components
        sentences, skills, quoted = [], [], []

        def quote(component, value, percent=False):
            text = f'{value:.0%}' if percent else f'{value:.2f}'
            quoted.append((component, text))
            return text

        sentences.append(f'{r.title} is {fit(r.score)} match for your skills (score {quote("score", r.score)}).')

        # The strongest contributions, plus any uncertain match so it is never hidden.
        contributions = r.skill_contributions
        shown = [s for i, s in enumerate(contributions) if i < SHOWN_CONTRIBUTIONS or s.low_confidence]
        if shown:
            more = len(contributions) - len(shown)
            tail = f', plus {more} more of your skills' if more else ''
            sentences.append(f'Of the skills you listed, the role treats {join(requirement_groups(shown))}{tail}.')
            sentences.append(f'Together they cover {quote("coverage", c.coverage, percent=True)} of your profile.')
            skills.extend(s.skill_id for s in shown)
            for s in shown:
                if s.low_confidence:
                    sentences.append(
                        f"Your '{s.query}' was only loosely matched to {s.skill_label} "
                        f'(similarity {s.match_similarity:.2f}), so treat that part with caution.'
                    )
        else:
            sentences.append('The role does not directly require any of the skills you listed.')

        sentences.append(
            f'Taken together, your skills {similarity_phrase(c.profile_similarity)} how O*NET describes '
            f'this role (similarity {quote("profile_similarity", c.profile_similarity)}).'
        )

        if r.proximity_paths:
            yours = {s.skill_id for s in contributions}
            listed = {s.skill_id for s in shown}
            own_paths = [p for p in r.proximity_paths if p.skill_id in yours]
            own = [p.skill_label for p in own_paths]
            related = [p.skill_label for p in r.proximity_paths if p.skill_id not in yours]
            links = []
            if own and all(p.skill_id in listed for p in own_paths):
                links.append('mainly through the skills above')  # already named; don't repeat them
            elif own:
                links.append(f'mainly through your {join(own)}')
            if related:
                links.append(f'{"with further links" if own else "mainly"} through related skills such as {join(related)}')
            sentences.append(
                f'In the skills graph the role sits {proximity_phrase(c.graph_proximity)} your profile '
                f'(proximity {quote("graph_proximity", c.graph_proximity)}), connected {", ".join(links)}.'
            )
            skills.extend(p.skill_id for p in r.proximity_paths)

        p = self.params
        sentences.append(
            f'The score weights coverage {p.coverage_weight:.0%}, similarity {p.similarity_weight:.0%} '
            f'and proximity {p.proximity_weight:.0%}.'
        )

        return Explanation(
            career_id=r.career_id,
            title=r.title,
            sentences=tuple(sentences),
            mentioned_skill_ids=tuple(dict.fromkeys(skills)),
            quoted_components=tuple(quoted),
        )
