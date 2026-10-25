"""The evaluation protocol (docs/evaluation_protocol.md): set roles, the test-set lock and run manifests."""

import ast
import json
from pathlib import Path

import pytest

from recommender import evaluate, evaluation, explanation_quality, results, tuning
from recommender.evaluation import (
    PROFILE_SETS, TEST_SEED, LockedSetError, describe_sets, generate_profiles, held_out_names, noisy_profiles,
    noisy_test, open_test_sets, test_profiles as make_test_profiles,
)
from recommender.graph import get_graph

BACKEND = Path(__file__).resolve().parents[1]

# The v1 profile sets, hashed before the lock was added. They are generated
# from the graph, so a change to the graph data changes them too.
V1_SETS = {
    'synthetic-validation': '05352ba9178648d9380e185c78a65339f39d8699ea357442f2c808c948c8d944',
    'noisy-validation': 'b78e59478c0a53f184bcda760170253de5ccf74d045c7db5b1278e79549a4b84',
    'synthetic-test': '33925f8531db0cda017f8def0f469cf277bf63378d2b45bfdcb40ce34ffac7f4',
    'noisy-test': '148718c5811df29f9b833680a9a3db1ebf42a7a08bee64ef53d53eaee3a1f17a',
    'hand-v1': '0ad60ebd2ee04c13d6f5dc3c944a64d5826ab091bcee6ffc28f8a1946a08532d',
}
CLEAN = {'commit': 'abc', 'clean': True, 'changes': []}
DIRTY = {'commit': 'abc', 'clean': False, 'changes': [' M backend/recommender/engine.py']}


class Stop(Exception):
    pass


@pytest.fixture(scope='module')
def kg():
    return get_graph()


@pytest.fixture
def tree(monkeypatch):
    """Set what the lock sees as the working-tree state."""
    def set_state(state):
        monkeypatch.setattr(evaluation, 'git_state', lambda: state)
    return set_state


@pytest.fixture
def results_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(results, 'RESULTS_DIR', tmp_path)
    return tmp_path


# Roles and hashes

def test_every_set_has_a_known_role():
    assert {s.role for s in PROFILE_SETS.values()} <= {'development', 'validation', 'test'}
    assert PROFILE_SETS['hand-v1'].role == 'development'
    assert {n for n, s in PROFILE_SETS.items() if s.role == 'test'} == {'synthetic-test', 'noisy-test'}


def test_the_protocol_names_the_selection_metric_and_guardrails():
    text = (BACKEND.parent / 'docs' / 'evaluation_protocol.md').read_text(encoding='utf-8')
    selection = text.split('### Model selection versus reporting', 1)[1].split('**Final reporting**', 1)[0]
    assert f'**Primary metric: {evaluation.SELECTION_METRIC}**' in selection
    assert all(f'**{g}**' in selection for g in evaluation.SELECTION_GUARDRAILS)


def test_v1_profile_sets_are_unchanged(kg, tree):
    tree(CLEAN)
    with open_test_sets():
        loaded = {name: s.load(kg) for name, s in PROFILE_SETS.items()}
    assert {name: d['sha256'] for name, d in describe_sets(loaded).items()} == V1_SETS


# The lock

@pytest.mark.parametrize('load', [
    make_test_profiles, noisy_test, held_out_names,
    lambda kg: noisy_profiles(kg, {}), lambda kg: generate_profiles(kg, TEST_SEED),
    *[s.load for s in PROFILE_SETS.values() if s.role == 'test'],
])
def test_test_sets_are_locked_by_default(kg, load):
    with pytest.raises(LockedSetError):
        load(kg)


def test_validation_and_development_sets_load_while_locked(kg):
    for s in PROFILE_SETS.values():
        if s.role != 'test':
            assert s.load(kg)


def test_a_dirty_tree_never_opens_the_test_sets(kg, tree):
    tree(DIRTY)
    with pytest.raises(LockedSetError, match='clean working tree'):
        with open_test_sets():
            pytest.fail('the body must not run')
    with pytest.raises(LockedSetError):
        make_test_profiles(kg)


def test_the_lock_closes_after_the_block_even_on_error(kg, tree):
    tree(CLEAN)
    with open_test_sets():
        assert make_test_profiles(kg)
    with pytest.raises(LockedSetError):
        make_test_profiles(kg)
    with pytest.raises(Stop):
        with open_test_sets():
            raise Stop
    with pytest.raises(LockedSetError):
        make_test_profiles(kg)


def test_evaluate_refuses_a_dirty_tree_before_loading_test_data(tree, results_dir, monkeypatch):
    tree(DIRTY)
    loaded = []
    monkeypatch.setattr(evaluate, 'test_profiles', lambda kg: loaded.append('test'))
    monkeypatch.setattr(evaluate, 'noisy_test', lambda kg: loaded.append('noisy'))
    with pytest.raises(LockedSetError):
        evaluate.main(['--run', 'dirty'])
    assert loaded == [] and list(results_dir.iterdir()) == []


def test_evaluate_opens_the_test_sets_only_while_loading_them(tree, results_dir, monkeypatch):
    tree(CLEAN)
    seen = []
    monkeypatch.setattr(evaluate, 'test_profiles', lambda kg: seen.append(evaluation._test_access) or [])
    monkeypatch.setattr(evaluate, 'noisy_test', lambda kg: seen.append(evaluation._test_access) or ({}, []))

    def systems(*args, **kwargs):
        seen.append(evaluation._test_access)
        raise Stop
    monkeypatch.setattr(evaluate, 'Systems', systems)
    with pytest.raises(Stop):
        evaluate.main(['--run', 'clean'])
    assert seen == [True, True, False]


@pytest.mark.parametrize('script, first_step', [
    (tuning, 'recommender.tuning.get_engine'), (explanation_quality, 'recommender.engine.get_engine'),
])
def test_access_does_not_leak_into_other_workflows(kg, tree, results_dir, monkeypatch, script, first_step):
    tree(CLEAN)

    def stop(*args, **kwargs):
        raise Stop
    monkeypatch.setattr(evaluate, 'Systems', stop)
    with pytest.raises(Stop):
        evaluate.main(['--run', 'final'])

    def check():
        assert not evaluation._test_access
        with pytest.raises(LockedSetError):
            make_test_profiles(kg)
        raise Stop
    monkeypatch.setattr(first_step, check)
    with pytest.raises(Stop):
        script.main(['--run', 'after'])


# Only the final evaluation may touch test sets (source inspection)

TEST_ONLY = {'open_test_sets', 'test_profiles', 'noisy_test', 'held_out_names', 'noisy_profiles', 'generate_profiles',
             'check_seed', 'TEST_SEED', 'HELD_OUT_SEED', 'NOISY_SEED', 'TEST_SEEDS', '_test_access', 'PROFILE_SETS'}
ALLOWED = {'evaluation.py': TEST_ONLY, 'evaluate.py': {'open_test_sets', 'test_profiles', 'noisy_test'}}


def identifiers(path):
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif isinstance(node, ast.alias):
            found.add(node.name.rsplit('.', 1)[-1])
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.add(node.value)
    return found


def app_sources():
    return [p for package in ('recommender', 'core', 'config', 'pipeline') for p in (BACKEND / package).rglob('*.py')]


def test_only_the_final_evaluation_names_test_sets():
    offenders = {p.name: sorted((identifiers(p) & TEST_ONLY) - ALLOWED.get(p.name, set())) for p in app_sources()}
    assert {name: names for name, names in offenders.items() if names} == {}


def test_evaluate_opens_the_test_sets_in_one_place():
    tree_ = ast.parse((BACKEND / 'recommender' / 'evaluate.py').read_text(encoding='utf-8'))
    opens = [n for n in ast.walk(tree_) if isinstance(n, ast.Call) and getattr(n.func, 'id', None) == 'open_test_sets']
    withs = [n for n in ast.walk(tree_) if isinstance(n, ast.With)]
    assert len(opens) == 1 and any(item.context_expr is opens[0] for w in withs for item in w.items)


@pytest.mark.parametrize('module, allowed', [
    ('tuning.py', {'describe_sets', 'noisy_validation', 'reciprocal_rank', 'validation_profiles'}),
    ('validate.py', {'describe_sets', 'hand_written_profiles', 'ndcg_at_k', 'noisy_validation', 'precision_at_k',
                     'recall_at_k', 'reciprocal_rank', 'validation_profiles'}),
    ('probes.py', {'validation_profiles'}),
])
def test_selection_code_imports_only_validation_sets(module, allowed):
    tree_ = ast.parse((BACKEND / 'recommender' / module).read_text(encoding='utf-8'))
    from_evaluation = {a.name for n in ast.walk(tree_) if isinstance(n, ast.ImportFrom)
                       and n.module == 'recommender.evaluation' for a in n.names}
    modules = {a.name for n in ast.walk(tree_) if isinstance(n, ast.Import) for a in n.names}
    assert from_evaluation == allowed
    assert not {m for m in modules if 'evaluation' in m}


# Working-tree state and manifests

def test_only_new_run_folders_are_ignored_by_the_clean_check():
    lines = ['?? data/results/v2-dev/evaluation.csv', '?? data/results/stray.csv',
             ' M data/results/evaluation.csv', ' M backend/recommender/engine.py', '?? notes.txt']
    assert results.uncommitted(lines) == lines[1:]


def test_outside_a_git_checkout_the_tree_counts_as_dirty(tmp_path, monkeypatch):
    monkeypatch.setattr(results, 'REPO_DIR', tmp_path)
    assert results.git_state()['clean'] is False


def test_manifest_records_the_run(results_dir):
    from recommender.engine import DEFAULT_PARAMS
    folder = results_dir / 'v2-check'
    started = results.run_started('recommender.evaluate', ['--run', 'v2-check'])
    sample = explanation_quality.HAND_WRITTEN_PROFILES
    sets = describe_sets({'hand-v1': [], 'noisy-test': ({}, [1, 2]), 'explanation-sample': sample},
                         roles={'explanation-sample': 'development'})
    assert sets['explanation-sample']['profiles'] == len(sample) and sets['noisy-test']['profiles'] == 2
    results.write_manifest(folder, started, sets, results.configuration(DEFAULT_PARAMS))
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['run'] == 'v2-check'
    assert manifest['command'] == 'python -m recommender.evaluate --run v2-check'
    assert {'started', 'finished'} <= manifest.keys()
    assert {'commit', 'clean', 'changes'} <= manifest['git'].keys()
    assert manifest['profile_sets']['hand-v1'] == {'role': 'development', 'profiles': 0, 'sha256': sets['hand-v1']['sha256']}
    config = manifest['configuration']
    assert len(config['id']) == 12 and config['params']['coverage_weight'] == DEFAULT_PARAMS.coverage_weight
    assert 'esco_onet_map.csv' in config['processed_data']
    with pytest.raises(FileExistsError):
        results.write_manifest(folder, started, sets, results.configuration(DEFAULT_PARAMS))
