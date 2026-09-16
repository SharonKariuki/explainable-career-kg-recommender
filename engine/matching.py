"""
Semantic skill matching (planned for Sprint 2 and 3).

Future responsibility:
    Map each skill string a user declares to one or more Skill nodes in the
    knowledge graph using Sentence-BERT embeddings and cosine similarity.

Planned behaviour:
    * Load the model named by settings.RECOMMENDER["SBERT_MODEL_NAME"]
      (sentence-transformers/all-mpnet-base-v2). Weights download on first use.
    * Load the precomputed Skill node embedding matrix and its id index from
      data/graph/ (produced by scripts/build_embeddings.py).
    * Encode the user's skill strings, normalise, and take cosine similarity
      against every Skill node embedding.
    * Keep matches at or above settings.RECOMMENDER["SIMILARITY_THRESHOLD"].
    * Return, for every match, the user's original wording, the Skill node id,
      its label and the similarity score. These values are carried unchanged
      into the explanation, so nothing is summarised or rounded here.

Not implemented in Sprint 1.
"""
