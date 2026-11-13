"""Evidence sufficiency: is there enough specific evidence to judge career fit? (Measured Matching C4, #160)

Kept apart from the ranking score and from mapping confidence. Everything here reads the
complete ranking (top_k=None) after it is computed and never writes to it, so the ranking is
unchanged (plan revision 4 §C6, revision 5 §C6.1):

    concept_weight(s)  = min((idf(s) - 1) * r_star(s), cap)
                         r_star(s) = max requirement_weight over the careers requiring s
    meaningful(s)      = confident(s) and concept_weight(s) >= w_min
                         confident: the node's reading (its best match) is not `uncertain`
    support(c)         = meaningful skills that career c requires
    c_star             = the career maximising (|support|, support weight, score)
    insufficient       = |support(c_star)| < G_min  or  weight(support(c_star)) < W_min

Constraints fixed by the plan (Q19): w_min > ln(24) * 0.5 (about 1.589), so a single-career
never-core tool is never meaningful; cap < W_min, so one concept never suffices alone;
G_min >= 2. `close_call` (several careers within epsilon of the top score) is reported only;
it never makes a profile insufficient.
"""

import math
from dataclasses import asdict, dataclass

VERSION = 'evidence-v1'
NEVER_CORE_MAX = math.log(24) * 0.5    # (idf - 1) * r* of a single-career tool at weight 0.5


@dataclass(frozen=True)
class EvidenceParams:
    w_min: float
    cap: float
    W_min: float
    G_min: int
    epsilon: float      # close_call: careers within this score distance of the top one
    u_max: float = 0.5  # reason inputs_unclear when more than this share of inputs is uncertain

    def check(self):
        problems = []
        if not self.w_min > NEVER_CORE_MAX:
            problems.append(f'w_min must exceed {NEVER_CORE_MAX:.4f}')
        if not self.cap < self.W_min:
            problems.append('cap must be below W_min')
        if not self.G_min >= 2:
            problems.append('G_min must be at least 2')
        if problems:
            raise ValueError('; '.join(problems))
        return self


# Fixture thresholds from the plan (revision 4 §C6): structure tests E1-E11 use these.
FIXTURE_PARAMS = EvidenceParams(w_min=1.6, cap=3.2, W_min=4.0, G_min=2, epsilon=0.02).check()
# Production thresholds, chosen on the students_v1 development split (see docs/evaluation_protocol.md).
DEFAULT_PARAMS = FIXTURE_PARAMS

ADVICE = {
    'skills_spread_across_areas': "Your skills point to several different areas. Pick the one you're most "
                                  "interested in and add more skills from it, or tell us your interests.",
    'skills_too_general': 'Add skills specific to the work you want, such as the tools, methods or tasks you '
                          'have used, not only skills most computing careers share.',
    'few_specific_skills': 'Add more of the specific tools, methods or tasks you have used, so that at least '
                           'two point to the same kind of work.',
    'inputs_unclear': 'Some of your skills could be read in more than one way. Write them more specifically, '
                      'for example the tool or task you mean.',
}


def raw_weights(engine):
    """(idf - 1) * r_star for every skill node, before the cap."""
    cached = getattr(engine, '_evidence_raw_weights', None)
    if cached is None:
        kg = engine.kg
        cached = {}
        for s in kg.skills():
            r_star = max(kg.requirement_weight(c, s) for c in kg.careers_requiring(s))
            cached[s] = (engine.idf[s] - 1) * r_star
        engine._evidence_raw_weights = cached
    return cached


def best_readings(matches):
    """The reading kept per node: the best-similarity match, as the engine keeps it."""
    best = {}
    for m in matches:
        if m.node_id not in best or m.similarity > best[m.node_id].similarity:
            best[m.node_id] = m
    return best


def assess(engine, matches, recommendations, params=DEFAULT_PARAMS):
    """The evidence for one profile. `recommendations` must be the complete ranking."""
    raw = raw_weights(engine)
    weight = lambda s: min(raw[s], params.cap)
    best = best_readings(matches)
    confident = {s for s, m in best.items() if not m.uncertain}
    meaningful = {s for s in confident if weight(s) >= params.w_min}

    star, star_support = None, ()
    star_key = (0, 0.0)
    for r in recommendations:                    # ranking order breaks remaining ties by score
        support = tuple(c.skill_id for c in r.skill_contributions if c.skill_id in meaningful)
        key = (len(support), sum(weight(s) for s in support))
        if key > star_key:
            star, star_support, star_key = r, support, key
    supported_concepts, supported_weight = star_key

    scores = [r.score for r in recommendations]
    close = sum(1 for s in scores if scores and scores[0] - s <= params.epsilon) if scores else 0
    uncertain_inputs = sum(1 for m in matches if m.uncertain)

    insufficient = supported_concepts < params.G_min or supported_weight < params.W_min
    reasons = []
    if insufficient:
        if not matches:
            reasons.append('few_specific_skills')
        elif len(meaningful) >= params.G_min and supported_concepts < params.G_min:
            reasons.append('skills_spread_across_areas')
        elif not meaningful:
            reasons.append('skills_too_general' if confident else 'inputs_unclear')
        else:
            reasons.append('few_specific_skills')
        if matches and uncertain_inputs / len(matches) > params.u_max and 'inputs_unclear' not in reasons:
            reasons.append('inputs_unclear')
    return {
        'insufficient': insufficient,
        'evidence': {
            'inputs': len(matches),
            'distinct_concepts': len(best),
            'confident_concepts': len(confident),
            'uncertain_inputs': uncertain_inputs,
            'meaningful_concepts': len(meaningful),
            'distinctive_weight': round(sum(weight(s) for s in confident), 4),
            'best_supported_career': None if star is None else star.career_id.split(':', 1)[1],
            'supported_concepts': supported_concepts,
            'supported_weight': round(supported_weight, 4),
            'supporting_skills': list(star_support),
            'close_alternatives': close,
            'close_call': close >= 2,
            'top_margin': round(scores[0] - scores[1], 4) if len(scores) >= 2 else None,
            'reasons': reasons,
            'advice': ADVICE[reasons[0]] if reasons else None,
            'thresholds': asdict(params),
            'version': VERSION,
        },
    }
