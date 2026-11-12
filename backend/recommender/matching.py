"""Match the skills a user declares to skill nodes in the knowledge graph.

Every name a graph skill is known by (O*NET label, tool name, ESCO preferred
and alternative labels) has a cached SBERT embedding. A declared skill is
encoded with the same model and matched to the node owning the most similar
name by cosine similarity. skill_aliases.csv adds the abbreviations, product
nicknames and certifications job postings use but the sources do not name
(SIEM, K8s, CompTIA A+), each as another name of an existing skill node. Matches below LOW_CONFIDENCE_THRESHOLD are still
returned, with the nearest node, but flagged so they can be treated and
explained as uncertain.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.embeddings import encode, load_embeddings, skill_labels
from recommender.graph import esco_node_ids, onet_node_id

# From probing typical inputs: specific skills match at 0.73-1.0 ("python",
# "sql", "cloud computing"), vaguer ones at 0.53-0.65 ("teamwork", "public
# speaking"), and unrelated words mostly at 0.35-0.59 ("gardening", "asdf").
LOW_CONFIDENCE_THRESHOLD = 0.60
ALIASES_FILE = Path(__file__).with_name('skill_aliases.csv')


def skill_aliases(path=ALIASES_FILE):
    return pd.read_csv(path, comment='#', dtype=str)


@dataclass(frozen=True)
class SkillMatch:
    query: str
    node_id: str
    node_label: str
    matched_text: str
    similarity: float
    low_confidence: bool


def graph_skill_names(kg):
    """Every name each graph skill node is known by: one row per (node_id, label)."""
    labels = skill_labels()
    esco_ids = esco_node_ids()
    labels['node_id'] = [
        esco_ids[skill_id] if source == 'esco' else onet_node_id(source, skill_id)
        for source, skill_id in zip(labels['source'], labels['skill_id'])
    ]
    # Rated skills below the importance cutoff for every career are not in the graph.
    labels = labels[labels['node_id'].isin(kg.graph.nodes)]
    return labels.drop_duplicates(['node_id', 'label'])[['node_id', 'label']].reset_index(drop=True)


def matcher_names(kg):
    """The graph's names plus skill_aliases.csv. Only the matcher uses the aliases:
    evaluation profiles are written from the graph's own names, so the sets do not change."""
    labels = graph_skill_names(kg)
    owner = labels.drop_duplicates('label').set_index('label')['node_id']
    aliases = skill_aliases()
    unknown = sorted(set(aliases['target']) - set(owner.index))
    if unknown:
        raise ValueError(f'skill_aliases.csv names skills the graph does not have: {", ".join(unknown)}')
    aliases = pd.DataFrame({'node_id': aliases['target'].map(owner), 'label': aliases['alias']})
    return pd.concat([labels, aliases]).drop_duplicates(['node_id', 'label']).reset_index(drop=True)


class SkillMatcher:
    def __init__(self, kg, hidden_names=()):
        """`hidden_names` are left out of the index (ignoring case), so evaluation
        can test whether a skill is still recognised from its other names."""
        self.kg = kg
        labels = matcher_names(kg)
        hidden = {name.casefold() for name in hidden_names}
        labels = labels[~labels['label'].str.casefold().isin(hidden)]
        self.texts = labels['label'].tolist()
        self.node_ids = labels['node_id'].tolist()
        vectors = load_embeddings(self.texts)
        self.matrix = np.stack([vectors[text] for text in self.texts])

    @staticmethod
    def clean(skills):
        """Distinct non-empty skills, trimmed, in the order given (repeats ignore case)."""
        distinct = {}
        for q in (s.strip() for s in skills if s and s.strip()):
            distinct.setdefault(q.casefold(), q)
        return list(distinct.values())

    def match(self, skills):
        """One SkillMatch per distinct non-empty skill, in the order given."""
        queries = self.clean(skills)
        return self.match_encoded(queries, encode(queries)) if queries else []

    def match_encoded(self, queries, vectors):
        """Match already-cleaned queries whose embeddings the caller has computed."""
        scores = vectors @ self.matrix.T
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
