"""Encode every skill label with a sentence-transformers model and cache the vectors.

Labels come from the processed dataset: O*NET rated skills, O*NET tools, and
ESCO preferred and alternative labels. The cache in data/cache/ is reused as
long as the model and the set of labels are unchanged.
"""

import hashlib
import re

import numpy as np
import pandas as pd

from pipeline import DATA_DIR, PROCESSED_DIR

MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
CACHE_FILE = DATA_DIR / 'cache' / 'skill_embeddings.npz'


def strip_qualifier(label):
    """Drop ESCO's disambiguating suffix: 'Python (computer programming)' -> 'Python'."""
    return re.sub(r'\s*\([^)]*\)\s*$', '', label).strip()


def skill_labels():
    """Every label a skill is known by, one row per (skill, label)."""
    rated = pd.read_csv(PROCESSED_DIR / 'onet_skills.csv', dtype=str)
    tools = pd.read_csv(PROCESSED_DIR / 'onet_tools.csv', dtype=str)
    esco = pd.read_csv(PROCESSED_DIR / 'esco_skills.csv', dtype=str, keep_default_na=False)

    esco_alt = esco.assign(label=esco['alt_labels'].str.split('|')).explode('label')
    frames = [
        pd.DataFrame({'source': 'onet_skill', 'skill_id': rated['element_id'], 'label': rated['skill'], 'preferred': True}),
        pd.DataFrame({'source': 'onet_tool', 'skill_id': tools['tool'], 'label': tools['tool'], 'preferred': True}),
        pd.DataFrame({'source': 'esco', 'skill_id': esco['skill_uri'], 'label': esco['label'], 'preferred': True}),
        pd.DataFrame({'source': 'esco', 'skill_id': esco['skill_uri'], 'label': esco['label'].map(strip_qualifier), 'preferred': False}),
        pd.DataFrame({'source': 'esco', 'skill_id': esco_alt['skill_uri'], 'label': esco_alt['label'], 'preferred': False}),
    ]
    labels = pd.concat(frames, ignore_index=True)
    labels = labels[labels['label'].str.len() > 0]
    return labels.drop_duplicates(['source', 'skill_id', 'label']).reset_index(drop=True)


def fingerprint(texts):
    return hashlib.sha256('\n'.join([MODEL_NAME, *texts]).encode('utf-8')).hexdigest()


def load_embeddings(texts):
    """Return {text: unit vector} for the given texts, from cache when possible."""
    texts = sorted(set(texts))
    key = fingerprint(texts)

    if CACHE_FILE.exists():
        cached = np.load(CACHE_FILE, allow_pickle=False)
        if str(cached['fingerprint']) == key:
            return dict(zip(cached['texts'].tolist(), cached['vectors']))

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    vectors = model.encode(texts, batch_size=128, normalize_embeddings=True, show_progress_bar=True).astype(np.float32)
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE_FILE, fingerprint=key, texts=np.array(texts), vectors=vectors)
    return dict(zip(texts, vectors))


def main():
    labels = skill_labels()
    vectors = load_embeddings(labels['label'])
    print(f'{len(labels)} skill labels, {len(vectors)} distinct texts encoded')
    print(labels.groupby(['source', 'preferred']).size().to_string())
    print(f'cache: {CACHE_FILE}')


if __name__ == '__main__':
    main()
