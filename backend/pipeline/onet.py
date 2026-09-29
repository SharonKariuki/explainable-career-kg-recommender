"""Extract the in-scope tech occupations and their skills from O*NET 31.0.

Writes three files to data/processed/:

- occupations.csv: the 24 occupations in tech_occupations.csv with their domain
- onet_skills.csv: rated Essential, Transferable and Knowledge elements, with
  importance (IM, 1-5) and level (LV, 0-7) rescaled to 0-1
- onet_tools.csv: Software Skills such as Python or Docker, which O*NET does
  not rate, weighted by their In Demand and Hot Technology flags
"""

from pathlib import Path

import pandas as pd

from pipeline import PROCESSED_DIR, RAW_DIR

ONET_DIR = RAW_DIR / 'onet' / 'db_31_0_text'
SCOPE_FILE = Path(__file__).with_name('tech_occupations.csv')

RATED_FILES = {
    'essential': 'Essential Skills.txt',
    'transferable': 'Transferable Skills.txt',
    'knowledge': 'Knowledge.txt',
}

# Tool weights by flag. In Demand marks tools frequently named in current job
# postings for that occupation; Hot Technology marks tools in demand across
# many occupations.
TOOL_WEIGHTS = {'in_demand': 1.0, 'hot_technology': 0.75, 'other': 0.5}


def read_onet(filename):
    return pd.read_csv(ONET_DIR / filename, sep='\t', dtype=str)


def load_occupations(scope):
    data = read_onet('Occupation Data.txt').rename(columns={
        'O*NET-SOC Code': 'onet_soc_code', 'Description': 'description',
    })
    occupations = scope[['onet_soc_code', 'title', 'domain']].merge(
        data[['onet_soc_code', 'description']], on='onet_soc_code', how='left', validate='one_to_one',
    )
    missing = occupations[occupations['description'].isna()]['onet_soc_code'].tolist()
    if missing:
        raise ValueError(f'Scope codes not found in O*NET: {missing}')
    return occupations


def load_rated_skills(codes):
    frames = []
    for skill_type, filename in RATED_FILES.items():
        df = read_onet(filename)
        df = df[df['O*NET-SOC Code'].isin(codes) & df['Scale ID'].isin(['IM', 'LV'])]
        df = df.assign(
            value=df['Data Value'].astype(float),
            suppressed=df['Recommend Suppress'].eq('Y'),
            not_relevant=df['Not Relevant'].eq('Y'),
            skill_type=skill_type,
        )
        frames.append(df)
    ratings = pd.concat(frames)

    keys = ['O*NET-SOC Code', 'Element ID', 'Element Name', 'skill_type']
    importance = ratings[ratings['Scale ID'] == 'IM'].set_index(keys)['value']
    lv = ratings[ratings['Scale ID'] == 'LV'].set_index(keys)

    # Suppression only ever affects the level scale, so importance is always
    # kept. A suppressed level is left blank rather than trusted; a level
    # marked Not Relevant means the skill is not used, so it becomes 0.
    level = lv['value'].where(~lv['suppressed']).mask(lv['not_relevant'], 0.0)

    skills = pd.DataFrame({
        'importance': ((importance - 1) / 4).round(4),
        'level': (level / 7).round(4),
    }).reset_index()
    return skills.rename(columns={
        'O*NET-SOC Code': 'onet_soc_code', 'Element ID': 'element_id', 'Element Name': 'skill',
    }).sort_values(['onet_soc_code', 'skill_type', 'element_id'])


def load_tools(codes):
    df = read_onet('Software Skills.txt')
    df = df[df['O*NET-SOC Code'].isin(codes)]
    tools = pd.DataFrame({
        'onet_soc_code': df['O*NET-SOC Code'],
        'tool': df['Workplace Example'].str.strip(),
        'category': df['Element Name'].str.strip(),
        'in_demand': df['In Demand'].eq('Y'),
        'hot_technology': df['Hot Technology'].eq('Y'),
    }).drop_duplicates(['onet_soc_code', 'tool'])
    tools['weight'] = TOOL_WEIGHTS['other']
    tools.loc[tools['hot_technology'], 'weight'] = TOOL_WEIGHTS['hot_technology']
    tools.loc[tools['in_demand'], 'weight'] = TOOL_WEIGHTS['in_demand']
    return tools.sort_values(['onet_soc_code', 'tool'])


def main():
    scope = pd.read_csv(SCOPE_FILE, dtype=str)
    codes = set(scope['onet_soc_code'])

    outputs = {
        'occupations.csv': load_occupations(scope),
        'onet_skills.csv': load_rated_skills(codes),
        'onet_tools.csv': load_tools(codes),
    }
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for filename, df in outputs.items():
        df.to_csv(PROCESSED_DIR / filename, index=False)
        print(f'{filename}: {len(df)} rows')


if __name__ == '__main__':
    main()
