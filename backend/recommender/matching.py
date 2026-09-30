"""Match the skills a user declares to skill nodes in the knowledge graph.

Every name a graph skill is known by (O*NET label, tool name, ESCO preferred
and alternative labels) has a cached SBERT embedding. A declared skill is
encoded with the same model and matched to the node owning the most similar
name by cosine similarity. Matches below LOW_CONFIDENCE_THRESHOLD are still
returned, with the nearest node, but flagged so they can be treated and
explained as uncertain.
"""

from dataclasses import dataclass

import numpy as np

from pipeline.embeddings import encode, load_embeddings, skill_labels
from recommender.graph import esco_node_ids, onet_node_id

# From probing typical inputs: specific skills match at 0.73-1.0 ("python",
# "sql", "cloud computing"), vaguer ones at 0.53-0.65 ("teamwork", "public
# speaking"), and unrelated words mostly at 0.35-0.59 ("gardening", "asdf").
LOW_CONFIDENCE_THRESHOLD = 0.60


@dataclass(frozen=True)
class SkillMatch:
    query: str
    node_id: str
    node_label: str
    matched_text: str
    similarity: float
    low_confidence: bool


class SkillMatcher:
    def __init__(self, kg):
        self.kg = kg
        labels = skill_labels()
        esco_ids = esco_node_ids()
        labels['node_id'] = [
            esco_ids[skill_id] if source == 'esco' else onet_node_id(source, skill_id)
            for source, skill_id in zip(labels['source'], labels['skill_id'])
        ]
        # Rated skills below the importance cutoff for every career are not in the graph.
        labels = labels[labels['node_id'].isin(kg.graph.nodes)].drop_duplicates(['node_id', 'label'])
        self.texts = labels['label'].tolist()
        self.node_ids = labels['node_id'].tolist()
        vectors = load_embeddings(self.texts)
        self.matrix = np.stack([vectors[text] for text in self.texts])

    def match(self, skills):
        """One SkillMatch per distinct non-empty skill, in the order given."""
        cleaned = (s.strip() for s in skills if s and s.strip())
        queries = list({q.casefold(): q for q in reversed(list(cleaned))}.values())[::-1]
        if not queries:
            return []
        scores = encode(queries) @ self.matrix.T
        matches = []
        for query, row in zip(queries, scores):
            best = int(row.argmax())
            similarity = round(float(row[best]), 4)
            node_id = self.node_ids[best]
            matches.append(SkillMatch(
                query=query,
                node_id=node_id,
                node_label=self.kg.node(node_id)['label'],
                matched_text=self.texts[best],
                similarity=similarity,
                low_confidence=similarity < LOW_CONFIDENCE_THRESHOLD,
            ))
        return matches
