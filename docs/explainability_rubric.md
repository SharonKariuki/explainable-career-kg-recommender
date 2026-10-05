# Explainability Quality Score: rubric

AjiraGuide explains every recommendation in plain language. The Explainability
Quality Score rates those explanations on three dimensions:

| Dimension | Question | How it is scored |
|---|---|---|
| Fidelity | Does the explanation only state what the score actually used? | Automatically, by `recommender/fidelity.py` |
| Completeness | Does it cover everything that drove the score? | Automatically (criteria C1-C6), and by human raters |
| Readability | Can a student understand it? | Automatically (reading level, sentence length, jargon), and by human raters |

## 1. Fidelity

An explanation passes when every skill it names and every value it quotes
belongs to that recommendation's score components, and its text names no
other skill in the knowledge graph. This is pass/fail and must be 100%.

## 2. Completeness

Each criterion is met, not met, or not applicable to that explanation.

| | Criterion | Applies when |
|---|---|---|
| C1 | States how good the match is and gives the score | Always |
| C2 | Names the strongest declared skills behind the score and counts the rest; if none apply directly, says so | Always |
| C3 | Uses the user's own words where the matched skill has a different name ("Structured query language SQL (your 'sql')") | A declared skill was matched to a differently named skill |
| C4 | Discloses every uncertain match and advises caution | A declared skill matched with similarity below 0.60 |
| C5 | Covers all three score components: Coverage, ProfileSimilarity, GraphProximity | Always |
| C6 | Says how the score weights the components | Always |

**Completeness score** = criteria met / criteria applicable (0 to 1).

## 3. Readability

| Measure | Target |
|---|---|
| Flesch-Kincaid grade level | 12 or below (readable by a school leaver) |
| Average words per sentence | 25 or fewer |
| Technical terms (IDF, PageRank, cosine, embedding, vector, node, edge, SBERT, BFS, traversal) | None, other than inside a skill's own name such as Node.js |

## 4. Results (automated)

Scored on 186 explanations: the top 3 careers for 52 synthetic validation
profiles and for 10 profiles written in everyday words ("good with people",
"fixing computers", "cooking"). Per-explanation scores are in
`data/results/explanation_quality.csv`.

| Measure | Result |
|---|---|
| Fidelity | 1,798 / 1,798 explanations pass (all 360 validation profiles, top 5 each) |
| Completeness | 1.00 mean; every applicable criterion met in all 186 (C3 applied to 94, C4 to 8) |
| Flesch-Kincaid grade | mean 9.7, max 12.8; 98% at grade 12 or below |
| Flesch reading ease | mean 49.7 |
| Words per sentence | mean 13.7; longest sentence 38 words |
| Technical terms | none |

Two changes came out of the first scoring run: the graph sentence no longer
repeats skills already named ("connected mainly through the skills above"),
which brought the mean grade from 11.1 down, and the jargon check now ignores
skill names (Node.js had been flagged as "node").

### Limits of the automated scores

- **Completeness is checked against the generator's own design.** Its
  criteria list what the generator was built to include, so 100% shows the
  generator reliably does what it promises. Whether users find the
  explanations complete needs human raters (section 5).
- **Readability formulas are approximate.** Flesch-Kincaid counts sentence
  and word length only; long skill names from O*NET and ESCO ("execute
  analytical mathematical calculations") raise the grade, and the formula
  cannot judge whether a sentence makes sense.
- **Uncertain matches come only from the hand-written profiles.** Synthetic
  profiles reuse skill names the matcher already knows, so they always match
  exactly. C4 was tested on 8 explanations.

## 5. Human rating form (Sprint 6, issue #49)

For each explanation, the rater reads the declared skills, the recommended
career and its explanation, then answers:

| | Question | Scale |
|---|---|---|
| H1 | I understand why this career was recommended. | 1 (strongly disagree) to 5 (strongly agree) |
| H2 | The explanation mentions the things that matter for this recommendation. | 1 to 5 |
| H3 | The explanation is easy to read. | 1 to 5 |
| H4 | After reading it, I trust this recommendation more. | 1 to 5 |
| H5 | Anything confusing, missing or wrong? | Free text |

H1 and H3 support readability, H2 completeness, and H4 the trust goal of
explainability. Suggested procedure: 5-10 volunteers, each rating the same 10
explanations drawn from `data/results/explanation_quality.csv` (mix of strong,
weak and uncertain matches), so ratings can be compared across raters.

## Reproducing

From `backend/`:

```bash
python -m recommender.fidelity               # fidelity over all validation profiles
python -m recommender.explanation_quality    # completeness and readability sample
```
