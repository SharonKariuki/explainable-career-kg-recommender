"""Print one occupation from the processed dataset with its weighted skills.

Usage (from backend/):
    python -m pipeline.summary                         # Software Developers
    python -m pipeline.summary "Data Scientists"
    python -m pipeline.summary 15-1212.00 --top 20
"""

import argparse
import sys

import pandas as pd

from pipeline import PROCESSED_DIR


def load_dataset():
    def read(name):
        return pd.read_csv(PROCESSED_DIR / name, dtype={'onet_soc_code': str}, keep_default_na=False, na_values=[''])

    return {
        'occupations': read('occupations.csv'),
        'onet_skills': read('onet_skills.csv'),
        'onet_tools': read('onet_tools.csv'),
        'esco_skills': read('esco_occupation_skills.csv').merge(read('esco_skills.csv'), on='skill_uri'),
        'esco_map': read('esco_onet_map.csv'),
    }


def find_occupation(occupations, query):
    q = query.strip().lower()
    match = occupations[(occupations['onet_soc_code'] == q) | (occupations['title'].str.lower() == q)]
    if match.empty:
        match = occupations[occupations['title'].str.lower().str.contains(q, regex=False)]
    if len(match) != 1:
        options = '\n  '.join(f'{c}  {t}' for c, t in zip(occupations['onet_soc_code'], occupations['title']))
        sys.exit(f'No single occupation matches "{query}". Choose one of:\n  {options}')
    return match.iloc[0]


def section(title, rows):
    print(f'\n{title}')
    print(rows.to_string(index=False, na_rep='-') if not rows.empty else '  (none)')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('occupation', nargs='?', default='Software Developers', help='title or O*NET-SOC code')
    parser.add_argument('--top', type=int, default=10, help='rows per section')
    args = parser.parse_args()

    data = load_dataset()
    occupation = find_occupation(data['occupations'], args.occupation)
    code = occupation['onet_soc_code']
    print(f"{occupation['title']} ({code}), {occupation['domain']}")

    rated = data['onet_skills'][data['onet_skills']['onet_soc_code'] == code]
    rated = rated.sort_values('importance', ascending=False).head(args.top)
    section('O*NET skills and knowledge (importance, level on 0-1)', rated[['skill', 'skill_type', 'importance', 'level']])

    tools = data['onet_tools'][data['onet_tools']['onet_soc_code'] == code]
    tools = tools.sort_values(['weight', 'tool'], ascending=[False, True]).head(args.top)
    section('O*NET tools (weight: 1.0 In Demand, 0.75 Hot Technology, 0.5 other)', tools[['tool', 'weight']])

    esco = data['esco_skills'][data['esco_skills']['onet_soc_code'] == code]
    esco = esco.merge(data['esco_map'][['skill_uri', 'onet_label', 'merged']], on='skill_uri')
    esco['same_as_onet'] = esco['onet_label'].where(esco['merged'], '')
    esco = esco.sort_values(['weight', 'label'], ascending=[False, True]).head(args.top)
    section(
        'ESCO skills (weight: mean of essential 1.0 / optional 0.5 over linked ESCO occupations)',
        esco[['label', 'weight', 'essential_in', 'optional_in', 'esco_occupations', 'same_as_onet']],
    )


if __name__ == '__main__':
    main()
