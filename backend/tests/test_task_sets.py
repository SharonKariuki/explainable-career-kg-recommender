import json

import pandas as pd
import pytest

from recommender import evaluation, task_sets as ts
from recommender.evaluation import LockedSetError


def data_available(raw_files=None):
    """The raw O*NET files (gitignored, from pipeline.download) and the built set."""
    return all(p.exists() for p in (raw_files or ts.RAW_FILES)) and ts.TASKS_FILE.exists()


needs_data = pytest.mark.skipif(not data_available(), reason='raw O*NET files or tasks-v1 not present')


@pytest.fixture(scope='module')
def table():
    return ts.read_table()


@pytest.fixture(scope='module')
def pairs():
    return ts.read_pairs()


def ids(row):
    return json.loads(row.task_ids)


# Without data: the skip itself, the flag, the lock

def test_a_fresh_clone_without_raw_files_skips(tmp_path):
    assert not data_available({tmp_path / 'Task Statements.txt': ''})


def test_the_flag_tells_tool_names_from_ordinary_words():
    names = pd.DataFrame({'label': ['Access', 'Python', 'data warehouse', 'design', 'Data'],
                          'skill_type': ['tool', 'tool', 'knowledge', 'skill', 'tool']})
    flag = ts.skill_name_flag(names)
    assert flag('Write scripts in Python.') and flag('Maintain the Access database.')
    assert flag('Design a DATA WAREHOUSE.')                   # multi-word names ignore case
    assert not flag('Control access to the data.')            # the verb, not the tool
    assert not flag('Design web pages.')                      # single generic words never count
    assert not flag('Analyse data.')                          # 'Data' as a 4-letter tool needs its exact case


def test_the_test_split_is_locked_and_nothing_loads_before_freezing(monkeypatch):
    with pytest.raises(LockedSetError):
        ts.task_test_profiles()
    if None in ts.FROZEN.values():
        with pytest.raises(RuntimeError, match='not frozen'):
            ts.task_validation_profiles()
    monkeypatch.setattr(evaluation, 'git_state', lambda: {'commit': 'x', 'clean': True, 'changes': []})
    with evaluation.open_test_sets():
        if None in ts.FROZEN.values():
            with pytest.raises(RuntimeError, match='not frozen'):
                ts.task_test_profiles()


@pytest.mark.skipif(None in ts.FROZEN.values(), reason='tasks-v1 is not frozen')
def test_loaded_profiles_carry_the_overlap_covariates():
    stored = ts.read_table().set_index('profile_id')
    for p in ts.task_validation_profiles():
        assert p.strata == {'description cosine third': stored.at[p.profile_id, 'cosine_third'],
                            'names a graph skill': stored.at[p.profile_id, 'names_a_graph_skill']}
        assert p.strata['description cosine third'] in {0, 1, 2}  # 0 is the lowest third
        assert isinstance(p.strata['names a graph skill'], bool)


# With the raw files and the built set

@needs_data
def test_raw_files_are_checked(tmp_path, monkeypatch):
    ts.check_raw()
    original = next(iter(ts.RAW_FILES))
    copy = tmp_path / original.name
    copy.write_bytes(original.read_bytes() + b' ')
    monkeypatch.setattr(ts, 'RAW_FILES', {copy: ts.RAW_FILES[original]})
    with pytest.raises(RuntimeError, match='differs'):
        ts.check_raw()


@needs_data
def test_ten_profiles_per_career_split_evenly(table):
    counts = table.groupby(['onet_soc_code', 'split']).size()
    assert table.onet_soc_code.nunique() == 24 and set(counts) == {ts.PER_SPLIT}


@needs_data
def test_every_text_is_the_onet_text_and_appears_once(table):
    raw = ts.core_tasks().set_index('task_id')
    for r in table.itertuples():
        assert all(ts.normalise(raw.task[t]) == ts.normalise(r.task) for t in ids(r))
        assert json.loads(r.source_codes) == sorted({raw.onet_soc_code[t] for t in ids(r)})
        assert r.task_id == min(ids(r), key=int) and r.onet_soc_code == raw.onet_soc_code[r.task_id]
    assert not table.task.map(ts.normalise).duplicated().any()
    assert (table.task_ids.map(json.loads).map(len) > 1).any()  # merged texts exist


@needs_data
def test_near_identical_tasks_never_cross_splits(table, pairs):
    split = {t: r.split for r in table.itertuples() for t in ids(r)}
    assert all(split[a] == split[b] for a, b in zip(pairs.task_id_a, pairs.task_id_b) if a in split and b in split)


@needs_data
def test_grades_follow_the_labelling_rules(table, pairs):
    related = ts.related_occupations()
    accepted = pairs[pairs.decision == 'accept']
    for r in table.itertuples():
        grades, sources, tasks = json.loads(r.grades), set(json.loads(r.source_codes)), set(ids(r))
        twins = ({b for a, b in zip(accepted.task_id_a, accepted.code_b) if a in tasks}
                 | {a for b, a in zip(accepted.task_id_b, accepted.code_a) if b in tasks})
        assert {c for c, g in grades.items() if g == 3} == sources
        assert {c for c, g in grades.items() if g == 2} == twins - sources
        assert {c for c, g in grades.items() if g == 1} <= {b for (a, b), tier in related.items()
                                                            if a in sources and tier == 'Primary-Short'}


@needs_data
def test_rejected_pairs_give_no_grade_two(table, pairs):
    assert list(pairs.index[pairs.decision == 'reject']) == [1, 4, 5, 6]
    profile = {t: r for r in table.itertuples() for t in ids(r)}
    for p in pairs[pairs.decision == 'reject'].itertuples():
        for task, other in ((p.task_id_a, p.code_b), (p.task_id_b, p.code_a)):
            if task in profile:
                assert json.loads(profile[task].grades).get(other) != 2


@needs_data
def test_the_split_balances_wording_and_leakage_per_career(table):
    flagged = table.groupby(['onet_soc_code', 'split']).names_a_graph_skill.sum().unstack()
    assert ((flagged.validation - flagged.test).abs() <= 1).all()
    assert flagged.validation.sum() == flagged.test.sum()
    thirds = table.groupby(['onet_soc_code', 'cosine_third', 'split']).size().unstack(fill_value=0)
    assert ((thirds.validation - thirds.test).abs() <= 1).all()


@needs_data
def test_every_nominated_pair_is_decided_with_a_reason(pairs):
    assert set(pairs.decision) <= ts.DECISIONS and pairs.reason.notna().all()
    with pytest.raises(ValueError, match='accept or reject'):
        ts.build(pairs.assign(decision='pending'))


# Verification tiers: the stored table is authoritative

def first_in(table, career, split):
    return table.index[(table.onet_soc_code == career) & (table.split == split)][0]


@needs_data
def test_tier1_integrity_checks_raw_and_frozen_files(monkeypatch):
    ts.check_integrity()
    monkeypatch.setattr(ts, 'FROZEN', {'tasks_v1.csv': None, 'twin_review.csv': '0' * 64})
    with pytest.raises(ts.VerificationError, match='twin_review.csv'):
        ts.check_integrity()


@needs_data
def test_tier2_the_stored_table_regenerates_exactly(table, pairs):
    ts.check_regeneration(table, pairs)


@needs_data
@pytest.mark.parametrize('change', ['task id', 'label', 'split', 'flag'])
def test_tier2_fails_on_a_meaningful_change(table, pairs, change):
    edited = table.copy()
    row = first_in(edited, edited.onet_soc_code.iloc[0], 'validation')
    if change == 'task id':
        edited.loc[row, 'task_id'] = '999999'
    elif change == 'label':
        grades = json.loads(edited.loc[row, 'grades'])
        grades[edited.loc[row, 'onet_soc_code']] = 2            # the listing occupation demoted from 3
        edited.loc[row, 'grades'] = json.dumps(grades)
    elif change == 'split':  # swap one validation and one test task of a career: still 5 and 5
        other = first_in(edited, edited.loc[row, 'onet_soc_code'], 'test')
        edited.loc[[row, other], 'split'] = ['test', 'validation']
    else:
        edited.loc[row, 'names_a_graph_skill'] = not edited.loc[row, 'names_a_graph_skill']
    with pytest.raises(ts.VerificationError):
        ts.check_regeneration(edited, pairs)


@needs_data
def test_tier2_fails_when_thirds_and_split_are_changed_together(table, pairs):
    """A consistent edit: two stored thirds changed and the split re-derived from them."""
    edited = table.copy()
    rows = edited.index[edited.onet_soc_code == edited.onet_soc_code.iloc[0]][:2]
    edited.loc[rows, 'cosine_third'] = (edited.loc[rows, 'cosine_third'] + 1) % 3
    covariates = edited.set_index('task_id')
    split = ts.assign_splits(ts.select(ts.candidates(ts.core_tasks())), pairs,
                             covariates.names_a_graph_skill.to_dict(), covariates.cosine_third.to_dict())
    edited['split'] = edited.task_id.map(split)
    with pytest.raises(ts.VerificationError, match='third of its stored cosine'):
        ts.check_regeneration(edited, pairs)


@needs_data
def test_repeated_or_foreign_task_ids_fail_cleanly(table, pairs):
    repeated = pd.concat([table, table.iloc[[0]]], ignore_index=True)
    with pytest.raises(ts.VerificationError, match='repeated'):
        ts.check_regeneration(repeated, pairs)
    foreign = table.copy()
    foreign.loc[0, 'task_id'] = '999999'
    with pytest.raises(ts.VerificationError, match='differ'):
        ts.check_covariate_drift(foreign)


@needs_data
def test_one_row_definition_serves_build_and_verification(table, pairs):
    candidate = ts.select(ts.candidates(ts.core_tasks())).iloc[0]
    row = ts.task_row(candidate, ({}, [], []), 'validation', 0.5, 1, False)
    assert list(row) == list(table.columns)
    with pytest.raises(ts.VerificationError, match='columns differ'):
        ts.check_regeneration(table.drop(columns='supplemental'), pairs)
    with pytest.raises(ts.VerificationError, match='columns differ'):
        ts.check_regeneration(table.assign(extra=1), pairs)


@needs_data
def test_loaders_and_tier1_share_the_frozen_hash_check(monkeypatch):
    real = {name: ts.normalised_hash(ts.EVAL_DIR / name) for name in ts.FROZEN}
    monkeypatch.setattr(ts, 'FROZEN', real)
    assert len(ts.task_validation_profiles()) == 120
    ts.check_integrity()
    monkeypatch.setattr(ts, 'FROZEN', {**real, 'tasks_v1.csv': '0' * 64})
    for check in (ts.task_validation_profiles, ts.check_integrity):
        with pytest.raises(ts.VerificationError, match='no longer matches'):
            check()


@needs_data
def test_after_a_data_change_the_stored_covariates_stand(table, pairs, monkeypatch):
    assert ts.covariate_data_unchanged()
    monkeypatch.setattr(ts, 'COVARIATE_DATA', {**ts.COVARIATE_DATA, 'onet_tools.csv': 'another graph'})
    assert not ts.covariate_data_unchanged() and ts.covariate_data_unchanged(['occupations.csv'])
    ts.check_regeneration(table, pairs)                      # stored flag stands
    monkeypatch.setattr(ts, 'COVARIATE_DATA', {**ts.COVARIATE_DATA, 'occupations.csv': 'new descriptions'})
    drifted = table.copy()
    drifted['own_description_cosine'] += 0.05
    drifted['cosine_third'] = drifted.task_id.map(ts.cosine_thirds(dict(zip(drifted.task_id, drifted.own_description_cosine))))
    warnings = ts.check_covariate_drift(drifted)             # stored cosines stand: a warning, no failure
    assert len(warnings) == 1 and 'drift not checked' in warnings[0]


@needs_data
def test_tier3_cosines_are_within_tolerance_and_thirds_only_warn(table):
    assert ts.check_covariate_drift(table) == []
    shifted = table.copy()
    shifted['own_description_cosine'] += 0.01                # harmless rounding-sized difference
    ts.check_covariate_drift(shifted)
    relabelled = table.copy()
    row = relabelled.index[0]
    relabelled.loc[row, 'cosine_third'] = (relabelled.loc[row, 'cosine_third'] + 1) % 3
    warnings = ts.check_covariate_drift(relabelled)
    assert len(warnings) == 1 and relabelled.loc[row, 'task_id'] in warnings[0] and 'split unchanged' in warnings[0]
    drifted = table.copy()
    drifted.loc[row, 'own_description_cosine'] += 0.02
    with pytest.raises(ts.VerificationError, match='drift'):
        ts.check_covariate_drift(drifted)
