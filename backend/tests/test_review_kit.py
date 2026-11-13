"""Human review kit for the gold labels (release P5): seeded sampling and scoring."""
import csv

import pytest

from pipeline import review_kit


def test_sampling_is_seeded_and_stratified(tmp_path):
    review_kit.sample(tmp_path / 'a')
    review_kit.sample(tmp_path / 'b')
    for name in ('mapping_review.csv', 'profile_review.csv'):
        assert (tmp_path / 'a' / name).read_bytes() == (tmp_path / 'b' / name).read_bytes()
    with open(tmp_path / 'a' / 'mapping_review.csv', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    labels = {r['gold_label'] for r in rows}
    assert labels == {'unambiguous', 'ambiguous', 'no_concept'} and all(r['verdict'] == '' for r in rows)


def write(path, header, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)


def test_scoring_counts_agreement_and_refuses_blank_verdicts(tmp_path):
    mapping = [{'id': f'm{i}', 'group': f'g{i}', 'verdict': 'agree' if i % 10 else 'disagree'} for i in range(100)]
    mapping[0]['verdict'] = 'unsure'
    profiles = [{'id': f's{i}', 'sufficiency_verdict': 'agree', 'grades_verdict': 'agree'} for i in range(80)]
    write(tmp_path / 'mapping_review.csv', ['id', 'group', 'verdict'], mapping)
    write(tmp_path / 'profile_review.csv', ['id', 'sufficiency_verdict', 'grades_verdict'], profiles)
    report = review_kit.score(tmp_path)
    assert report['mapping labels']['decided'] == 99 and report['mapping labels']['unsure'] == 1
    assert report['mapping labels']['agree'] == pytest.approx(90 / 99)
    assert report['profile sufficiency']['outcome'] == 'Pass'
    profiles[0]['grades_verdict'] = ''
    write(tmp_path / 'profile_review.csv', ['id', 'sufficiency_verdict', 'grades_verdict'], profiles)
    with pytest.raises(ValueError):
        review_kit.score(tmp_path)
