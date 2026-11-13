"""Interval estimates and acceptance outcomes for the Measured Matching evaluation (#157).

The plan (Measured Matching revision 6, C3) fixes one method per kind of quantity:

- Gated quantities are pooled proportions of binary outcomes. Their 95% interval is a
  Wilson interval on the Kish effective sample size: units keep their own outcome (no
  averaging within a cluster), and clustering enters once, through the design effect.
- Report-only quantities that are not proportions (MRR, nDCG, per-profile means) use a
  cluster bootstrap: whole clusters are resampled, and no design effect is applied.

Each interval is then read against a target as Pass, Fail, Inconclusive or Not assessable.
"""

import math
import random
from dataclasses import dataclass

Z95 = 1.959963984540054
RELIABLE_N = 60       # effective n at or above this: reliable
EXPLORATORY_N = 30    # effective n from this up to RELIABLE_N: exploratory; below: counts only
MIN_CLUSTERS = 30     # fewer clusters than this: the ICC is unstable, so a gate is not assessable
BOOTSTRAP_SAMPLES = 10_000


def wilson_interval(p, n, z=Z95):
    """Wilson score interval for a proportion p observed on n (possibly fractional) units."""
    if n <= 0:
        return 0.0, 1.0
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    # At p = 0 (or 1) the lower (or upper) bound is exactly 0 (or 1); floating-point
    # cancellation would otherwise leave a value like 7e-18.
    low = 0.0 if p <= 0 else max(0.0, centre - half)
    high = 1.0 if p >= 1 else min(1.0, centre + half)
    return low, high


def anova_icc(clusters):
    """One-way ANOVA estimate of the intra-cluster correlation of binary outcomes, in [0, 1].

    `clusters` is a list of lists of 0/1 outcomes. Returns 0 when it cannot be estimated
    (fewer than two clusters, or no within-cluster variation to compare against).
    """
    clusters = [list(c) for c in clusters if len(c)]
    k = len(clusters)
    n = sum(len(c) for c in clusters)
    if k < 2 or n <= k:
        return 0.0
    grand = sum(sum(c) for c in clusters) / n
    ssb = sum(len(c) * (sum(c) / len(c) - grand) ** 2 for c in clusters)
    ssw = sum(sum((x - sum(c) / len(c)) ** 2 for x in c) for c in clusters)
    msb = ssb / (k - 1)
    msw = ssw / (n - k)
    m0 = (n - sum(len(c) ** 2 for c in clusters) / n) / (k - 1)
    denominator = msb + (m0 - 1) * msw
    if denominator <= 0:
        return 0.0
    return min(1.0, max(0.0, (msb - msw) / denominator))


def design_effect(cluster_sizes, icc):
    """Kish design effect 1 + (m - 1) * icc, with m the size-weighted mean cluster size."""
    total = sum(cluster_sizes)
    if total == 0:
        return 1.0
    m = sum(s * s for s in cluster_sizes) / total
    return 1 + (m - 1) * icc


def reliability(n_eff):
    if n_eff >= RELIABLE_N:
        return 'reliable'
    if n_eff >= EXPLORATORY_N:
        return 'exploratory'
    return 'counts only'


@dataclass(frozen=True)
class ProportionEstimate:
    n: int
    clusters: int
    positives: int
    p: float
    icc: float
    design_effect: float
    n_eff: float
    low: float
    high: float
    reliability: str


def kish_wilson(outcomes_by_cluster):
    """Pooled proportion with a Wilson interval on the Kish effective sample size.

    `outcomes_by_cluster` maps a cluster id to that cluster's binary outcomes. A cluster of
    one unit contributes design effect 1, so unclustered data gives the plain Wilson interval.
    """
    clusters = [[int(bool(x)) for x in values] for values in outcomes_by_cluster.values() if len(values)]
    n = sum(len(c) for c in clusters)
    positives = sum(sum(c) for c in clusters)
    if n == 0:
        return ProportionEstimate(0, 0, 0, float('nan'), 0.0, 1.0, 0.0, 0.0, 1.0, 'counts only')
    p = positives / n
    icc = anova_icc(clusters)
    de = design_effect([len(c) for c in clusters], icc)
    n_eff = n / de
    low, high = wilson_interval(p, n_eff)
    return ProportionEstimate(n, len(clusters), positives, p, icc, de, n_eff, low, high, reliability(n_eff))


def outcome(estimate, target, direction):
    """Pass, Fail, Inconclusive or Not assessable for a gated target.

    direction '>=' means the quantity should be at least `target`; '<=' at most `target`.
    Pass and Fail need the whole interval on one side of the target; an interval that
    crosses it is Inconclusive whatever the point estimate. Too few effective units or
    clusters make the result Not assessable.
    """
    if direction not in ('>=', '<='):
        raise ValueError(f'direction must be ">=" or "<=", not {direction!r}')
    if estimate.n_eff < RELIABLE_N or estimate.clusters < MIN_CLUSTERS:
        return 'Not assessable'
    low, high = estimate.low, estimate.high
    if direction == '>=':
        return 'Pass' if low >= target else ('Fail' if high < target else 'Inconclusive')
    return 'Pass' if high <= target else ('Fail' if low > target else 'Inconclusive')


def cluster_bootstrap(values_by_cluster, statistic, samples=BOOTSTRAP_SAMPLES, seed=7, level=0.95):
    """Percentile interval of `statistic` over clusters resampled with replacement.

    `values_by_cluster` maps a cluster id to that cluster's unit values; `statistic` takes the
    list of resampled clusters (each a list of values). No design effect is applied: resampling
    whole clusters already carries the clustering.
    """
    clusters = [list(v) for v in values_by_cluster.values() if len(v)]
    if not clusters:
        return float('nan'), float('nan'), float('nan')
    rng = random.Random(seed)
    point = statistic(clusters)
    replicates = sorted(statistic([clusters[rng.randrange(len(clusters))] for _ in clusters]) for _ in range(samples))
    tail = (1 - level) / 2
    low = replicates[int(math.floor(tail * (samples - 1)))]
    high = replicates[int(math.ceil((1 - tail) * (samples - 1)))]
    return point, low, high


def mean_of_cluster_means(clusters):
    """Average each cluster first, then average the clusters: one value per profile."""
    return sum(sum(c) / len(c) for c in clusters) / len(clusters)
