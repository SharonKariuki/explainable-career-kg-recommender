import pytest

from recommender.engine import EngineParams, get_engine
from recommender.tuning import component_table, low_confidence_grid, rank_of_target, weight_grid


def test_weight_grid_covers_the_simplex():
    grid = list(weight_grid())
    assert len(grid) == 66
    assert all(sum(w) == pytest.approx(1) and min(w) >= 0 for w in grid)


def test_low_confidence_grid_skips_redundant_thresholds():
    grid = list(low_confidence_grid())
    assert len(grid) == len(set(grid)) == 7
    assert [t for t, w in grid if w == 1.0] == [0.6]


@pytest.mark.parametrize('skills, target', [
    (['sql', 'data warehouse'], 'career:15-1243.01'),
    (['Solidity'], 'career:15-1212.00'),
])
@pytest.mark.parametrize('depth', [1, 3])
def test_fast_ranking_agrees_with_the_engine(skills, target, depth):
    engine = get_engine()
    prepared = engine.prepare(skills)
    weights = (0.3, 0.3, 0.4)
    table = component_table(engine, prepared, target, threshold=0.6, weight=0.5)
    params = EngineParams(max_depth=depth, low_confidence_threshold=0.6, low_confidence_weight=0.5,
                          coverage_weight=weights[0], similarity_weight=weights[1], proximity_weight=weights[2])
    ranked = [r.career_id for r in engine.score(prepared, params)[1]]
    expected = ranked.index(target) + 1 if target in ranked else None
    assert rank_of_target(table, weights, depth) == expected
