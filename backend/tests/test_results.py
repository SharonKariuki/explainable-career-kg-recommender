import pandas as pd
import pytest

from recommender import evaluate, explanation_quality, results, tuning, validate


@pytest.mark.parametrize('filename, expected', results.V1_RESULTS.items())
def test_v1_results_are_unchanged(filename, expected):
    assert results.normalised_hash(results.RESULTS_DIR / filename) == expected


@pytest.fixture
def results_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(results, 'RESULTS_DIR', tmp_path)
    return tmp_path


def test_a_new_run_gets_its_own_folder(results_dir):
    assert results.run_dir('v2-dev_1') == results_dir / 'v2-dev_1'


@pytest.mark.parametrize('run', ['', 'v1', 'V1', '..', '../v2', 'a/b', 'a\\b', '/tmp/x', 'C:x', '.hidden',
                                 'evaluation.csv', '-flag', 'x' * 65])
def test_unsafe_or_reserved_run_names_are_refused(results_dir, run):
    with pytest.raises(ValueError):
        results.run_dir(run)


def test_an_existing_run_folder_is_refused(results_dir):
    (results_dir / 'v2-dev').mkdir()
    with pytest.raises(FileExistsError):
        results.run_dir('v2-dev')


def test_write_csv_never_replaces_a_file(results_dir):
    folder = results_dir / 'v2-dev'
    path = results.write_csv(pd.DataFrame({'a': [1]}), folder, 'out.csv')
    with pytest.raises(FileExistsError):
        results.write_csv(pd.DataFrame({'a': [2]}), folder, 'out.csv')
    assert pd.read_csv(path).a.tolist() == [1]


def _refuse_work(*args, **kwargs):
    raise AssertionError('the run name should be checked before any work starts')


@pytest.mark.parametrize('script', [evaluate, tuning, explanation_quality, validate])
@pytest.mark.parametrize('argv', [[], ['--run', 'v1'], ['--run', '../escape'], ['--run', 'used']])
def test_scripts_reject_a_bad_run_before_working(script, argv, results_dir, monkeypatch):
    (results_dir / 'used').mkdir()
    monkeypatch.setattr(evaluate, 'get_graph', _refuse_work)
    monkeypatch.setattr(tuning, 'get_engine', _refuse_work)
    monkeypatch.setattr(validate, 'get_graph', _refuse_work)
    monkeypatch.setattr('recommender.engine.get_engine', _refuse_work)
    with pytest.raises(SystemExit) as exit_info:
        script.main(argv)
    assert exit_info.value.code == 2
    assert sorted(p.name for p in results_dir.iterdir()) == ['used']
