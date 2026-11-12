import pandas as pd
import pytest

from recommender.rating_kit import QUESTIONS, sheet_markdown, sheet_rows, summarise


def test_the_sheet_has_ten_explanations_from_the_current_engine():
    rows = sheet_rows()
    assert list(rows.item) == list(range(1, 11))
    assert set(rows['rank']) == {1, 2} and rows.explanation.str.len().min() > 50
    text = sheet_markdown(rows)
    assert text.count('## Item') == 10 and all(question in text for question in QUESTIONS.values())


def ratings(values):
    return pd.DataFrame([{'rater': r, 'item': i, **dict(zip(QUESTIONS, v))} for r, i, v in values])


def test_summary_reports_mean_spread_and_agreement():
    table = summarise(ratings([('a', 1, (5, 4, 4, 3)), ('b', 1, (3, 4, 2, 3)), ('a', 2, (4, 4, 4, 5))]))
    h1 = table[(table.item == 'all') & (table.question == 'H1')].iloc[0]
    assert h1.raters == 2 and h1['mean'] == pytest.approx(4.0) and h1.agree_share == pytest.approx(2 / 3, abs=1e-3)
    assert set(table.item) == {'all', 1, 2}


def test_summary_rejects_bad_files():
    with pytest.raises(ValueError, match='missing columns'):
        summarise(pd.DataFrame({'rater': ['a'], 'item': [1]}))
    with pytest.raises(ValueError, match='from 1 to 5'):
        summarise(ratings([('a', 1, (6, 4, 4, 4))]))
