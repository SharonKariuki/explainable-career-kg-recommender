"""Score explanations for completeness and readability (rubric: docs/explainability_rubric.md).

Fidelity is checked separately (fidelity.py). This module applies the parts
of the rubric that can be scored from an explanation and its recommendation:

Completeness, each criterion met or not (or not applicable):
  C1  states the fit and the score
  C2  names the strongest declared skills behind Coverage and counts the rest
  C3  uses the user's own words where the matched skill is named differently
  C4  discloses every flagged match: low confidence, a close second reading or a shared name (#161)
  C5  covers all three components (Coverage, ProfileSimilarity, GraphProximity)
  C6  says how the score weights the components

Readability: Flesch-Kincaid grade level, Flesch reading ease, sentence
lengths, and technical terms a student would not know.

Usage (from backend/):
    python -m recommender.explanation_quality --run NAME   # score a sample, write data/results/<run>/explanation_quality.csv
"""

import re

from recommender.explanation import SHOWN_CONTRIBUTIONS, cautions, is_uncertain, reading_lookup

JARGON = ('idf', 'pagerank', 'cosine', 'embedding', 'vector', 'node', 'edge', 'sbert', 'bfs', 'traversal')
TARGET_GRADE = 12
MAX_AVERAGE_SENTENCE_WORDS = 25

WORD = re.compile(r"[A-Za-z][A-Za-z'*+#.-]*")


def syllables(word):
    """Approximate syllable count: vowel groups, ignoring a silent final 'e'
    (but not the spoken '-le' after a consonant, as in 'table')."""
    word = word.lower().strip(".'")
    groups = re.findall(r'[aeiouy]+', word)
    count = len(groups)
    spoken_le = re.search(r'[^aeiouy]le$', word)
    if word.endswith('e') and not word.endswith('ee') and not spoken_le and count > 1:
        count -= 1
    return max(count, 1)


def readability(sentences, names=()):
    """`names` (skill names, the user's words, the career title) are excluded from
    the jargon check, so a skill such as Node.js is not mistaken for 'node'."""
    words = [w for s in sentences for w in WORD.findall(s)]
    lengths = [len(WORD.findall(s)) for s in sentences]
    per_sentence = len(words) / len(sentences)
    per_word = sum(syllables(w) for w in words) / len(words)
    text = ' '.join(sentences)
    for name in sorted(set(names), key=len, reverse=True):
        text = text.replace(name, ' ')
    text = text.lower()
    return {
        'fk_grade': round(0.39 * per_sentence + 11.8 * per_word - 15.59, 2),
        'reading_ease': round(206.835 - 1.015 * per_sentence - 84.6 * per_word, 2),
        'avg_sentence_words': round(per_sentence, 1),
        'max_sentence_words': max(lengths),
        'jargon': ' '.join(t for t in JARGON if re.search(rf'\b{t}\b', text)),
    }


def completeness(explanation, recommendation, readings=()):
    """{criterion: True / False / None (not applicable)}."""
    text, r = explanation.text, recommendation
    contributions = r.skill_contributions
    reading = reading_lookup(readings)
    shown = [s for i, s in enumerate(contributions)
             if i < SHOWN_CONTRIBUTIONS or s.low_confidence or is_uncertain(reading(s))]
    quoted = dict(explanation.quoted_components)

    renamed = [s for s in shown if s.query.casefold() != s.skill_label.casefold()]
    # Since #161 C4 covers every flagged contribution: low confidence, a close second reading, or a shared name.
    flagged = [s for s in contributions if s.low_confidence or is_uncertain(reading(s))]
    return {
        'C1_fit_and_score': ('match for your skills' in text or 'for your skills (score' in text) and 'score' in quoted,
        'C2_skills_behind_coverage': (
            all(s.skill_label in text for s in shown)
            and (len(contributions) == len(shown) or f'plus {len(contributions) - len(shown)} more' in text)
        ) if contributions else 'does not directly require' in text,
        'C3_users_own_words': all(f"your '{s.query}'" in text for s in renamed) if renamed else None,
        'C4_uncertain_matches_disclosed': all(
            any(c in text for c in cautions(s, reading(s))) and cautions(s, reading(s))
            for s in flagged) if flagged else None,
        'C5_all_three_components': (
            ('coverage' in quoted or not contributions)
            and 'profile_similarity' in quoted
            and ('graph_proximity' in quoted or not r.proximity_paths)
        ),
        'C6_score_weights': 'weights coverage' in text,
    }


def score(explanation, recommendation, readings=()):
    r = recommendation
    criteria = completeness(explanation, r, readings)
    applicable = [v for v in criteria.values() if v is not None]
    names = [r.title, *(s.skill_label for s in r.skill_contributions), *(s.query for s in r.skill_contributions),
             *(p.skill_label for p in r.proximity_paths)]
    return {
        **criteria,
        'completeness': round(sum(applicable) / len(applicable), 4),
        **readability(explanation.sentences, names),
    }


# Profiles in everyday wording. Synthetic profiles reuse names the matcher
# already knows, so they never produce uncertain matches; these do.
HAND_WRITTEN_PROFILES = (
    ('good with people', 'fixing computers', 'Windows'),
    ('building websites', 'JavaScript', 'graphic design'),
    ('Excel', 'making charts', 'good with numbers'),
    ('hacking', 'networks', 'Linux'),
    ('Python', 'maths', 'curious about AI'),
    ('managing a team', 'planning projects', 'budgets'),
    ('playing guitar', 'Python', 'SQL'),
    ('cooking', 'customer service'),
    ('teaching', 'public speaking', 'research'),
    ('phones', 'apps', 'Java'),
)


def near_tie_with_top(assessment, ranked, recommendation):
    """In a near tie with the top career: close_call holds and it scores within epsilon of the top."""
    e = assessment['evidence']
    return bool(e['close_call'] and ranked and ranked[0].score - recommendation.score <= e['thresholds']['epsilon'])


def main(argv=None):
    import pandas as pd

    from recommender.engine import DEFAULT_PARAMS, get_engine
    from recommender.evaluation import describe_sets, validation_profiles
    from recommender.explanation import ExplanationGenerator
    from recommender.results import configuration, parse_run, run_started, write_csv, write_manifest

    run = parse_run(__doc__.splitlines()[0], argv)
    started = run_started(__spec__.name, argv)

    engine, generator = get_engine(), ExplanationGenerator()
    validation = validation_profiles(engine.kg)
    sample = [(p.profile_id, p.skills, 'synthetic') for p in validation[::7]]
    sample += [(f'hand-{i}', skills, 'hand-written') for i, skills in enumerate(HAND_WRITTEN_PROFILES)]
    from recommender import evidence
    from recommender.fidelity import check_fidelity
    rows = []
    for profile_id, skills, kind in sample:
        # As the API explains: with the profile's readings, its evidence and the near-tie flag (#161).
        matches, ranked = engine.rank(skills, top_k=None)
        assessment = evidence.assess(engine, matches, ranked)
        for rank, r in enumerate(ranked[:3], 1):
            near_tie = near_tie_with_top(assessment, ranked, r)
            x = generator.explain(r, matches, assessment, rank, near_tie)
            rows.append({'profile_id': profile_id, 'kind': kind, 'skills': ' | '.join(skills),
                         'rank': rank, 'career': r.title, 'insufficient': assessment['insufficient'],
                         'near_tie': near_tie, **score(x, r, matches),
                         'fidelity': check_fidelity(x, r, matches).passed, 'text': x.text})

    results = pd.DataFrame(rows)
    out = write_csv(results, run, 'explanation_quality.csv')
    sets = describe_sets({'synthetic-validation': validation, 'explanation-sample': HAND_WRITTEN_PROFILES},
                         roles={'explanation-sample': 'development'})  # every 7th validation profile is scored
    write_manifest(run, started, sets, configuration(DEFAULT_PARAMS))

    criteria = [c for c in results.columns if c.startswith('C')]
    kinds = results.drop_duplicates('profile_id')['kind'].value_counts()
    print(f'{len(results)} explanations (top 3 for {kinds.get("synthetic", 0)} synthetic validation profiles and '
          f'{kinds.get("hand-written", 0)} hand-written ones) -> {out}\n')
    print('Completeness (share met, where applicable)')
    for c in criteria:
        applicable = results[c].dropna()
        print(f'  {c:32} {applicable.astype(bool).mean():.0%}  (applies to {len(applicable)})')
    print(f'  overall completeness score: mean {results.completeness.mean():.3f}, min {results.completeness.min():.3f}')
    print(f'  fidelity: {results.fidelity.mean():.0%} pass; insufficient profiles {results.insufficient.mean():.0%} '
          f'of explanations; near ties {results.near_tie.mean():.0%}')
    print('\nReadability')
    print(f'  Flesch-Kincaid grade: mean {results.fk_grade.mean():.1f}, max {results.fk_grade.max():.1f} '
          f'(target <= {TARGET_GRADE}; {(results.fk_grade <= TARGET_GRADE).mean():.0%} meet it)')
    print(f'  Flesch reading ease: mean {results.reading_ease.mean():.1f}')
    print(f'  words per sentence: mean {results.avg_sentence_words.mean():.1f}, '
          f'longest sentence {results.max_sentence_words.max()} words')
    print(f'  explanations with jargon: {(results.jargon != "").sum()}')


if __name__ == '__main__':
    main()
