"""δ calibration (Measured Matching C3, #159): flags recomputed at a margin, the clean-input rate, the choice."""
import pandas as pd

from recommender import calibration as cal


def r(node, margin, reasons=(), sim=0.9):
    return {'node_id': node, 'margin': margin, 'reasons': list(reasons), 'similarity': sim}


def test_close_runner_up_is_recomputed_at_each_delta():
    reading = r('A', 0.02, ['close_runner_up'])
    assert cal.reasons_at(reading, 0.0) == [] and cal.reasons_at(reading, 0.03) == ['close_runner_up']
    assert cal.reasons_at(r('A', 0.02, ['shared_name']), 0.03) == ['shared_name', 'close_runner_up']


def test_clean_rate_counts_correct_readings_and_skips_shared_name_only_flags():
    clean = [('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')]
    readings = {'a': r('A', 0.01), 'b': r('B', 0.5, ['shared_name']), 'c': r('C', 0.5), 'd': r('X', 0.001)}
    est = cal.clean_false_uncertainty(clean, readings, delta=0.02)
    assert est.n == 3 and round(est.p, 4) == round(1 / 3, 4)          # d is wrong, so not in the denominator
    assert cal.clean_false_uncertainty(clean, readings, 0.02, exclude_shared_only=False).p == 2 / 3


def test_choose_takes_the_largest_delta_meeting_both_targets():
    frame = pd.DataFrame({'delta': [0.0, 0.01, 0.02, 0.03], 'F_clean': [0.01, 0.03, 0.05, 0.07],
                          'F_unamb': [0.05, 0.10, 0.14, 0.12]})
    assert cal.choose(frame) == 0.02
    assert cal.choose(frame.assign(F_clean=0.9)) == 0.0
