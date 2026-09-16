"""
Knowledge graph loading and traversal (planned for Sprint 2 and 3).

Future responsibility:
    Load the serialised NetworkX graph from data/graph/ into memory once per
    process, and expose read-only queries over it.

Planned behaviour:
    * Load the graph built by scripts/build_graph.py and check its schema
      version against docs/04-knowledge-graph-schema.md.
    * Breadth-first traversal from the matched Skill nodes, bounded by
      settings.RECOMMENDER["MAX_TRAVERSAL_DEPTH"], collecting candidate
      Occupation nodes together with the depth at which each was reached.
    * Record the path (node ids and edge types) that reached each candidate so
      the explanation module can cite it.
    * Accessors for an occupation's required skills with their O*NET
      importance weights, which scoring and skills-gap logic depend on.

Not implemented in Sprint 1.
"""
