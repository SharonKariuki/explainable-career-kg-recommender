"""Extract ESCO skills for the in-scope O*NET occupations.

Links each O*NET occupation to ESCO occupations through the official
ESCO-O*NET crosswalk, then collects their essential and optional skills.
Writes three files to data/processed/:

- esco_occupations.csv: the crosswalk links used, with their match type
- esco_occupation_skills.csv: one weighted row per O*NET occupation and skill
- esco_skills.csv: label, type and alternative labels of every linked skill
"""

import pandas as pd

from pipeline import PROCESSED_DIR, RAW_DIR

ESCO_DIR = RAW_DIR / 'esco' / 'ESCO_v1.1.0'
CROSSWALK_FILE = RAW_DIR / 'esco' / 'ONET_Occupations_0_updated.csv'
CROSSWALK_HEADER_ROWS = 16

# In the crosswalk, broadMatch means the O*NET occupation is broader than the
# ESCO one (e.g. Software Developers -> gambling games developer), so its skills
# may not apply. Those links are only used when an occupation has no other.
PREFERRED_MATCHES = {'exactMatch', 'closeMatch', 'narrowMatch'}
FALLBACK_MATCHES = {'broadMatch'}

RELATION_SCORES = {'essential': 1.0, 'optional': 0.5}


def load_crosswalk(codes):
    crosswalk = pd.read_csv(CROSSWALK_FILE, skiprows=CROSSWALK_HEADER_ROWS, dtype=str, encoding='utf-8-sig')
    crosswalk = crosswalk.rename(columns={
        'O*NET Id': 'onet_soc_code', 'ESCO or ISCO URI': 'esco_uri',
        'ESCO or ISCO Title': 'esco_title', 'Type of Match': 'match_type',
    })[['onet_soc_code', 'esco_uri', 'esco_title', 'match_type']]
    # Links to ISCO groups have no skills of their own, only ESCO occupations do.
    crosswalk = crosswalk[crosswalk['onet_soc_code'].isin(codes) & crosswalk['esco_uri'].str.contains('/esco/occupation/')]

    preferred = crosswalk[crosswalk['match_type'].isin(PREFERRED_MATCHES)]
    fallback = crosswalk[
        crosswalk['match_type'].isin(FALLBACK_MATCHES)
        & ~crosswalk['onet_soc_code'].isin(preferred['onet_soc_code'])
    ]
    links = pd.concat([preferred, fallback]).drop_duplicates(['onet_soc_code', 'esco_uri'])

    missing = sorted(set(codes) - set(links['onet_soc_code']))
    if missing:
        raise ValueError(f'No ESCO occupation linked to: {missing}')
    return links.sort_values(['onet_soc_code', 'esco_uri'])


def weight_skills(links):
    relations = pd.read_csv(ESCO_DIR / 'occupationSkillRelations_en.csv', dtype=str)
    relations = relations.rename(columns={'occupationUri': 'esco_uri', 'skillUri': 'skill_uri', 'relationType': 'relation'})
    relations = relations[['esco_uri', 'skill_uri', 'relation']].drop_duplicates(['esco_uri', 'skill_uri'])

    linked = links[['onet_soc_code', 'esco_uri']].merge(relations, on='esco_uri')
    linked['score'] = linked['relation'].map(RELATION_SCORES)

    # A skill's weight is its mean score over all ESCO occupations linked to the
    # O*NET occupation, counting unlisted as 0. A skill listed by only one niche
    # specialisation therefore ends up with a low weight.
    per_occupation = links.groupby('onet_soc_code').size().rename('esco_occupations')
    skills = linked.groupby(['onet_soc_code', 'skill_uri']).agg(
        essential_in=('relation', lambda r: (r == 'essential').sum()),
        optional_in=('relation', lambda r: (r == 'optional').sum()),
        score_sum=('score', 'sum'),
    ).reset_index().merge(per_occupation, on='onet_soc_code')
    skills['weight'] = (skills['score_sum'] / skills['esco_occupations']).round(4)
    return skills.drop(columns='score_sum').sort_values(['onet_soc_code', 'weight', 'skill_uri'], ascending=[True, False, True])


def clean_alt_labels(value, label):
    if pd.isna(value):
        return ''
    labels = []
    for alt in value.split('\n'):
        alt = alt.strip()
        if alt and alt.lower() != label.lower() and alt.lower() not in {l.lower() for l in labels}:
            labels.append(alt)
    return '|'.join(labels)


def describe_skills(skill_uris):
    skills = pd.read_csv(ESCO_DIR / 'skills_en.csv', dtype=str)
    skills = skills[skills['conceptUri'].isin(skill_uris)]
    missing = set(skill_uris) - set(skills['conceptUri'])
    if missing:
        raise ValueError(f'{len(missing)} linked skills are missing from skills_en.csv')

    label = skills['preferredLabel'].str.strip()
    return pd.DataFrame({
        'skill_uri': skills['conceptUri'],
        'label': label,
        'skill_type': skills['skillType'].fillna('').str.strip(),
        'alt_labels': [clean_alt_labels(v, l) for v, l in zip(skills['altLabels'], label)],
    }).sort_values('label')


def main():
    codes = set(pd.read_csv(PROCESSED_DIR / 'occupations.csv', dtype=str)['onet_soc_code'])
    links = load_crosswalk(codes)
    occupation_skills = weight_skills(links)

    outputs = {
        'esco_occupations.csv': links,
        'esco_occupation_skills.csv': occupation_skills,
        'esco_skills.csv': describe_skills(occupation_skills['skill_uri'].unique()),
    }
    for filename, df in outputs.items():
        df.to_csv(PROCESSED_DIR / filename, index=False)
        print(f'{filename}: {len(df)} rows')


if __name__ == '__main__':
    main()
