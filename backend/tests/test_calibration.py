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


def test_tau_recomputes_below_threshold_and_keeps_other_reasons():
    reading = {'node_id': 'A', 'margin': 0.5, 'reasons': ['below_threshold', 'shared_name'], 'similarity': 0.57}
    assert cal.reasons_at(reading, 0.0) == ['below_threshold', 'shared_name']          # τ not given: as read
    assert cal.reasons_at(reading, 0.0, tau=0.55) == ['shared_name']                  # 0.57 is not below 0.55
    assert cal.reasons_at(reading, 0.0, tau=0.60) == ['below_threshold', 'shared_name']


def test_choose_joint_minimises_confidently_incorrect_within_both_targets():
    frame = pd.DataFrame({'tau': [0.6, 0.55, 0.5, 0.5], 'delta': [0.0, 0.01, 0.02, 0.0],
                          'F_clean': [0.0, 0.01, 0.02, 0.09], 'F_unamb': [0.16, 0.12, 0.08, 0.05],
                          'M7 primary': [0.10, 0.11, 0.12, 0.05]})
    best = cal.choose_joint(frame)
    assert (best.tau, best.delta) == (0.55, 0.01)        # the 0.05 row breaks F_clean; the first breaks F_unamb
    assert cal.choose_joint(frame.assign(F_unamb=0.9)) is None


def test_the_flag_threshold_defaults_to_the_ranking_threshold():
    from recommender import matching
    assert matching.UNCERTAIN_SIMILARITY == matching.LOW_CONFIDENCE_THRESHOLD
