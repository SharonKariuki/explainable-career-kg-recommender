"""Map ESCO skills onto O*NET skills and tools by embedding similarity.

Each ESCO skill is paired with its most similar O*NET rated skill or tool.
Pairs at or above MERGE_THRESHOLD are the same skill under two names and will
become one node in the graph; the rest stay distinct ESCO skills. Writes
data/processed/esco_onet_map.csv with the score of every pair.

Only the preferred label (with and without ESCO's parenthetical qualifier)
is compared. Alternative labels are too loose for merging: "tools for
software configuration management" lists "git" as one, which would merge
the whole category into Git.
"""

import numpy as np
import pandas as pd

from pipeline import PROCESSED_DIR
from pipeline.embeddings import load_embeddings, skill_labels, strip_qualifier

# Chosen by inspecting every pair between 0.80 and 1.00: all pairs at or above
# 0.90 are the same skill, while 0.85-0.90 already includes false merges
# such as "Sass" -> "SAS" and "web analytics" -> "Google Analytics".
MERGE_THRESHOLD = 0.90


def main():
    labels = skill_labels()
    vectors = load_embeddings(labels['label'])

    onet = labels[labels['source'] != 'esco'].drop_duplicates(['source', 'skill_id'])
    onet_matrix = np.stack([vectors[text] for text in onet['label']])

    esco = pd.read_csv(PROCESSED_DIR / 'esco_skills.csv', dtype=str, keep_default_na=False)
    rows = []
    for uri, label in zip(esco['skill_uri'], esco['label']):
        candidates = {label, strip_qualifier(label)}
        scores = np.stack([vectors[text] for text in candidates]) @ onet_matrix.T
        best = int(scores.max(axis=0).argmax())
        similarity = float(scores[:, best].max())
        rows.append({
            'skill_uri': uri,
            'esco_label': label,
            'onet_source': onet['source'].iloc[best],
            'onet_skill_id': onet['skill_id'].iloc[best],
            'onet_label': onet['label'].iloc[best],
            'similarity': round(similarity, 4),
            'merged': similarity >= MERGE_THRESHOLD,
        })

    mapping = pd.DataFrame(rows).sort_values(['similarity', 'esco_label'], ascending=[False, True])
    mapping.to_csv(PROCESSED_DIR / 'esco_onet_map.csv', index=False)
    print(f'esco_onet_map.csv: {len(mapping)} rows, {mapping["merged"].sum()} merged at >= {MERGE_THRESHOLD}')


if __name__ == '__main__':
    main()
