"""Encode every skill label with a sentence-transformers model and cache the vectors.

Labels come from the processed dataset: O*NET rated skills, O*NET tools, and
ESCO preferred and alternative labels. The cache in data/cache/ keeps every
text encoded so far with the current model, so only new labels are encoded.
"""

import re
from functools import lru_cache

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


@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def encode(texts):
    """Unit-length embeddings for `texts`, one row per text."""
    return get_model().encode(list(texts), batch_size=128, normalize_embeddings=True).astype(np.float32)


def load_embeddings(texts):
    """Return {text: unit vector} for the given texts.

    Vectors already in the cache are reused; only texts it does not hold yet
    are encoded, and then added to it. The cache is discarded if it was built
    with a different model.
    """
    texts = set(texts)
    cache = {}
    if CACHE_FILE.exists():
        cached = np.load(CACHE_FILE, allow_pickle=False)
        if 'model' in cached.files and str(cached['model']) == MODEL_NAME:
            cache = dict(zip(cached['texts'].tolist(), cached['vectors']))

    missing = sorted(texts - cache.keys())
    if missing:
        cache.update(zip(missing, encode(missing)))
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(cache)
        np.savez(CACHE_FILE, model=MODEL_NAME, texts=np.array(ordered), vectors=np.stack([cache[t] for t in ordered]))
    return {text: cache[text] for text in texts}


def main():
    labels = skill_labels()
    vectors = load_embeddings(labels['label'])
    print(f'{len(labels)} skill labels, {len(vectors)} distinct texts encoded')
    print(labels.groupby(['source', 'preferred']).size().to_string())
    print(f'cache: {CACHE_FILE}')


if __name__ == '__main__':
    main()
