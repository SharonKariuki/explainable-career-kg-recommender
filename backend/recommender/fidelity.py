"""Fidelity check: an explanation may only state what the score actually used.

This is the fidelity dimension of the Explainability Quality Score, checked
in code. An explanation passes when:

1. every skill it claims to mention is one of the recommendation's score
   components (a skill contribution or a proximity path);
2. every component value it quotes equals the recommendation's value;
3. every user phrase it quotes ("your 'sql'") is a declared skill behind a
   contribution; and
4. its text names no skill from the knowledge graph other than those
   (a check on the words themselves, independent of what the generator
   says it mentioned).

Usage (from backend/):
    python -m recommender.fidelity          # check a batch of explanations
"""

import re
from dataclasses import dataclass
from functools import lru_cache

from recommender.graph import get_graph

QUOTED_QUERY = re.compile(r"your '([^']+)'", re.IGNORECASE)


@dataclass(frozen=True)
class FidelityReport:
    passed: bool
    violations: tuple


@lru_cache(maxsize=1)
def skill_label_pattern():
    """One regex matching any graph skill label as a whole phrase, longest first."""
    kg = get_graph()
    labels = sorted({kg.node(s)['label'] for s in kg.skills()}, key=len, reverse=True)
    return re.compile(r'(?<!\w)(' + '|'.join(re.escape(label) for label in labels) + r')(?!\w)', re.IGNORECASE)


def formatted(component, value):
    return f'{value:.0%}' if component == 'coverage' else f'{value:.2f}'


def check_fidelity(explanation, recommendation):
    violations = []
    r = recommendation

    allowed = {s.skill_id: s for s in r.skill_contributions}
    paths = {p.skill_id: p for p in r.proximity_paths}
    for skill_id in explanation.mentioned_skill_ids:
        if skill_id not in allowed and skill_id not in paths:
            violations.append(f'mentions {skill_id}, which is not a score component')

    actual = {
        'score': r.score,
        'coverage': r.components.coverage,
        'profile_similarity': r.components.profile_similarity,
        'graph_proximity': r.components.graph_proximity,
    }
    for component, printed in explanation.quoted_components:
        if component not in actual:
            violations.append(f'quotes unknown component {component}')
        elif printed != formatted(component, actual[component]):
            violations.append(f'quotes {component} as {printed}, actual {formatted(component, actual[component])}')

    queries = {s.query for s in r.skill_contributions}
    for quoted in QUOTED_QUERY.findall(explanation.text):
        if quoted not in queries:
            violations.append(f"quotes '{quoted}', which is not a declared skill behind the score")

    # Remove the phrases the explanation is entitled to use (including the
    # career's own title, which can contain skill names such as "Database"),
    # then look for any other skill name left in the text.
    permitted = [r.title]
    permitted += [allowed[s].skill_label for s in explanation.mentioned_skill_ids if s in allowed]
    permitted += [paths[s].skill_label for s in explanation.mentioned_skill_ids if s in paths]
    permitted += [s.query for s in r.skill_contributions if s.skill_id in explanation.mentioned_skill_ids]
    remaining = explanation.text
    for phrase in sorted(set(permitted), key=len, reverse=True):
        remaining = re.sub(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', ' ', remaining, flags=re.IGNORECASE)
    for stray in sorted(set(m.group(1) for m in skill_label_pattern().finditer(remaining))):
        violations.append(f'names the skill "{stray}", which is not among the components it explains')

    return FidelityReport(passed=not violations, violations=tuple(violations))


def main():
    import time

    from recommender.engine import get_engine
    from recommender.evaluation import validation_profiles
    from recommender.explanation import ExplanationGenerator

    engine, generator = get_engine(), ExplanationGenerator()
    profiles = validation_profiles(engine.kg)
    start = time.perf_counter()
    checked, failures = 0, []
    for profile in profiles:
        for r in engine.rank(profile.skills, top_k=5)[1]:
            report = check_fidelity(generator.explain(r), r)
            checked += 1
            if not report.passed:
                failures.append((profile.skills, r.title, report.violations))
    print(f'{checked} explanations from {len(profiles)} validation profiles (top 5 each): '
          f'{checked - len(failures)} passed, {len(failures)} failed ({time.perf_counter() - start:.0f}s)')
    for skills, title, violations in failures[:10]:
        print(f'  {skills} -> {title}: {"; ".join(violations)}')


if __name__ == '__main__':
    main()
