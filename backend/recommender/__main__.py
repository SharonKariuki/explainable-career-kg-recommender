"""Rank careers for a list of skills, with explanations and skills to build.

Usage (from backend/):
    python -m recommender Python "machine learning" statistics
    python -m recommender Python "machine learning" statistics --baseline
"""

import argparse
import textwrap

from recommender.baseline import get_baseline
from recommender.engine import get_engine
from recommender.explanation import ExplanationGenerator
from recommender.skills_gap import get_skills_gap


def main():
    parser = argparse.ArgumentParser(description='Rank careers for a list of skills.')
    parser.add_argument('skills', nargs='+', help='e.g. Python "machine learning" statistics')
    parser.add_argument('--top', type=int, default=3, help='number of careers to show')
    parser.add_argument('--baseline', action='store_true', help='rank with the keyword baseline instead')
    args = parser.parse_args()

    if args.baseline:
        _, ranked = get_baseline().rank(args.skills, top_k=args.top)
        for i, r in enumerate(ranked, 1):
            print(f'{i}. {r.title}  score {r.score:.2f}')
        return

    matches, ranked = get_engine().rank(args.skills, top_k=args.top)
    for m in matches:
        note = '  (uncertain)' if m.low_confidence else ''
        print(f'{m.query!r} -> {m.node_label} [{m.similarity:.2f}]{note}')

    generator, gaps = ExplanationGenerator(), get_skills_gap()
    for i, r in enumerate(ranked, 1):
        print(f'\n{i}. {r.title}')
        print(textwrap.fill(generator.explain(r).text, width=100, initial_indent='   ', subsequent_indent='   '))
        learn = ', '.join(g.label for g in gaps.gaps(r, matches, limit=5))
        print(textwrap.fill(f'Skills to build: {learn}', width=100, initial_indent='   ', subsequent_indent='   '))


if __name__ == '__main__':
    main()
