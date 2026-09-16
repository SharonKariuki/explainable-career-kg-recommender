"""
Research core of the career recommender.

This package runs inside the Django process. It loads the NetworkX knowledge
graph and the cached skill embeddings once, then serves recommendation
requests from memory. In Sprint 1 every module is an empty placeholder whose
docstring records its planned responsibility; no logic is implemented.

Pipeline (planned):
    matching.py     user skill text  -> matched graph Skill nodes (SBERT)
    graph.py        matched Skill nodes -> candidate Occupations (BFS)
    scoring.py      candidates -> ranked list with separate score terms
    explanation.py  score terms + paths -> plain-language explanation
    skills_gap.py   required minus matched skills -> ordered gap list
"""
