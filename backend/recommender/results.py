"""Where evaluation runs write their results, and the v1 results they must not touch.

The v1 results are the files directly in data/results/ (tag v1-baseline).
Every later run writes to its own new folder, data/results/<run>/, and a run
is written once: an existing folder or file is never replaced. Each run
folder gets a manifest.json recording what produced it.
"""

import argparse
import dataclasses
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone

from pipeline import DATA_DIR, PROCESSED_DIR
from pipeline.embeddings import MODEL_NAME

REPO_DIR = DATA_DIR.parent
RESULTS_DIR = DATA_DIR / 'results'
RESERVED_RUNS = {'v1'}
RUN_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}')

# sha256 of each v1 file with line endings normalised to \n (Windows checks them out with \r\n).
V1_RESULTS = {
    'evaluation.csv': '2c8c333364a36f08b25354ad870332178772c2033c0c0ec3ae699a81ef90e00d',
    'explanation_quality.csv': 'ebfd59dcdb515c9c2e82e81ddc942d1701b53d24f9dfed6d650d50589f88042f',
    'tuning.csv': 'ec99ba0322db60b5924e50a38cc93ecae709231f6d88d7688ad750a6f829a3a1',
}


def normalised_hash(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def run_dir(run):
    """The folder for a new run; raises if the name is unsafe, reserved or already used."""
    if not RUN_NAME.fullmatch(run):
        raise ValueError(f'run name {run!r} must be letters, digits, "-" or "_" (at most 64)')
    if run.lower() in RESERVED_RUNS:
        raise ValueError(f'run name {run!r} is reserved for the published results')
    folder = RESULTS_DIR / run
    if folder.resolve().parent != RESULTS_DIR.resolve():
        raise ValueError(f'run name {run!r} points outside {RESULTS_DIR}')
    if folder.exists():
        raise FileExistsError(f'{folder} already exists; choose a new run name')
    return folder


def parse_run(description, argv=None):
    """Read the required --run argument and return its folder, before any work starts."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--run', required=True, help='name of the new folder under data/results/')
    args = parser.parse_args(argv)
    try:
        return run_dir(args.run)
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))


def write_csv(frame, folder, filename):
    """Write a results table into the run folder, refusing to replace any file."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    with open(path, 'x', newline='', encoding='utf-8') as file:
        frame.to_csv(file, index=False)
    return path


def uncommitted(status_lines):
    """Lines of `git status --porcelain` that make the tree dirty; new run folders do not count."""
    return [line for line in status_lines
            if not (line.startswith('?? data/results/') and line[len('?? data/results/'):].count('/') >= 1)]


def git_state():
    """{'commit', 'clean', 'changes'}; outside a git checkout the tree counts as dirty."""
    def git(*args):
        return subprocess.run(['git', *args], cwd=REPO_DIR, capture_output=True, text=True, check=True).stdout
    try:
        commit = git('rev-parse', 'HEAD').strip()
        changes = uncommitted(git('status', '--porcelain', '--untracked-files=all').splitlines())
    except (OSError, subprocess.CalledProcessError):
        return {'commit': None, 'clean': False, 'changes': ['not a git checkout']}
    return {'commit': commit, 'clean': not changes, 'changes': changes}


def run_started(module, argv=None):
    """What a run records before it starts working."""
    args = sys.argv[1:] if argv is None else argv
    return {'command': ' '.join(['python', '-m', module, *args]),
            'started': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'git': git_state()}


def configuration(params):
    """The engine parameters, model and graph data a run used, with a short identifier."""
    content = {
        'params': dataclasses.asdict(params) if params else None,
        'model': MODEL_NAME,
        'processed_data': {p.name: normalised_hash(p) for p in sorted(PROCESSED_DIR.glob('*.csv'))},
    }
    digest = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
    return {'id': digest[:12], **content}


def write_manifest(folder, started, sets, config):
    """Write manifest.json next to a run's results, refusing to replace one."""
    manifest = {'run': folder.name, **started,
                'finished': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'profile_sets': sets, 'configuration': config}
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / 'manifest.json', 'x', encoding='utf-8') as file:
        json.dump(manifest, file, indent=2)
    return manifest
