"""Graded reporting through validate.py and evaluate.py, end to end on a small fixture.

Fake rankers return fixed rankings, so nothing loads a model or the real tasks-v1 files;
task_sets._load is replaced by the fixture, and test-split loading still passes the lock.
"""

import json
from types import SimpleNamespace

import pandas as pd
import pytest

from recommender import evaluate, evaluation, results, task_sets, validate
from recommender.evaluation import LabelledProfile, Profile
from recommender.probes import ProbeResult
from recommender.task_sets import GradedProfile

CAREERS = [f'career:{i:02d}' for i in range(24)]
OWN, TWIN, RELATED = CAREERS[0], CAREERS[1], CAREERS[2]
FIRST = {'own task': OWN, 'twin task': TWIN, 'related task': RELATED}
V1_RUN = results.RESULTS_DIR / 'v1-validation'


class FakeSystems:
    def __init__(self, kg, hidden_names=()):
        self.careers = CAREERS
        self.engine = SimpleNamespace(matcher=None)

    def rank(self, system, skills):
        first = FIRST.get(skills[0], OWN)
        return [first] + [c for c in CAREERS if c != first]


def graded(split):
    """Three profiles; only the first has a grade-2 label, and its twin career ranks first."""
    return [
        GradedProfile(f'{split}-1', OWN, ('twin task',), {OWN: 3, TWIN: 2, RELATED: 1}),
        GradedProfile(f'{split}-2', OWN, ('own task',), {OWN: 3, RELATED: 1}),
        GradedProfile(f'{split}-3', OWN, ('related task',), {OWN: 3, RELATED: 1}),
    ]


def synthetic(prefix):
    return [Profile(f'{prefix}-{size}', OWN, size, ('own task',) * size, ('s',) * size) for size in (2, 3)]


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(results, 'RESULTS_DIR', tmp_path)
    monkeypatch.setattr(evaluation, 'git_state', lambda: {'commit': 'x', 'clean': True, 'changes': []})
    monkeypatch.setattr(task_sets, '_load', graded)
    hand = [LabelledProfile('hand-0', ('own task',), frozenset({OWN}))]
    for module in (validate, evaluate):
        monkeypatch.setattr(module, 'get_graph', lambda: None)
        monkeypatch.setattr(module, 'Systems', FakeSystems)
        monkeypatch.setattr(module, 'hand_written_profiles', lambda kg: hand)
    monkeypatch.setattr(validate, 'validation_profiles', lambda kg: synthetic('val'))
    monkeypatch.setattr(validate, 'noisy_validation', lambda kg: ({}, synthetic('noisy-val')))
    monkeypatch.setattr(validate, 'run_probes', lambda engine: [ProbeResult('p', 'e', False, 'o', 'c')])
    monkeypatch.setattr(evaluate, 'test_profiles', lambda kg: synthetic('test'))
    monkeypatch.setattr(evaluate, 'noisy_test', lambda kg: ({}, synthetic('noisy-test')))
    monkeypatch.setattr(evaluate, 'matching_accuracy', lambda *a: dict.fromkeys(
        ('correct', 'correct_when_confident', 'correct_when_uncertain', 'uncertain_share'), 0.5))
    return tmp_path


def frozen(monkeypatch, value):
    monkeypatch.setattr(task_sets, 'FROZEN', dict.fromkeys(task_sets.FROZEN, 'f' * 64 if value else None))


def header(path):
    return list(pd.read_csv(path, nrows=0).columns)


@pytest.mark.parametrize('script, name, csv, v1_csv', [
    (validate, 'tasks-v1-validation', 'validation.csv', V1_RUN / 'validation.csv'),
    (evaluate, 'tasks-v1-test', 'evaluation.csv', results.RESULTS_DIR / 'evaluation.csv'),
])
def test_frozen_graded_sets_are_reported_beside_strict_precision(script, name, csv, v1_csv, fixture, monkeypatch, capsys):
    frozen(monkeypatch, True)
    script.main(['--run', 'graded'])
    run = fixture / 'graded'
    table = pd.read_csv(run / 'graded.csv')
    full = table.set_index('system').loc['full']
    assert set(table.system) == set(evaluate.SYSTEMS) and set(table.dataset) == {name}
    assert (full['profiles'], full['grade_2_profiles']) == (3, 1)
    # the tables are rounded to 4 decimals, like validation.csv and evaluation.csv
    assert full['p@1'] == pytest.approx(2 / 3, abs=1e-4) and full['p@1_grade3'] == pytest.approx(1 / 3, abs=1e-4)
    assert full['p@1'] - full['p@1_grade3'] <= full['p@1_gap_bound'] + 1e-4
    assert '3 profiles, 1 with a grade-2 label' in full['disclosure'] and '1/3 = 0.333' in full['disclosure']
    assert 'No claim about near-identical tasks' in full['disclosure']
    printed = capsys.readouterr().out
    assert full['disclosure'] in printed and 'p@1_grade3' in printed
    assert header(run / csv) == header(v1_csv)                 # the existing table keeps its format
    manifest = json.loads((run / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['profile_sets'][name]['role'] == ('test' if script is evaluate else 'validation')


@pytest.mark.parametrize('script, csv, v1_csv', [
    (validate, 'validation.csv', V1_RUN / 'validation.csv'),
    (evaluate, 'evaluation.csv', results.RESULTS_DIR / 'evaluation.csv'),
])
def test_unfrozen_graded_sets_are_skipped_and_outputs_unchanged(script, csv, v1_csv, fixture, monkeypatch, capsys):
    frozen(monkeypatch, False)
    script.main(['--run', 'plain'])
    run = fixture / 'plain'
    assert not (run / 'graded.csv').exists()
    assert 'tasks-v1 is not frozen' in capsys.readouterr().out
    assert header(run / csv) == header(v1_csv)
    manifest = json.loads((run / 'manifest.json').read_text(encoding='utf-8'))
    assert not any(name.startswith('tasks-v1') for name in manifest['profile_sets'])


def test_the_test_split_still_needs_the_lock_when_frozen(monkeypatch):
    frozen(monkeypatch, True)
    monkeypatch.setattr(task_sets, '_load', graded)
    with pytest.raises(evaluation.LockedSetError):
        task_sets.task_test_profiles()
    assert task_sets.task_validation_profiles()[0].profile_id == 'validation-1'
