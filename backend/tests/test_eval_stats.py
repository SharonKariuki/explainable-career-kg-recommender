import math

import pytest

from recommender.eval_stats import (
    ProportionEstimate, anova_icc, cluster_bootstrap, design_effect, kish_wilson, mean_of_cluster_means,
    outcome, reliability, wilson_interval,
)


def test_wilson_matches_the_closed_form():
    low, high = wilson_interval(0.8, 60)
    assert (round(low, 3), round(high, 3)) == (0.682, 0.882)
    assert wilson_interval(0.0, 50)[0] == 0.0 and wilson_interval(0.0, 50)[1] > 0   # never zero width at p = 0
    assert wilson_interval(1.0, 50)[1] == 1.0 and wilson_interval(1.0, 50)[0] < 1


def test_icc_is_zero_without_clustering_and_high_when_clusters_agree():
    independent = [[1], [0], [1], [0], [1], [0]]                       # one unit per cluster
    assert anova_icc(independent) == 0.0
    agreeing = [[1, 1], [0, 0], [1, 1], [0, 0], [1, 1], [0, 0]]        # both units always agree
    assert anova_icc(agreeing) == pytest.approx(1.0)
    mixed = [[1, 0], [0, 1], [1, 0], [0, 1]]                           # within-cluster disagreement
    assert anova_icc(mixed) == 0.0                                      # negative estimate truncated to 0


def test_design_effect_uses_the_size_weighted_mean_cluster_size():
    assert design_effect([1, 1, 1], 0.9) == 1.0
    assert design_effect([2, 2, 2], 0.5) == pytest.approx(1.5)
    assert design_effect([1, 3], 0.5) == pytest.approx(1 + ((1 + 9) / 4 - 1) * 0.5)


def test_kish_wilson_reduces_to_wilson_for_singleton_clusters():
    clusters = {i: [i % 5 != 0] for i in range(100)}
    est = kish_wilson(clusters)
    assert est.design_effect == 1.0 and est.n_eff == 100
    assert (est.low, est.high) == pytest.approx(wilson_interval(0.8, 100))


def test_kish_wilson_widens_the_interval_for_correlated_clusters():
    paired = {i: [i % 5 != 0] * 2 for i in range(100)}     # two identical units per cluster
    est = kish_wilson(paired)
    assert est.n == 200 and est.design_effect == pytest.approx(2.0) and est.n_eff == pytest.approx(100)
    assert (est.low, est.high) == pytest.approx(wilson_interval(0.8, 100))   # duplicates add no information


def estimate(low, high, n_eff=100, clusters=100):
    return ProportionEstimate(n_eff, clusters, 0, (low + high) / 2, 0, 1, n_eff, low, high, reliability(n_eff))


@pytest.mark.parametrize('low, high, target, direction, expected', [
    (0.74, 0.92, 0.70, '>=', 'Pass'),
    (0.68, 0.88, 0.70, '>=', 'Inconclusive'),   # point estimate passes, interval crosses
    (0.52, 0.76, 0.70, '>=', 'Inconclusive'),   # point estimate misses, interval crosses
    (0.38, 0.62, 0.70, '>=', 'Fail'),
    (0.05, 0.13, 0.15, '<=', 'Pass'),
    (0.06, 0.16, 0.15, '<=', 'Inconclusive'),
    (0.12, 0.25, 0.15, '<=', 'Inconclusive'),
    (0.23, 0.38, 0.15, '<=', 'Fail'),
])
def test_outcomes_follow_the_whole_interval(low, high, target, direction, expected):
    assert outcome(estimate(low, high), target, direction) == expected


def test_small_samples_and_few_clusters_are_not_assessable():
    assert outcome(estimate(0.9, 0.99, n_eff=40), 0.5, '>=') == 'Not assessable'
    assert outcome(estimate(0.9, 0.99, n_eff=100, clusters=20), 0.5, '>=') == 'Not assessable'
    with pytest.raises(ValueError):
        outcome(estimate(0.1, 0.2), 0.5, '>')


def test_reliability_bands():
    assert [reliability(n) for n in (60, 59.9, 30, 29.9)] == ['reliable', 'exploratory', 'exploratory', 'counts only']


def test_cluster_bootstrap_is_seeded_and_brackets_the_point():
    values = {f'p{i}': [i % 3 / 2, (i + 1) % 3 / 2] for i in range(40)}
    first = cluster_bootstrap(values, mean_of_cluster_means, samples=2000)
    assert first == cluster_bootstrap(values, mean_of_cluster_means, samples=2000)
    point, low, high = first
    assert low <= point <= high and high - low > 0
    assert math.isnan(cluster_bootstrap({}, mean_of_cluster_means)[0])
