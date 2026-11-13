"""Provision the baseline SBERT model for offline loading, and verify it (Measured Matching C1, #157).

Downloads exactly the files SentenceTransformer(MODEL_NAME) uses at one revision into an
empty HF_HOME, then writes refs/main = that revision. Both steps are needed: a snapshot
downloaded by revision alone is not found by an offline load, because the application asks
for the default revision ("main"), which resolves through refs/main.

Every file's sha256 is checked against the approved baseline fingerprint, and LFS files also
against the hashes Hugging Face publishes for that revision. Any mismatch exits non-zero.

    python .github/scripts/provision_model.py --hf-home DIR --baseline backend/tests/snapshots
    python .github/scripts/provision_model.py --hf-home DIR --revision SHA   # bootstrap: no baseline yet
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from recommender.invariance import MODEL_FILES, approval_state, read_baseline  # noqa: E402

MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--hf-home', required=True)
    parser.add_argument('--baseline', help='folder holding the approved baseline snapshot')
    parser.add_argument('--revision', help='revision to provision when there is no baseline yet')
    parser.add_argument('--report')
    args = parser.parse_args(argv)

    import os
    os.environ['HF_HOME'] = args.hf_home
    os.environ['HF_HUB_OFFLINE'] = '0'
    from huggingface_hub import HfApi, snapshot_download

    expected = {}
    revision = args.revision
    if args.baseline:
        state = approval_state(args.baseline)
        if state != 'approved':
            print(f'Baseline in {args.baseline} is not approved ({state}); its pins are not used.', file=sys.stderr)
            return 2
        document = read_baseline(args.baseline)
        revision = document['fingerprint']['model_revision']
        expected = document['fingerprint']['model_files']
    if not revision:
        print('No baseline and no --revision: nothing to provision.', file=sys.stderr)
        return 2

    snapshot = Path(snapshot_download(MODEL_NAME, revision=revision, allow_patterns=list(MODEL_FILES)))
    if snapshot.name != revision:
        print(f'Downloaded snapshot {snapshot.name} is not the requested revision {revision}.', file=sys.stderr)
        return 3
    refs = snapshot.parents[1] / 'refs'
    refs.mkdir(exist_ok=True)
    (refs / 'main').write_text(revision)

    local = {f: hashlib.sha256((snapshot / f).read_bytes()).hexdigest() for f in MODEL_FILES}
    published = {s.rfilename: s.lfs.sha256 for s in HfApi().model_info(MODEL_NAME, revision=revision,
                                                                       files_metadata=True).siblings if s.lfs}
    problems = [f'{f}: baseline {expected[f]} != downloaded {local[f]}' for f in MODEL_FILES if expected and expected.get(f) != local[f]]
    problems += [f'{f}: published {published[f]} != downloaded {local[f]}' for f in MODEL_FILES if f in published and published[f] != local[f]]
    report = {'model': MODEL_NAME, 'revision': revision, 'refs_main': (refs / 'main').read_text(),
              'files': local, 'checked_against_baseline': bool(expected),
              'checked_against_published_lfs': sorted(f for f in MODEL_FILES if f in published), 'problems': problems}
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=1), encoding='utf-8')
    print(json.dumps(report, indent=1))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
