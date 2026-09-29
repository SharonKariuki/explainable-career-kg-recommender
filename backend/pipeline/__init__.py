"""Data pipeline that turns raw O*NET and ESCO files into the AjiraGuide dataset.

Each step is a module run from `backend/`, e.g. `python -m pipeline.download`.
"""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'
RAW_DIR = DATA_DIR / 'raw'
PROCESSED_DIR = DATA_DIR / 'processed'
