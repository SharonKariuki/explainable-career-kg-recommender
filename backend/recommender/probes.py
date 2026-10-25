"""Known-answer regression probes from the Phase 1 investigation.

Each probe states behaviour the recommender should have and measures what it
does. All seven describe failures found in the v1 baseline, and each needs a
production change (recorded in `change_needed`) before it can pass; a probe
that passes after a change must keep passing. Validation profiles only.

Usage: `python -m recommender.validate` runs them with the validation metrics.
"""

from dataclasses import dataclass
from typing import Callable

import numpy as np

from recommender.evaluation import validation_profiles
from recommender.explanation import ExplanationGenerator

DEMO_PROFILE = ('SQL', 'python', 'public speaking', 'team management', 'excel', 'django', 'react')
UBIQUITOUS_PROFILE = ('SQL', 'python', 'excel')  # each required by 23 or 24 of the 24 careers
MAX_UNRELATED_SCORE = 0.4  # explanation.fit() calls 0.4 and above "a good match"
MAX_SIZE_BIAS = 0.3        # v1: 0.73
NEAR_TIE = 0.01


@dataclass(frozen=True)
class Probe:
    name: str
    expectation: str
    check: Callable    # engine -> (passed, what was observed)
    change_needed: str


@dataclass(frozen=True)
class ProbeResult:
    name: str
    expectation: str
    passed: bool
    observed: str
    change_needed: str


def title(engine, career):
    return engine.kg.node(career)['label']


def unrelated_hobby(engine):
    matches, recs = engine.rank(['cooking'], top_k=1)
    m, top = matches[0], (recs[0].score if recs else 0.0)
    return (m.low_confidence and top < MAX_UNRELATED_SCORE,
            f"'cooking' -> {m.node_label} {m.similarity:.3f}{' (uncertain)' if m.low_confidence else ''}; "
            f'top score {top:.3f}')


def teamwork(engine):
    matches, recs = engine.rank(['teamwork'], top_k=1)
    top = title(engine, recs[0].career_id) if recs else '-'
    return top != 'Penetration Testers', f"'teamwork' -> {matches[0].node_label} {matches[0].similarity:.3f}; first: {top}"


def generic_pair(engine):
    _, recs = engine.rank(['SQL', 'python'], top_k=3)
    first = recs[0]
    return (title(engine, first.career_id) != 'Blockchain Engineers',
            f'first: {first.title} {first.score:.3f} (coverage {first.components.coverage:.2f}, '
            f'proximity {first.components.graph_proximity:.2f}, total edge weight {engine.strength[first.career_id]:.0f})')


def size_bias(engine):
    off_target = {c: [] for c in engine.careers}
    for p in validation_profiles(engine.kg):
        for r in engine.rank(p.skills, top_k=None)[1]:
            if r.career_id != p.career_id:
                off_target[r.career_id].append(r.components.graph_proximity)
    careers = [c for c in engine.careers if off_target[c]]
    corr = float(np.corrcoef([np.median(off_target[c]) for c in careers],
                             [1 / engine.strength[c] for c in careers])[0, 1])
    return corr < MAX_SIZE_BIAS, f'corr(median off-target proximity, 1/total edge weight) = {corr:.2f} over synthetic-validation'


def public_speaking(engine):
    m = engine.matcher.match(['public speaking'])[0]
    return (m.node_label == 'Speaking' and not m.low_confidence,
            f"'public speaking' -> {m.node_label} {m.similarity:.3f}{' (uncertain)' if m.low_confidence else ''}")


def explanation_context(engine):
    matches, recs = engine.rank(DEMO_PROFILE, top_k=None)
    top = recs[0]
    text = ExplanationGenerator().explain(top).text
    used = {c.query for c in top.skill_contributions}
    unused = [m.query for m in matches if m.query not in used]
    rivals = [r.title for r in recs[1:] if top.score - r.score < NEAR_TIE]
    missing = [q for q in unused if q not in text] + ([] if not rivals or any(t in text for t in rivals) else ['near-tie'])
    return not missing, (f'{top.title} {top.score:.3f}; unused skills {unused}; within {NEAR_TIE} of it: {rivals}; '
                         f'not disclosed: {missing}')


def insufficient_signal(engine):
    _, recs = engine.rank(UBIQUITOUS_PROFILE, top_k=None)
    return (len(recs) < len(engine.careers),
            f'{len(recs)} of {len(engine.careers)} careers ranked for {list(UBIQUITOUS_PROFILE)}; '
            f'top {recs[0].title} {recs[0].score:.3f}')


PROBES = (
    Probe('unrelated-hobby', "'cooking' is uncertain and no career scores 0.4 or more", unrelated_hobby,
          'matching: tool names (Chef) need a shared word, or a margin test between the top candidates'),
    Probe('teamwork', "'teamwork' does not put Penetration Testers first", teamwork,
          'matching or data: teamwork should not resolve to the 3-career ESCO node "manage a team"'),
    Probe('generic-pair', "['SQL', 'python'] does not rank the smallest career (Blockchain Engineers) first",
          generic_pair, 'proximity: compare against a profile-free baseline instead of dividing by total edge weight'),
    Probe('size-bias', f'off-target proximity correlates with 1/total edge weight below {MAX_SIZE_BIAS}', size_bias,
          'proximity: as for generic-pair'),
    Probe('public-speaking', "'public speaking' matches Speaking with confidence", public_speaking,
          'matching data: an evidence-cited alias (O*NET Speaking) or a lexical check'),
    Probe('explanation-context', 'the top explanation names unused skills and any career within 0.01', explanation_context,
          'explanation: explain() sees one recommendation; it needs the matches and neighbouring scores'),
    Probe('insufficient-signal', 'a profile of only ubiquitous skills does not rank every career', insufficient_signal,
          'engine or API: a candidate filter or a not-enough-signal response'),
)


def run_probes(engine):
    results = []
    for probe in PROBES:
        passed, observed = probe.check(engine)
        results.append(ProbeResult(probe.name, probe.expectation, bool(passed), observed, probe.change_needed))
    return results
