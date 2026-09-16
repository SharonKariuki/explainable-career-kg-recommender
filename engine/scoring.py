"""
Transparent additive scoring (planned for Sprint 3).

Future responsibility:
    Rank candidate occupations with

        FinalScore(o) = wc * SkillCoverage(o)
                      + wp * GraphProximity(o)
                      - wm * MissingPenalty(o)

    where wc, wp and wm come from settings.RECOMMENDER (initially 0.5, 0.2 and
    0.3) and are tuned during evaluation.

Planned behaviour:
    * Compute each term separately and return all of them alongside the final
      score. Each term is stored in its own column of the Recommendation model
      and reused, unchanged, by explanation.py and skills_gap.py.
    * Record the weights, threshold, depth limit and model name in force so a
      stored score can be recomputed from its components.

The exact definitions of the three terms are fixed in Sprint 3 and will be
documented in docs/02-architecture.md when they are implemented.

Not implemented in Sprint 1.
"""
