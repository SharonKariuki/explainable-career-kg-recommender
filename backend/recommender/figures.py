"""Report figures drawn from committed result files.

    python -m recommender.figures

Reads data/results/tuning.csv (written by `python -m recommender.tuning`) and
writes docs/figures/tuning_progress.png: validation MRR across the coverage
weights tested, with depth, low-confidence threshold and low-confidence weight
held at the chosen defaults. For each coverage weight the best remaining
split between similarity and proximity is shown, which is how the defaults
were picked. Needs matplotlib (pip install matplotlib).
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from recommender.engine import DEFAULT_PARAMS

ROOT = Path(__file__).resolve().parents[2]
TUNING = ROOT / 'data' / 'results' / 'tuning.csv'
OUT = ROOT / 'docs' / 'figures'


def tuning_curve(table, params=DEFAULT_PARAMS):
    fixed = table[(table.max_depth == params.max_depth)
                  & (table.low_confidence_threshold.round(2) == round(params.low_confidence_threshold, 2))
                  & (table.low_confidence_weight.round(2) == round(params.low_confidence_weight, 2))]
    best = fixed.loc[fixed.groupby('coverage_weight').mrr.idxmax()]
    return best.sort_values('coverage_weight')


def tuning_progress(table, path):
    curve = tuning_curve(table)
    x = curve.coverage_weight
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=200)
    left.plot(x, curve.mrr_clean, label='Clean Wording MRR')
    left.plot(x, curve.mrr_noisy, label='Unseen Wording MRR')
    left.set_title('Tuning - AjiraGuide - Validation MRR by Wording')
    for size in (2, 3, 5):
        right.plot(x, curve[f'mrr_size_{size}'], label=f'{size} Skills')
    right.set_title('Tuning - AjiraGuide - Validation MRR by Profile Size')
    low, high = right.get_ylim()
    right.set_ylim(low, high + (high - low) * 0.25)  # room for the legend
    for ax, where in ((left, 'lower right'), (right, 'upper left')):
        ax.axvline(DEFAULT_PARAMS.coverage_weight, color='grey', linestyle='--', linewidth=1)
        ax.set_xlabel('Coverage Weight')
        ax.set_ylabel('MRR')
        ax.grid(alpha=0.3)
        ax.legend(loc=where)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return curve


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    curve = tuning_progress(pd.read_csv(TUNING), OUT / 'tuning_progress.png')
    chosen = curve[curve.coverage_weight.round(2) == round(DEFAULT_PARAMS.coverage_weight, 2)].iloc[0]
    print(f"Wrote {OUT / 'tuning_progress.png'}")
    print(f"Chosen coverage weight {chosen.coverage_weight:.1f}: validation MRR {chosen.mrr:.3f} "
          f"(clean {chosen.mrr_clean:.3f}, unseen {chosen.mrr_noisy:.3f})")


if __name__ == '__main__':
    main()
