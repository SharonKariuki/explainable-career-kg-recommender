"""Ranking-invariance snapshot, approval and drift logic (Measured Matching C1, #157).

The CLI tests run on a small corpus with a fixed fingerprint, so they exercise every exit path
(fail closed, environment mismatch, ranking change, pass, drift, simulated drift) quickly.
"""
import copy
import json
import shutil
import subprocess

import pytest

from recommender import invariance as inv

FP = {
    'base_image_digest': 'sha256:' + 'a' * 64, 'python': '3.11.9', 'machine': 'x86_64', 'packages_sha256': 'p' * 64,
    'packages': ['numpy==2.4.6'], 'model_name': 'sentence-transformers/all-MiniLM-L6-v2',
    'model_revision': '1110a243fdf4706b3f48f1d95db1a4f5529b4d41', 'model_files': {'model.safetensors': 'm' * 64},
    'embedding_probe_sha256': 'e' * 64, 'processed_data': {'occupations.csv': 'o' * 64}, 'aliases_sha256': 's' * 64,
    'corpus_sha256': 'c' * 64,
}
SMALL = [('six-e2e', 'six-e2e-00', ['HTML', 'CSS', 'JavaScript'], '', 'plain'),
         ('constructed', 'constructed-00', ['Python', 'SQL'], '', 'plain'),
         ('background', 'background-00', ['Python'], 'I study statistics.', 'plain')]


@pytest.fixture(scope='module')
def small_profiles():
    return inv.snapshot_profiles(SMALL, {})


def write(folder, profiles, fp=FP, approve=True, sha=None):
    document = {'format': inv.FORMAT, 'status': 'provisional', 'fingerprint': fp, 'profile_count': len(profiles),
                'profiles': profiles}
    digest = inv.write_baseline(folder, document, fp['packages'])
    if approve:
        (folder / inv.APPROVAL_FILE).write_text(json.dumps(
            {'status': 'approved', 'approved_by': 'reviewer', 'approved_on': '2026-11-13',
             'snapshot_sha256': sha or digest}), encoding='utf-8')
    return digest


@pytest.fixture
def cli(monkeypatch, small_profiles):
    """Run the CLI on the small corpus with a fixed fingerprint (overridable per test)."""
    state = {'fp': FP, 'profiles': small_profiles}
    monkeypatch.setattr(inv, 'pin_threads', lambda: None)   # keep the test session's thread settings
    monkeypatch.setattr(inv, 'corpus', lambda: (SMALL, {}))
    monkeypatch.setattr(inv, 'fingerprint', lambda rows, digest=None: dict(state['fp']))
    monkeypatch.setattr(inv, 'snapshot_profiles', lambda rows, held: copy.deepcopy(state['profiles']))
    return state


# ---- Records and comparison ----

def test_records_are_deterministic(small_profiles):
    again = inv.snapshot_profiles(SMALL, {})
    assert again == small_profiles
    record = small_profiles[0]['record']
    assert record['ranking'] and all(len(r) == 7 for r in record['ranking'])
    assert all(isinstance(r[1], str) for r in record['ranking'])          # floats kept exactly, as repr
    assert small_profiles[2]['record']['ranking'][0][5] is not None      # the background path is recorded


def test_identical_records_compare_equal(small_profiles):
    assert inv.compare_records(small_profiles, copy.deepcopy(small_profiles)) == ([], [])


def test_a_changed_concept_order_or_fit_is_categorical(small_profiles):
    changed = copy.deepcopy(small_profiles)
    changed[0]['record']['matches'][0][1] = 'tool:Something else'
    changed[1]['record']['ranking'][0][6] = 'possible' if changed[1]['record']['ranking'][0][6] != 'possible' else 'good'
    changed[2]['record']['ranking'][0], changed[2]['record']['ranking'][1] = \
        changed[2]['record']['ranking'][1], changed[2]['record']['ranking'][0]
    categorical, _ = inv.compare_records(small_profiles, changed)
    fields = ' '.join(c[1] for c in categorical)
    assert 'match 0' in fields and 'fit' in fields and 'career order' in fields


def test_floats_are_exact_unless_a_tolerance_is_given(small_profiles):
    nudged = copy.deepcopy(small_profiles)
    nudged[0]['record']['ranking'][0][1] = repr(float(nudged[0]['record']['ranking'][0][1]) + 1e-12)
    assert inv.compare_records(small_profiles, nudged)[1]                         # exact: a 1e-12 change is caught
    assert inv.compare_records(small_profiles, nudged, tolerance=1e-9) == ([], [])  # cross-environment tolerance


def test_baseline_files_are_byte_reproducible(tmp_path, small_profiles):
    a, b = tmp_path / 'a', tmp_path / 'b'
    assert write(a, small_profiles, approve=False) == write(b, small_profiles, approve=False)
    assert (a / inv.SNAPSHOT_FILE).read_bytes() == (b / inv.SNAPSHOT_FILE).read_bytes()


# ---- Approval: the check fails closed ----

def test_approval_states(tmp_path, small_profiles):
    assert inv.approval_state(tmp_path / 'none') == 'missing'
    write(tmp_path, small_profiles, approve=False)
    assert inv.approval_state(tmp_path).startswith('provisional (no approval file)')
    (tmp_path / inv.APPROVAL_FILE).write_text(json.dumps({'status': 'pending'}))
    assert 'approval status' in inv.approval_state(tmp_path)
    write(tmp_path, small_profiles, sha='0' * 64)
    assert inv.approval_state(tmp_path) == 'provisional (approval names a different snapshot)'
    write(tmp_path, small_profiles)
    assert inv.approval_state(tmp_path) == 'approved'


def test_check_fails_closed_without_an_approved_baseline(tmp_path, cli, small_profiles):
    assert inv.main(['check', '--baseline', str(tmp_path / 'missing')]) == 2
    write(tmp_path, small_profiles, approve=False)
    assert inv.main(['check', '--baseline', str(tmp_path)]) == 2


def test_check_passes_on_an_identical_ranking(tmp_path, cli, small_profiles):
    write(tmp_path, small_profiles)
    assert inv.main(['check', '--baseline', str(tmp_path)]) == 0


def test_check_reports_environment_mismatch_not_a_ranking_result(tmp_path, cli, small_profiles):
    write(tmp_path, small_profiles)
    cli['fp'] = {**FP, 'model_revision': 'f' * 40}       # negative control: altered fingerprint
    assert inv.main(['check', '--baseline', str(tmp_path)]) == 3


def test_check_fails_on_a_ranking_change(tmp_path, cli, small_profiles):
    write(tmp_path, small_profiles)
    changed = copy.deepcopy(small_profiles)
    changed[0]['record']['ranking'][0][1] = repr(float(changed[0]['record']['ranking'][0][1]) + 1e-6)
    cli['profiles'] = changed
    assert inv.main(['check', '--baseline', str(tmp_path)]) == 4


# ---- Drift: separate job, altered-fingerprint negative controls ----

def drift(tmp_path, *extra, revision=FP['model_revision']):
    return inv.main(['drift', '--baseline', str(tmp_path), '--resolved-base-digest', FP['base_image_digest'],
                     '--resolved-model-revision', revision, '--report', str(tmp_path / 'report.json'), *extra])


def test_drift_job_passes_when_nothing_changed(tmp_path, cli, small_profiles):
    write(tmp_path, small_profiles)
    assert drift(tmp_path) == 0
    assert json.loads((tmp_path / 'report.json').read_text())['status'] == 'no drift'


def test_simulated_drift_fails_the_drift_job(tmp_path, cli, small_profiles):
    write(tmp_path, small_profiles)
    assert drift(tmp_path, '--simulate-drift') == 5
    report = json.loads((tmp_path / 'report.json').read_text())
    assert report['status'] == 'upstream drift (no ranking effect)' and report['simulated'] is True
    assert {'model_revision', 'base_image_digest'} <= set(report['differences'])


def test_an_altered_baseline_fingerprint_fails_the_drift_job(tmp_path, cli, small_profiles):
    write(tmp_path, small_profiles, fp={**FP, 'embedding_probe_sha256': '0' * 64})
    assert drift(tmp_path) == 5


def test_drift_with_a_ranking_change_is_reported_as_such(tmp_path, cli, small_profiles):
    write(tmp_path, small_profiles, fp={**FP, 'model_revision': '0' * 40})
    changed = copy.deepcopy(small_profiles)
    changed[0]['record']['ranking'][0], changed[0]['record']['ranking'][1] = \
        changed[0]['record']['ranking'][1], changed[0]['record']['ranking'][0]
    cli['profiles'] = changed
    assert drift(tmp_path, revision=FP['model_revision']) == 5
    assert json.loads((tmp_path / 'report.json').read_text())['status'] == 'upstream drift (ranking changed)'


def test_inconsistent_resolution_fails(tmp_path, cli, small_profiles):
    write(tmp_path, small_profiles)
    assert drift(tmp_path, revision='9' * 40) == 6


def test_drift_job_fails_closed_without_an_approved_baseline(tmp_path, cli, small_profiles):
    write(tmp_path, small_profiles, approve=False)
    assert drift(tmp_path) == 2


def test_drift_status_logic():
    same = dict(FP)
    assert inv.drift_status(FP, same, FP['model_revision'], [], []) == ('no drift', 0)
    assert inv.drift_status(FP, same, FP['model_revision'], [('p', 'f', 1, 2)], []) == ('ranking changed without upstream drift', 4)
    assert inv.drift_status(FP, {**FP, 'packages_sha256': 'x'}, FP['model_revision'], [], [])[1] == 5


# ---- Corpus and sources ----

def test_corpus_is_fixed_and_uses_no_test_set():
    rows, held = inv.corpus()          # would raise LockedSetError if a test seed were used
    sets = {}
    for name, *_ in rows:
        sets[name] = sets.get(name, 0) + 1
    assert sets == {'synthetic-validation': 360, 'noisy-validation': 360, 'hand-v1': 30, 'job-skills': 168,
                    'six-e2e': 18, 'constructed': 9, 'background': 6}
    assert len({(r[0], r[1]) for r in rows}) == len(rows)
    assert inv.corpus_sha256(rows) == inv.corpus_sha256(inv.corpus()[0])


@pytest.mark.skipif(shutil.which('git') is None, reason='git is needed to read the baseline commit')
def test_the_approved_baseline_was_generated_from_the_baseline_commit_sources():
    # Later phases change ranking sources (C2 edits matching.py); whether rankings moved is decided
    # by the snapshot comparison. What must always hold is the baseline's provenance: the approved
    # snapshot was generated from exactly the baseline commit's ranking sources.
    try:
        expected = inv.commit_source_hashes(inv.BASELINE_COMMIT)
    except subprocess.CalledProcessError:
        pytest.skip('baseline commit not in this clone')
    assert inv.approval_state(inv.BACKEND / 'tests' / 'snapshots') == 'approved'
    document = inv.read_baseline(inv.BACKEND / 'tests' / 'snapshots')
    assert document['ranking_sources_checked_against_baseline'] is True
    assert document['ranking_sources'] == expected


# ---- Drift diagnostics (#173): what the fresh image has installed, and its embedding cache ----

def test_package_inventory_lists_what_differs_from_the_baseline():
    inventory = inv.package_inventory(['numpy==2.4.6', 'pip==24.0', 'torch==2.14.0+cpu'],
                                      ['numpy==2.4.6', 'pip==24.0', 'torch==2.15.0+cpu', 'wheel==0.45.1'])
    assert inventory['only_installed'] == ['wheel==0.45.1']
    assert inventory['only_baseline'] == []
    assert inventory['version_differs'] == ['torch: 2.14.0+cpu -> 2.15.0+cpu']
    assert inventory['installed'] == ['numpy==2.4.6', 'pip==24.0', 'torch==2.15.0+cpu', 'wheel==0.45.1']


def test_the_drift_report_carries_the_inventory_and_cache_without_changing_the_status(tmp_path, cli, small_profiles):
    write(tmp_path, small_profiles, fp={**FP, 'embedding_cache_sha256': 'b' * 64})
    cli['fp'] = {**FP, 'packages': ['numpy==2.4.6', 'wheel==0.45.1'], 'embedding_cache_sha256': 'c' * 64}
    assert drift(tmp_path) == 0                     # packages_sha256 is unchanged in FP, so no drift is declared
    report = json.loads((tmp_path / 'report.json').read_text())
    assert report['status'] == 'no drift'
    assert report['inventory']['only_installed'] == ['wheel==0.45.1']
    assert report['embedding_cache'] == {'baseline_sha256': 'b' * 64, 'installed_sha256': 'c' * 64}
