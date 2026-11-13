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


def test_the_image_builds_its_embedding_cache_with_the_gates_portable_arithmetic():
    """The cache baked at build time must equal the one the gate computes (#173); this step's
    environment and pin_threads() must match the invariance workflow's settings."""
    dockerfile = (BACKEND / 'Dockerfile').read_text(encoding='utf-8')
    step = next(block for block in dockerfile.split('\nRUN ') if 'warm_up()' in block)
    gate = (BACKEND.parent / '.github' / 'workflows' / 'invariance-pr.yml').read_text(encoding='utf-8')
    for setting in ('OMP_NUM_THREADS=1', 'MKL_NUM_THREADS=1', 'OPENBLAS_NUM_THREADS=1',
                    'ATEN_CPU_CAPABILITY=default', 'MKL_CBWR=COMPATIBLE', 'OPENBLAS_CORETYPE=Haswell'):
        assert setting in step and setting in gate, setting
    assert step.index('pin_threads()') < step.index('warm_up()')
    assert 'ENV ATEN_CPU_CAPABILITY' not in dockerfile          # build step only; the server is unchanged


def test_the_image_removes_packages_the_lock_does_not_list_and_checks_its_inventory():
    """The base image ships `wheel`, which the lock does not list (drift run 43417955162, #173)."""
    dockerfile = (BACKEND / 'Dockerfile').read_text(encoding='utf-8')
    assert 'pip uninstall --yes wheel' in dockerfile
    assert 'installed packages differ from the approved lock' in dockerfile
    assert dockerfile.index('pip uninstall --yes wheel') < dockerfile.index('warm_up()')
