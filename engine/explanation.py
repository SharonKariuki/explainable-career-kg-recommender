"""
Explanation generation (planned for Sprint 4).

Future responsibility:
    Turn the evidence behind a ranking into a plain-language explanation.

Planned behaviour:
    * Input is only the structured evidence already produced upstream: matched
      skills with similarity scores, the graph paths that reached the
      occupation, and the individual score terms.
    * Render the text from fixed templates filled with that evidence. The text
      is never generated independently of the evidence, so every sentence can
      be traced back to a stored value.
    * Return the text together with the structured matched_skills,
      missing_skills and evidence_paths fields stored on the Explanation model.

Not implemented in Sprint 1.
"""
