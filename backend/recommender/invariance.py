"""Ranking-invariance snapshot and environment fingerprint (Measured Matching C1, #157).

Measured Matching must not change any ranking. This module records, for a fixed corpus of
profiles, everything the ranking produces: the concept each skill was read as, the existing
`low_confidence` flag, the full career order with score and components, `fit`, and the
skills behind coverage. A later change passes only if it reproduces that record.

The record is meaningful only in the environment it was made in, so it carries a fingerprint:
base image, Python packages, model revision and files, an embedding probe, the processed data,
the corpus, and the sources that determine the ranking (checked against the baseline commit).

Commands (from backend/):
    python -m recommender.invariance generate --out DIR [--expected-sources FILE] [--base-image-digest D]
    python -m recommender.invariance check --baseline DIR [--base-image-digest D]
    python -m recommender.invariance drift --baseline DIR --resolved-base-digest D --resolved-model-revision R
                                           [--simulate-drift]
    python -m recommender.invariance sources [--commit SHA]

Exit codes: 0 pass; 2 no approved baseline; 3 environment mismatch; 4 ranking changed;
5 upstream drift (the drift command); 6 inconsistent resolution; 7 baseline sources differ.
"""

import argparse
import gzip
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
BASELINE_COMMIT = '739956a37ef3f3a8b2c0032d359979d770bb4d66'
SNAPSHOT_FILE = 'ranking_invariance_v1.json.gz'
LOCK_FILE = 'requirements_lock_v1.txt'
APPROVAL_FILE = 'approval_v1.json'   # written by a reviewer, never by this module
FORMAT = 'ajiraguide-ranking-invariance/1'

# The files that determine what the ranking is, relative to the repository root. The baseline
# snapshot may only be generated from a tree where these equal BASELINE_COMMIT.
RANKING_SOURCES = (
    'backend/recommender/engine.py', 'backend/recommender/matching.py', 'backend/recommender/graph.py',
    'backend/recommender/explanation.py', 'backend/recommender/skill_aliases.csv',
    'backend/pipeline/__init__.py', 'backend/pipeline/embeddings.py', 'backend/pipeline/onet.py',
    'backend/requirements.txt',
)
RANKING_SOURCE_GLOBS = ('data/processed/*.csv',)
# Files SentenceTransformer(MODEL_NAME) downloads for this model; the fingerprint hashes these.
MODEL_FILES = (
    '1_Pooling/config.json', 'README.md', 'config.json', 'config_sentence_transformers.json', 'model.safetensors',
    'modules.json', 'sentence_bert_config.json', 'special_tokens_map.json', 'tokenizer.json',
    'tokenizer_config.json', 'vocab.txt',
)
# Fingerprint fields that must match the baseline for a comparison to mean anything.
ENVIRONMENT_FIELDS = ('base_image_digest', 'python', 'machine', 'packages_sha256', 'model_name', 'model_revision',
                      'model_files', 'embedding_probe_sha256', 'processed_data', 'aliases_sha256')
# Fields whose change, in the scheduled job, is upstream drift.
DRIFT_FIELDS = ('base_image_digest', 'packages_sha256', 'model_revision', 'model_files', 'embedding_probe_sha256')
DRIFT_FLOAT_TOLERANCE = 1e-9
# Environment variables that decide how floating-point work is split and which CPU code paths
# torch, MKL, oneDNN and OpenBLAS take. GitHub runners vary in CPU model, so these are fixed
# by the workflows and recorded here.
NUMERIC_ENV = ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'ATEN_CPU_CAPABILITY',
               'OPENBLAS_CORETYPE', 'MKL_CBWR', 'ONEDNN_MAX_CPU_ISA', 'DNNL_MAX_CPU_ISA')

# Profiles beyond the generated sets: the six evaluated students with their wordings, the
# constructed evidence cases, and profiles with background text (the 40% background path).
EXTRA_PROFILES = {
    'six-e2e': [
        ['HTML', 'CSS', 'JavaScript', 'React', 'Git'],
        ['web pages', 'styling websites', 'JS', 'React.js', 'version control'],
        ['building websites', 'responsive design', 'front-end JavaScript', 'React components', 'GitHub'],
        ['Python', 'Django', 'SQL', 'REST APIs', 'Git'],
        ['Python programming', 'Django web framework', 'databases', 'building APIs', 'GitHub'],
        ['server-side development', 'Python', 'writing SQL queries', 'RESTful web services', 'version control'],
        ['Python', 'SQL', 'Excel', 'statistics', 'Power BI'],
        ['data analysis in Python', 'writing SQL queries', 'spreadsheets', 'statistical analysis', 'dashboards'],
        ['pandas', 'databases', 'Microsoft Excel', 'probability and statistics', 'data visualisation'],
        ['TCP/IP', 'routing', 'Linux', 'network troubleshooting', 'Cisco'],
        ['network protocols', 'configuring routers', 'Linux administration', 'fixing network problems', 'Cisco IOS'],
        ['CCNA', 'IP addressing and subnetting', 'Ubuntu', 'diagnosing connectivity issues', 'switches and routers'],
        ['Linux', 'networking', 'security analysis', 'incident response', 'SIEM'],
        ['Linux', 'computer networks', 'analysing security threats', 'responding to security incidents', 'Splunk'],
        ['SOC analyst work', 'threat detection', 'log analysis', 'handling cyber attacks', 'Kali Linux'],
        ['Python', 'SQL'],
        ['python', 'sql'],
        ['coding in Python', 'databases'],
    ],
    'constructed': [
        ['Python', 'sql', 'JavaScript', 'Hypertext markup language HTML', 'Cascading style sheets CSS', 'Git',
         'GitHub', 'problem solving'],
        ['Python', 'Python programming', 'coding in Python', 'Python scripting', 'Python 3'],
        ['ICT network routing', 'Cisco IOS', 'implement a virtual private network', 'Firewall software',
         'design computer network'],
        ['ADP Workforce Now', 'Anti-Trojan software', '3D graphics software', 'Arping', 'Adobe Distiller'],
        ['eMASS', 'Hugging Face', 'keep up to date on product knowledge', 'Microsoft Azure Data Factory',
         'Operational Data Store ODS software'],
        ['Solidity', 'smart contract', 'eMASS', 'MITRE ATT&CK software'],
        ['Linear algebra', 'Calculus', 'Cypress', 'Playwright', 'AWK', 'Ada'],
        ['playing guitar', 'cooking'],
        [],
    ],
}
BACKGROUND_PROFILES = [
    (['Python', 'SQL'], 'I study statistics and enjoy building predictive models.'),
    (['HTML', 'CSS', 'JavaScript'], 'I want to design websites that are easy to use.'),
    (['Linux', 'networking'], 'Two years of IT support; I want to move into network administration.'),
    (['Excel'], 'Business degree; interested in dashboards and reporting.'),
    (['Java', 'Git'], 'Computer science student who likes building backend services.'),
    (['incident response', 'SIEM'], 'I want to work in a security operations centre.'),
]
PROBE_TEXTS = sorted({s for group in EXTRA_PROFILES.values() for p in group for s in p} | {'probe sentence'})


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def normalised_sha256(data):
    """sha256 with CRLF folded to LF, so a Windows checkout and a Linux checkout agree."""
    return _sha256(data.replace(b'\r\n', b'\n'))


def canonical_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


# ---- Sources ----

def ranking_source_paths(root=REPO):
    paths = list(RANKING_SOURCES)
    for pattern in RANKING_SOURCE_GLOBS:
        paths += sorted(str(p.relative_to(root)).replace('\\', '/') for p in root.glob(pattern))
    return paths


def source_hashes(read_bytes, paths):
    return {p: normalised_sha256(read_bytes(p)) for p in paths}


def worktree_source_hashes(root=REPO):
    return source_hashes(lambda p: (root / p).read_bytes(), ranking_source_paths(root))


def commit_source_hashes(commit, root=REPO):
    def read(path):
        return subprocess.run(['git', 'show', f'{commit}:{path}'], cwd=root, capture_output=True, check=True).stdout
    return source_hashes(read, ranking_source_paths(root))


# ---- Corpus ----

def corpus():
    """[(set name, profile id, skills, background, engine key)], in a fixed order, no test sets."""
    from recommender.evaluation import hand_written_profiles, noisy_validation, validation_profiles
    from recommender.graph import get_graph
    from recommender.job_profiles import job_profiles, load_jobs

    kg = get_graph()
    rows = [('synthetic-validation', p.profile_id, list(p.skills), '', 'plain') for p in validation_profiles(kg)]
    held, noisy = noisy_validation(kg)
    rows += [('noisy-validation', p.profile_id, list(p.skills), '', 'hidden') for p in noisy]
    rows += [('hand-v1', p.profile_id, list(p.skills), '', 'plain') for p in hand_written_profiles(kg)]
    rows += [('job-skills', f'{code}/{variant}', list(skills), '', 'plain')
             for code, variant, skills in job_profiles(load_jobs())]
    for name, profiles in EXTRA_PROFILES.items():
        rows += [(name, f'{name}-{i:02d}', list(s), '', 'plain') for i, s in enumerate(profiles)]
    rows += [('background', f'background-{i:02d}', list(s), b, 'plain') for i, (s, b) in enumerate(BACKGROUND_PROFILES)]
    return rows, held


def corpus_sha256(rows):
    return _sha256(canonical_json([list(r) for r in rows]).encode())


# ---- Snapshot ----

def record(engine, skills, background=''):
    """The canonical ranking record for one profile. Floats are kept exactly, as repr."""
    from recommender.explanation import fit_level

    matches, recs = engine.rank(skills, top_k=None, background=background)
    return {
        'matches': [[m.query, m.node_id, repr(m.similarity), m.low_confidence] for m in matches],
        'ranking': [[r.career_id, repr(r.score), repr(r.components.coverage), repr(r.components.profile_similarity),
                     repr(r.components.graph_proximity),
                     None if r.components.background_similarity is None else repr(r.components.background_similarity),
                     fit_level(r.score)] for r in recs],
        'contributions': [[r.career_id, [[c.skill_id, repr(c.coverage_share)] for c in r.skill_contributions]]
                          for r in recs],
    }


def engines(held):
    from recommender.engine import RecommendationEngine, get_engine
    from recommender.graph import get_graph
    from recommender.matching import SkillMatcher

    kg = get_graph()
    return {'plain': get_engine(), 'hidden': RecommendationEngine(kg, SkillMatcher(kg, held.values()))}


def snapshot_profiles(rows, held):
    found = engines(held)
    return [{'set': s, 'id': pid, 'skills': skills, 'background': background,
             'record': record(found[key], skills, background)} for s, pid, skills, background, key in rows]


# ---- Fingerprint ----

def packages():
    return sorted(f'{d.metadata["Name"].lower()}=={d.version}' for d in metadata.distributions() if d.metadata['Name'])


def cpu_info():
    info = {'processor': platform.processor()}
    cpuinfo = Path('/proc/cpuinfo')
    if cpuinfo.exists():
        text = cpuinfo.read_text(errors='replace')
        model = next((line.split(':', 1)[1].strip() for line in text.splitlines() if line.startswith('model name')), '')
        flags = next((line.split(':', 1)[1].split() for line in text.splitlines() if line.startswith('flags')), [])
        info.update(model=model, avx2='avx2' in flags, avx512f='avx512f' in flags)
    return info


def model_snapshot_dir():
    """The snapshot directory, and revision, that SentenceTransformer(MODEL_NAME) loads from.

    The loaded model only reports its repository name, so the snapshot is found the way the
    hub resolves it for the loader: through refs/main in the cache (`try_to_load_from_cache`).
    The offline-provisioning check showed this is what selects the files: pointing refs/main
    at a decoy snapshot changes the embeddings, and pointing it back restores them exactly.
    """
    from huggingface_hub import try_to_load_from_cache
    from pipeline.embeddings import MODEL_NAME, get_model

    get_model()   # load first, exactly as the application does
    resolved = try_to_load_from_cache(MODEL_NAME, 'config.json')
    if not isinstance(resolved, str):
        raise RuntimeError(f'{MODEL_NAME} is not resolvable from the local cache (refs/main missing?)')
    path = Path(resolved).parent
    if path.parent.name != 'snapshots':
        raise RuntimeError(f'model resolved outside a Hugging Face snapshot directory: {path}')
    return path, path.name


def model_file_hashes(snapshot):
    missing = [f for f in MODEL_FILES if not (snapshot / f).is_file()]
    if missing:
        raise RuntimeError(f'model snapshot {snapshot} lacks {missing}')
    return {f: _sha256((snapshot / f).read_bytes()) for f in MODEL_FILES}


def embedding_probe():
    from pipeline.embeddings import encode

    vectors = encode(PROBE_TEXTS)
    return _sha256(vectors.tobytes()), _sha256(vectors.round(6).tobytes())


def fingerprint(rows, base_image_digest=None):
    import torch
    from pipeline.embeddings import CACHE_FILE, MODEL_NAME
    from recommender.matching import ALIASES_FILE
    from recommender.results import configuration

    snapshot, revision = model_snapshot_dir()
    probe_exact, probe_rounded = embedding_probe()
    pkgs = packages()
    return {
        'base_image_digest': base_image_digest or os.environ.get('BASE_IMAGE_DIGEST') or 'unknown',
        'python': platform.python_version(),
        'machine': platform.machine(),
        'os': platform.platform(),
        'cpu': cpu_info(),
        'threads': {'torch': torch.get_num_threads(), **{k: os.environ.get(k) for k in NUMERIC_ENV}},
        'packages_sha256': _sha256('\n'.join(pkgs).encode()),
        'packages': pkgs,
        'model_name': MODEL_NAME,
        'model_revision': revision,
        'model_files': model_file_hashes(snapshot),
        'hf_offline': os.environ.get('HF_HUB_OFFLINE'),
        'embedding_probe_sha256': probe_exact,
        'embedding_probe_rounded_sha256': probe_rounded,
        'embedding_cache_sha256': _sha256(CACHE_FILE.read_bytes()) if CACHE_FILE.exists() else None,
        'processed_data': configuration(None)['processed_data'],
        'aliases_sha256': normalised_sha256(ALIASES_FILE.read_bytes()),
        'corpus_sha256': corpus_sha256(rows),
    }


def pin_threads():
    """One thread everywhere: the snapshot must not depend on how work is split across cores."""
    for name in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'):
        os.environ.setdefault(name, '1')
    import torch
    torch.set_num_threads(1)


# ---- Baseline files ----

def write_baseline(folder, document, lock_lines):
    folder.mkdir(parents=True, exist_ok=True)
    raw = canonical_json(document).encode()
    with open(folder / SNAPSHOT_FILE, 'wb') as f:
        with gzip.GzipFile(fileobj=f, mode='wb', mtime=0) as gz:   # mtime 0: identical input, identical file
            gz.write(raw)
    (folder / LOCK_FILE).write_text('\n'.join(lock_lines) + '\n', encoding='utf-8')
    return _sha256(raw)


def read_snapshot(folder):
    """(document, sha256 of its canonical content), or (None, None) when there is no snapshot."""
    path = Path(folder) / SNAPSHOT_FILE
    if not path.exists():
        return None, None
    with gzip.open(path, 'rb') as f:
        raw = f.read()
    return json.loads(raw.decode('utf-8')), _sha256(raw)


def read_approval(folder):
    path = Path(folder) / APPROVAL_FILE
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def approval_state(folder):
    """'approved', or the reason the baseline is not approved. A generated snapshot is always
    provisional; it becomes the baseline only when approval_v1.json names it by content sha256."""
    document, digest = read_snapshot(folder)
    if document is None:
        return 'missing'
    approval = read_approval(folder)
    if approval is None:
        return 'provisional (no approval file)'
    if approval.get('status') != 'approved' or not approval.get('approved_by') or not approval.get('approved_on'):
        return f'provisional (approval status {approval.get("status")!r})'
    if approval.get('snapshot_sha256') != digest:
        return 'provisional (approval names a different snapshot)'
    return 'approved'


def read_baseline(folder):
    """The snapshot document (approved or not); None when absent."""
    return read_snapshot(folder)[0]


def is_approved(folder):
    return approval_state(folder) == 'approved'


# ---- Comparison ----

def float_equal(a, b, tolerance):
    if a is None or b is None:
        return a is b
    if tolerance == 0:
        return a == b
    return abs(float(a) - float(b)) <= tolerance


def compare_records(baseline, current, tolerance=0.0, limit=20):
    """Differences between two lists of profile records, as (profile, field, baseline, current).

    Categorical fields (query, node, low_confidence, order, fit, contributing skills) must be
    equal exactly; floats must be equal exactly unless `tolerance` is given. Returns
    (categorical differences, float differences), each capped at `limit` entries.
    """
    categorical, floats = [], []

    def add(bucket, *item):
        if len(bucket) < limit:
            bucket.append(item)

    base = {(p['set'], p['id']): p for p in baseline}
    cur = {(p['set'], p['id']): p for p in current}
    if list(base) != list(cur):
        add(categorical, 'corpus', 'profile ids', len(base), len(cur))
        return categorical, floats
    for key, b in base.items():
        c = cur[key]
        where = f'{key[0]}/{key[1]}'
        if (b['skills'], b['background']) != (c['skills'], c['background']):
            add(categorical, where, 'input', b['skills'], c['skills'])
            continue
        bm, cm = b['record']['matches'], c['record']['matches']
        if len(bm) != len(cm):
            add(categorical, where, 'matches count', len(bm), len(cm))
        for i, (x, y) in enumerate(zip(bm, cm)):
            if (x[0], x[1], x[3]) != (y[0], y[1], y[3]):
                add(categorical, where, f'match {i} (query, node, low_confidence)', [x[0], x[1], x[3]], [y[0], y[1], y[3]])
            elif not float_equal(x[2], y[2], tolerance):
                add(floats, where, f'match {i} similarity', x[2], y[2])
        br, cr = b['record']['ranking'], c['record']['ranking']
        if [r[0] for r in br] != [r[0] for r in cr]:
            add(categorical, where, 'career order', [r[0] for r in br][:5], [r[0] for r in cr][:5])
            continue
        for x, y in zip(br, cr):
            if x[6] != y[6]:
                add(categorical, where, f'{x[0]} fit', x[6], y[6])
            for j, name in enumerate(('score', 'coverage', 'profile_similarity', 'graph_proximity', 'background_similarity'), 1):
                if not float_equal(x[j], y[j], tolerance):
                    add(floats, where, f'{x[0]} {name}', x[j], y[j])
        for (career, bs), (_, cs) in zip(b['record']['contributions'], c['record']['contributions']):
            if [s for s, _ in bs] != [s for s, _ in cs]:
                add(categorical, where, f'{career} contributing skills', [s for s, _ in bs], [s for s, _ in cs])
            else:
                for (s, x), (_, y) in zip(bs, cs):
                    if not float_equal(x, y, tolerance):
                        add(floats, where, f'{career} {s} coverage_share', x, y)
    return categorical, floats


def environment_differences(baseline_fp, current_fp, fields=ENVIRONMENT_FIELDS):
    return {f: (baseline_fp.get(f), current_fp.get(f)) for f in fields if baseline_fp.get(f) != current_fp.get(f)}


def drift_status(baseline_fp, current_fp, resolved_model_revision, categorical, floats):
    """(status, exit code) for the scheduled upstream-drift job (plan revision 6, C5).

    `floats` must come from a comparison at DRIFT_FLOAT_TOLERANCE.
    """
    if resolved_model_revision != current_fp.get('model_revision'):
        return 'inconsistent resolution', 6
    drifted = environment_differences(baseline_fp, current_fp, DRIFT_FIELDS)
    if not drifted and not categorical and not floats:
        return 'no drift', 0
    if drifted and not categorical and not floats:
        return 'upstream drift (no ranking effect)', 5
    if drifted:
        return 'upstream drift (ranking changed)', 5
    return 'ranking changed without upstream drift', 4


# ---- Commands ----

def cmd_sources(args):
    hashes = commit_source_hashes(args.commit) if args.commit else worktree_source_hashes()
    print(json.dumps(hashes, indent=1, sort_keys=True))
    return 0


def cmd_generate(args):
    pin_threads()
    sources = worktree_source_hashes()
    if args.expected_sources:
        expected = json.loads(Path(args.expected_sources).read_text(encoding='utf-8'))
        if expected != sources:
            differing = sorted(k for k in set(expected) | set(sources) if expected.get(k) != sources.get(k))
            print(f'Ranking sources differ from baseline commit {BASELINE_COMMIT[:7]}: {differing}', file=sys.stderr)
            return 7
    rows, held = corpus()
    profiles = snapshot_profiles(rows, held)
    fp = fingerprint(rows, args.base_image_digest)   # after the snapshot, so the embedding cache exists and is hashed
    document = {
        'format': FORMAT,
        'status': 'provisional',
        'note': (f'Generated automatically; unapproved. It becomes the baseline only when a reviewer adds '
                 f'{APPROVAL_FILE} naming this snapshot by content sha256.'),
        'baseline_commit': BASELINE_COMMIT,
        # The branch head, not GitHub's synthetic PR merge commit (the workflow passes the head SHA).
        'generated_from_commit': os.environ.get('GIT_COMMIT') or args.commit or 'unknown',
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'ranking_sources': sources,
        'ranking_sources_checked_against_baseline': bool(args.expected_sources),
        'fingerprint': fp,
        'profile_count': len(profiles),
        'profiles': profiles,
    }
    digest = write_baseline(Path(args.out), document, fp['packages'])
    print(json.dumps({'written': str(Path(args.out) / SNAPSHOT_FILE), 'content_sha256': digest,
                      'profiles': len(profiles), 'status': 'provisional', 'model_revision': fp['model_revision'],
                      'base_image_digest': fp['base_image_digest'], 'corpus_sha256': fp['corpus_sha256']}, indent=1))
    return 0


def cmd_check(args):
    state = approval_state(args.baseline)
    if state != 'approved':
        print(f'No approved baseline in {args.baseline} ({state}). The check fails closed.', file=sys.stderr)
        return 2
    baseline = read_baseline(args.baseline)
    pin_threads()
    rows, held = corpus()
    current_fp = fingerprint(rows, args.base_image_digest)
    mismatch = environment_differences(baseline['fingerprint'], current_fp)
    if mismatch:
        print('Environment mismatch: the pinned baseline environment was not reproduced, so no ranking result is '
              'reported.', file=sys.stderr)
        for field, (b, c) in mismatch.items():
            print(f'  {field}: baseline {str(b)[:120]} | here {str(c)[:120]}', file=sys.stderr)
        for field in ('cpu', 'threads'):   # context: runners differ in CPU model
            print(f'  {field} (not compared): baseline {baseline["fingerprint"].get(field)} | here {current_fp.get(field)}',
                  file=sys.stderr)
        return 3
    categorical, floats = compare_records(baseline['profiles'], snapshot_profiles(rows, held), tolerance=0.0)
    if categorical or floats:
        print(f'Ranking changed: {len(categorical)} categorical and {len(floats)} float differences (first shown).',
              file=sys.stderr)
        for d in (categorical + floats)[:20]:
            print('  ', d, file=sys.stderr)
        return 4
    print(f'Ranking invariant: {baseline["profile_count"]} profiles identical to the approved baseline.')
    return 0


def cmd_drift(args):
    state = approval_state(args.baseline)
    if state != 'approved':
        print(f'No approved baseline in {args.baseline} ({state}). Drift cannot be judged; failing closed.',
              file=sys.stderr)
        return 2
    baseline = read_baseline(args.baseline)
    baseline_fp = dict(baseline['fingerprint'])
    if args.simulate_drift:   # dry run: a deliberately altered baseline fingerprint must fail the job
        baseline_fp['model_revision'] = '0' * 40
        baseline_fp['base_image_digest'] = 'sha256:' + '0' * 64
    pin_threads()
    rows, held = corpus()
    current_fp = fingerprint(rows, args.resolved_base_digest)
    categorical, floats = compare_records(baseline['profiles'], snapshot_profiles(rows, held),
                                          tolerance=DRIFT_FLOAT_TOLERANCE)
    status, code = drift_status(baseline_fp, current_fp, args.resolved_model_revision, categorical, floats)
    report = {'status': status, 'simulated': bool(args.simulate_drift),
              'baseline': {f: baseline_fp.get(f) for f in DRIFT_FIELDS},
              'resolved': {'base_image_digest': args.resolved_base_digest, 'model_revision': args.resolved_model_revision},
              'downloaded': {f: current_fp.get(f) for f in DRIFT_FIELDS},
              'differences': {f: v for f, v in environment_differences(baseline_fp, current_fp, DRIFT_FIELDS).items()},
              'ranking': {'categorical': [list(map(str, d)) for d in categorical],
                          'float_beyond_1e-9': [list(map(str, d)) for d in floats]}}
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=1, default=str), encoding='utf-8')
    print(f'Upstream drift status: {status}')
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('sources'); s.add_argument('--commit')
    g = sub.add_parser('generate'); g.add_argument('--out', required=True); g.add_argument('--expected-sources')
    g.add_argument('--base-image-digest'); g.add_argument('--commit')
    c = sub.add_parser('check'); c.add_argument('--baseline', required=True); c.add_argument('--base-image-digest')
    d = sub.add_parser('drift'); d.add_argument('--baseline', required=True)
    d.add_argument('--resolved-base-digest', required=True); d.add_argument('--resolved-model-revision', required=True)
    d.add_argument('--simulate-drift', action='store_true'); d.add_argument('--report')
    args = parser.parse_args(argv)
    return {'sources': cmd_sources, 'generate': cmd_generate, 'check': cmd_check, 'drift': cmd_drift}[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
