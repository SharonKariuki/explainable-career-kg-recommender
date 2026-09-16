"""
Skills gap derivation (planned for Sprint 4).

Future responsibility:
    For a recommended occupation, list the required skills the user has not
    matched, ordered by O*NET importance.

Planned behaviour:
    * Required skills come from the occupation's REQUIRES edges in the graph.
    * Matched skills come from matching.py for the same request.
    * The gap is the set difference, ordered by importance weight. It is the
      same set that feeds the MissingPenalty term in scoring.py, so the gap
      shown to the user and the penalty in the score always agree.
    * Learning resources linked to gap skills are attached here once that
      data source is added.

Not implemented in Sprint 1.
"""
