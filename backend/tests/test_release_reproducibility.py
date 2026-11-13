"""Production builds reproduce the approved ranking environment (release readiness, P0).

The upstream-drift job showed that a fresh image resolved newer transitive packages than the
approved baseline and that rankings moved with them. The image now installs exactly the approved
lock and the application loads the approved model revision; these tests keep it that way.
"""
import re
from pathlib import Path

from pipeline import embeddings
from recommender import invariance as inv

BACKEND = Path(__file__).resolve().parents[1]
LOCK = BACKEND / 'tests' / 'snapshots' / 'requirements_lock_v1.txt'


def pins(path):
    out = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.split('#')[0].strip()
        if line:
            name, version = line.split('==')
            out[name.strip().lower().replace('_', '-')] = version.strip()
    return out


def test_the_image_installs_exactly_the_approved_lock():
    dockerfile = (BACKEND / 'Dockerfile').read_text(encoding='utf-8')
    assert 'COPY backend/tests/snapshots/requirements_lock_v1.txt requirements.lock' in dockerfile
    install = re.search(r'RUN pip install ([^\n]*(?:\\\n[^\n]*)*)', dockerfile).group(1)
    assert '--no-deps' in install and '-r requirements.lock' in install
    assert 'requirements.txt' not in dockerfile                       # no second, unpinned resolution


def test_requirements_agree_with_the_lock():
    lock = pins(LOCK)
    for name, version in pins(BACKEND / 'requirements.txt').items():
        assert lock.get(name, '').split('+')[0] == version, f'{name}=={version} differs from the lock'


def test_the_lock_is_the_approved_baseline_lock():
    document = inv.read_baseline(BACKEND / 'tests' / 'snapshots')
    assert inv.approval_state(BACKEND / 'tests' / 'snapshots') == 'approved'
    assert sorted(document['fingerprint']['packages']) == sorted(
        l.strip() for l in LOCK.read_text(encoding='utf-8').splitlines() if l.strip())


def test_the_application_loads_the_approved_model_revision():
    document = inv.read_baseline(BACKEND / 'tests' / 'snapshots')
    assert embeddings.MODEL_REVISION == document['fingerprint']['model_revision']
