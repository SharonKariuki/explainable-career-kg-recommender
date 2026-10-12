# AjiraGuide: Testing and Evaluation Report

**Project:** AjiraGuide, an explainable knowledge-graph-based career guidance recommender
**Author:** Sharon Mugure Kariuki
**Scope:** Sprints 1-6: data pipeline, knowledge graph, recommendation engine, explanations, skills gap and web application

## 1. Summary

| Question | Answer |
|---|---|
| Does the system work end to end? | Yes. A new user can register, enter skills and read an explained recommendation in the browser; 116 automated tests pass. |
| Is it better than keyword matching? | Yes. On held-out profiles with two skills, MRR rises from 0.349 to 0.528 (+0.179, 95% CI +0.107 to +0.251); with wording the system has never seen, from 0.132 to 0.552 (+0.421, 95% CI +0.346 to +0.496). |
| Are the explanations faithful? | Yes. 1,798 of 1,798 generated explanations state only what their score used. |
| Are they readable? | Mean Flesch-Kincaid grade 9.7; 98% at grade 12 or below; no technical jargon. |
| Main limitation | On 30 everyday-language profiles, ranking by SBERT similarity alone (MRR 0.865) beats the full system (0.670): the weights were tuned on synthetic profiles that do not read like real users. |

## 2. Testing

### 2.1 Approach

| Level | What it covers | Where |
|---|---|---|
| Unit | Graph construction and traversal, skill matching, scoring, baseline, explanations, fidelity, skills gap, metrics | `backend/tests/` |
| Integration | REST API: accounts, tokens, profiles, recommendations, owner-only access | `test_auth_api.py`, `test_recommendation_api.py`, `test_owner_access.py` |
| System | Realistic user scenarios through the API | `test_system_scenarios.py` |
| End to end | The real web app driven in headless Chrome at desktop and phone width | Manual runs, Sprint 5-6 |
| Data | The processed dataset rebuilt from the original downloads | `python -m pipeline.*` |

### 2.2 Results

All 116 automated tests pass (`python -m pytest` from `backend/`).

| Area | Tests |
|---|---|
| Knowledge graph | 9 |
| Matching, engine, baseline, skills gap | 26 |
| Explanations, fidelity, explanation quality | 26 |
| Evaluation profiles, metrics, tuning and evaluation runner | 23 |
| API: accounts, recommendations, owner-only access | 23 |
| System scenarios | 9 |

The system scenarios cover a new user's full journey (register, empty state,
save skills, recommendations, detail, log out, log back in), a single skill,
unrelated skills ("cooking", "playing guitar"), awkward input ("C++", "R",
"Café management", repeats, blanks), a changed profile, a 30-skill profile
answered in under two seconds, and the fidelity of every served explanation.

End-to-end browser runs: a new user reaches an explained recommendation in
about 5 seconds with no console or network errors. Rebuilding the dataset from
the original O*NET and ESCO files reproduces the committed files byte for byte.

### 2.3 Defects found by testing

| Found by | Defect | Fix |
|---|---|---|
| Matching probe | Asking for part of the embedding cache overwrote the whole cache | Cache keyed by model; only missing texts encoded |
| Fidelity tests | A quoted phrase starting "Your '...'" escaped the check | Case-insensitive match |
| Fidelity batch | Career titles containing skill names ("Database Administrators") reported as violations | Career title treated as permitted text |
| Explanation quality tests | Syllable estimate over-counted words like "role" and "profile" | Silent final "e" rule corrected |
| Browser run | A late profile response erased skills the user had just added | Superseded responses ignored |
| Browser run | Career diagram clipped on phones | Stacked layout below 600px |
| Re-tuning | PageRank divided by zero when every match was uncertain and ignored | Proximity 0 when there is nothing to walk from |
| System scenario | Logging back in failed while the browser still sent a revoked token | Register and login ignore tokens |

## 3. Evaluation

### 3.1 Systems compared

| System | Matching | Ranking |
|---|---|---|
| Keyword baseline | Exact or substring name match | Share of declared skills matched |
| SBERT only | None | Similarity of the profile to each career's O*NET description |
| Graph only | Exact name match into the graph | Coverage and GraphProximity |
| **AjiraGuide (full)** | SBERT | 0.7 Coverage + 0.1 ProfileSimilarity + 0.2 GraphProximity |

### 3.2 Profile sets

| Set | Profiles | Purpose | Correct answer |
|---|---|---|---|
| Validation (clean) | 360 | Tuning only | The career the skills were sampled from |
| Validation (unseen wording) | 360 | Tuning only | As above |
| Test (clean) | 360 | Evaluation | As above |
| Test (unseen wording) | 360 | Evaluation | As above |
| Hand-written | 30 | Evaluation | 1-2 careers, labelled before any results were seen |

Synthetic profiles have 2, 3 or 5 skills sampled from one career's core
requirements, five per career and size. "Unseen wording" profiles use only
alternative skill names that are hidden from the matcher, so a skill must be
recognised by meaning. Validation and test sets use different random seeds;
the two unseen-wording sets hide mostly different names (350 of 569 differ) and
share one profile in 360. Hand-written profiles use everyday language ("good
with people", "crunching numbers").

### 3.3 Metrics

Precision@K, Recall@K and mean reciprocal rank (MRR) of the correct career.
With one correct career, Precision@K is at most 1/K. The difference between
the full system and the baseline is reported with a 95% bootstrap interval
(2,000 resamples of profiles).

### 3.4 Results

**Test profiles, clean wording (360)**

| System | P@1 | P@3 | R@3 | R@5 | MRR |
|---|---|---|---|---|---|
| Keyword baseline | 0.256 | 0.169 | 0.506 | 0.642 | 0.429 |
| SBERT only | 0.086 | 0.090 | 0.269 | 0.381 | 0.244 |
| Graph only | 0.444 | 0.243 | 0.731 | 0.825 | 0.617 |
| **AjiraGuide** | **0.447** | **0.244** | **0.733** | **0.833** | **0.620** |

**Test profiles, unseen wording (360)**

| System | P@1 | P@3 | R@3 | R@5 | MRR |
|---|---|---|---|---|---|
| Keyword baseline | 0.083 | 0.071 | 0.214 | 0.344 | 0.208 |
| SBERT only | 0.206 | 0.123 | 0.369 | 0.494 | 0.347 |
| Graph only | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| **AjiraGuide** | **0.433** | **0.235** | **0.706** | **0.808** | **0.599** |

**MRR by profile size**

| Skills | Keyword (clean) | AjiraGuide (clean) | Keyword (unseen) | AjiraGuide (unseen) |
|---|---|---|---|---|
| 2 | 0.349 | **0.528** | 0.132 | **0.552** |
| 3 | 0.389 | **0.576** | 0.212 | **0.560** |
| 5 | 0.548 | **0.756** | 0.282 | **0.685** |

| AjiraGuide minus keyword, MRR | All profiles | 2-skill profiles |
|---|---|---|
| Clean wording | +0.191 (CI +0.147 to +0.234) | +0.179 (CI +0.107 to +0.251) |
| Unseen wording | +0.391 (CI +0.343 to +0.439) | +0.421 (CI +0.346 to +0.496) |

**Hand-written profiles (30)**

| System | P@1 | P@3 | R@3 | R@5 | MRR |
|---|---|---|---|---|---|
| Keyword baseline | 0.333 | 0.222 | 0.467 | 0.567 | 0.471 |
| SBERT only | **0.800** | **0.356** | **0.817** | **0.933** | **0.865** |
| Graph only | 0.167 | 0.111 | 0.267 | 0.300 | 0.248 |
| AjiraGuide | 0.533 | 0.333 | 0.750 | 0.850 | 0.670 |

AjiraGuide minus keyword: +0.199 MRR (CI -0.006 to +0.406).

**Skill matching on unseen wording (1,200 skills).** 69.1% are matched to
exactly the skill they were sampled from. Matches at or above the 0.60
low-confidence threshold are right 74.8% of the time; below it, 10.4%. The
threshold therefore separates trustworthy matches from guesses, which is why
uncertain matches are flagged to the user and count for half.

### 3.5 Tuning

924 configurations (traversal depth, low-confidence threshold and weight, and
component weights in steps of 0.1) were scored on both validation sets. The
chosen defaults, Coverage 0.7, ProfileSimilarity 0.1, GraphProximity 0.2 at
depth 1 with threshold 0.60, reach combined validation MRR 0.608. The top of
the grid is flat (36 configurations within 0.005), so the choice is stable.
Weights were first tuned on clean validation only (0.3 / 0.3 / 0.4); adding
the unseen-wording validation set raised unseen-wording test MRR from 0.562 to
0.599 without lowering the other sets.

### 3.6 Explainability

| Dimension | Result |
|---|---|
| Fidelity | 1,798 / 1,798 explanations pass (360 validation profiles, top 5 each) |
| Completeness | Every applicable criterion met in 186 scored explanations |
| Readability | Flesch-Kincaid grade mean 9.7 (98% at or below 12); 13.7 words per sentence; no jargon |

Rubric, criteria and the human rating form: `docs/explainability_rubric.md`.
The human rating pass with volunteers has not yet been carried out.

## 4. Discussion

**The combination is what works.** On clean profiles the graph does almost
all the work (graph only 0.617, full 0.620). On unseen wording the graph alone
fails completely, because exact names no longer match, and SBERT alone is
weak (0.347); together they reach 0.599. The knowledge graph supplies precise,
explainable structure and SBERT supplies robustness to wording.

**Sparse profiles benefit most from unseen-wording robustness.** With two
skills, keyword matching finds the right career first or near the top only
rarely (MRR 0.132 on unseen wording); AjiraGuide reaches 0.552.

**Everyday language is the open problem.** On hand-written profiles, ranking
by similarity to the career description is best. Tuning on unseen-wording
validation moved weight towards Coverage, not similarity, because those
alternative names are still technical ("permissioned blockchain"), unlike how
people describe themselves ("good with people"). No synthetic set used here
represents real users.

## 5. Limitations

- The 30 hand-written profiles and their labels were written by the author;
  the sample is small and the interval for the full-vs-keyword difference
  includes zero.
- Synthetic profiles are drawn from the graph itself and are mostly tools,
  because O*NET lists far more tools than rated skills; they favour graph
  methods.
- Each synthetic profile has one correct career, although neighbouring careers
  (Web Developers and Web and Digital Interface Designers) are often both
  reasonable; P@K understates quality.
- The AI domain has one occupation, because O*NET files ML and AI engineer
  titles under Computer and Information Research Scientists.
- Completeness is checked against the explanation generator's own design;
  user-judged completeness, readability and trust need the human rating pass.
- The model takes about 20-30 seconds to load when the server starts.

## 6. Future work

1. Collect real user profiles (for example from the volunteer rating pass) and
   re-tune on them.
2. Adaptive weighting: lean on ProfileSimilarity when a profile matches the
   graph poorly, as everyday-language profiles do.
3. Graded relevance using O*NET's related-occupation lists, so near-miss
   careers earn partial credit.
4. Run the human rating pass from the rubric with 5-10 volunteers.

## 7. Reproducing

From `backend/` with the virtual environment active:

| Command | Output |
|---|---|
| `python -m pytest` | 116 tests |
| `python -m recommender.tuning` | `data/results/tuning.csv` |
| `python -m recommender.evaluate` | `data/results/evaluation.csv` and the tables above |
| `python -m recommender.fidelity` | Fidelity over all validation explanations |
| `python -m recommender.explanation_quality` | `data/results/explanation_quality.csv` |
