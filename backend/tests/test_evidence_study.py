"""Evidence redesign study (release P2): rate arithmetic."""
import pytest

from recommender.evidence_study import rates


def test_rates_are_recall_and_false_insufficient():
    predicted = [True, True, False, True, False, False]
    labels = [True, True, True, False, False, False]          # three insufficient, three sufficient
    assert rates(predicted, labels) == pytest.approx((2 / 3, 1 / 3))
