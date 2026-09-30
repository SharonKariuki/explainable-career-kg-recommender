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

# Same skill, but O*NET names the tool with its vendor or full name, which
# keeps the similarity under the threshold. Each pair was checked by hand
# against the candidates whose O*NET tool name contains the ESCO label.
MANUAL_MERGES = {
    'Java (computer programming)': 'Oracle Java',
    'SQL': 'Structured query language SQL',
    'CSS': 'Cascading style sheets CSS',
    'Angular': 'Google Angular',
    'Android (mobile operating systems)': 'Google Android',
    'Sass': 'Syntactically awesome style sheets SASS',
    'DB2': 'IBM DB2',
    'MATLAB': 'The MathWorks MATLAB',
    'Eclipse (integrated development environment software)': 'Eclipse IDE',
    'SQL Server Integration Services': 'Microsoft SQL Server Integration Services SSIS',
    'VBScript': 'Microsoft Visual Basic Scripting Edition VBScript',
    'Nessus': 'Tenable Nessus',
    'Nexpose': 'Rapid7 Nexpose',
    'Vagrant': 'HashiCorp Vagrant',
    'Groovy': 'Apache Groovy',
    'GIMP (graphics editor software)': 'GNU Image Manipulation Program GIMP',
    'APL': 'A programming language APL',
    'COBOL': 'Common business oriented language COBOL',
    'ABAP': 'Advanced business application programming ABAP',
    'Lisp': 'List processing language LISP',
    'MDX': 'Multidimensional Expressions MDX',
}


def main():
    labels = skill_labels()
    vectors = load_embeddings(labels['label'])

    onet = labels[labels['source'] != 'esco'].drop_duplicates(['source', 'skill_id']).reset_index(drop=True)
    onet_matrix = np.stack([vectors[text] for text in onet['label']])
    tool_index = {label: i for i, label in enumerate(onet['label']) if onet['source'].iloc[i] == 'onet_tool'}

    esco = pd.read_csv(PROCESSED_DIR / 'esco_skills.csv', dtype=str, keep_default_na=False)
    unknown = set(MANUAL_MERGES) - set(esco['label']) | set(MANUAL_MERGES.values()) - set(tool_index)
    if unknown:
        raise ValueError(f'MANUAL_MERGES labels not found in the data: {sorted(unknown)}')

    rows = []
    for uri, label in zip(esco['skill_uri'], esco['label']):
        candidates = {label, strip_qualifier(label)}
        scores = np.stack([vectors[text] for text in candidates]) @ onet_matrix.T
        if label in MANUAL_MERGES:
            best, method = tool_index[MANUAL_MERGES[label]], 'manual'
        else:
            best = int(scores.max(axis=0).argmax())
            method = 'similarity' if scores[:, best].max() >= MERGE_THRESHOLD else ''
        rows.append({
            'skill_uri': uri,
            'esco_label': label,
            'onet_source': onet['source'].iloc[best],
            'onet_skill_id': onet['skill_id'].iloc[best],
            'onet_label': onet['label'].iloc[best],
            'similarity': round(float(scores[:, best].max()), 4),
            'merged': bool(method),
            'merge_method': method,
        })

    mapping = pd.DataFrame(rows).sort_values(['similarity', 'esco_label'], ascending=[False, True])
    mapping.to_csv(PROCESSED_DIR / 'esco_onet_map.csv', index=False)
    methods = mapping['merge_method'].value_counts()
    print(f'esco_onet_map.csv: {len(mapping)} rows, {methods.get("similarity", 0)} merged at >= {MERGE_THRESHOLD}, '
          f'{methods.get("manual", 0)} from MANUAL_MERGES')


if __name__ == '__main__':
    main()
