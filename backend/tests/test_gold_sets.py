"""The frozen gold sets (Measured Matching C3, #159): they rebuild byte-for-byte from the committed
annotations, they load, and their test splits stay locked."""
import pytest

from pipeline import gold_sets
from recommender import mapping_eval as me, student_eval as se
from recommender.evaluation import LockedSetError
from recommender.results import normalised_hash


def test_the_frozen_sets_rebuild_from_the_committed_annotations(tmp_path, monkeypatch):
    monkeypatch.setattr(gold_sets, 'GOLD', gold_sets.DATA_DIR / 'eval_sets' / 'gold_v1')
    gold_sets.build(tmp_path)
    assert normalised_hash(tmp_path / 'mapping_v1.json') == me.FROZEN['mapping_v1.json']
    assert normalised_hash(tmp_path / 'students_v1.json') == se.FROZEN['students_v1.json']


def test_the_frozen_sets_load_and_their_test_splits_are_locked():
    from recommender.graph import get_graph
    kg = get_graph()
    assert me.load_items('validation', node_ids=set(kg.skills()))
    assert se.load_profiles('validation', career_codes={c.split(':')[1] for c in kg.careers()})
    with pytest.raises(LockedSetError):
        me.load_items('test')
    with pytest.raises(LockedSetError):
        se.load_profiles('test')
