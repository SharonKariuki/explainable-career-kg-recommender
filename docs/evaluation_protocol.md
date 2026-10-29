# Evaluation protocol

How AjiraGuide's recommendations are evaluated from Phase 1 onwards: which
profile sets exist, what each may be used for, and how test results are kept
independent of every choice made during development.

The v1 results (`data/results/*.csv`, tag `v1-baseline`, commit `875fcd0`)
were produced before this protocol and are kept unchanged as the baseline.

## Roles

| Role | May be used for | Never used for |
|---|---|---|
| development | debugging, diagnosing failures, examples | any reported claim |
| validation | choosing parameters, graph corrections and configurations | final results |
| test | reporting a frozen configuration, once | any choice |

## Profile sets

Hashes are sha256 of each set's canonical JSON (profiles in generated order,
dict keys and label sets sorted); the noisy sets hash the pair (hidden
names, profiles). `tests/test_protocol.py` checks them.

| Set | Role | How it is made | Profiles | Labels | sha256 (prefix) |
|---|---|---|---|---|---|
| `synthetic-validation` | validation | 2, 3 or 5 skills drawn from one career's requirements with edge weight ≥ 0.75, seed 1; half written under another name, half lower-cased | 360 | the source career | `05352ba9178648d9` |
| `noisy-validation` | validation | as above from edges ≥ 0.5, written only with names hidden from the matcher; hidden names seed 6, profiles seed 5 | 360 | the source career | `b78e59478c0a53f1` |
| `synthetic-test` | test | as `synthetic-validation`, seed 2 | 360 | the source career | `33925f8531db0cda` |
| `noisy-test` | test | as `noisy-validation`; hidden names seed 3, profiles seed 4 | 360 | the source career | `148718c5811df29f` |
| `hand-v1` | development | 30 everyday-language profiles in `evaluation.py` | 30 | 1-2 careers each, written with the profiles | `0ad60ebd2ee04c13` |

Notes:

- **`hand-v1` is now development data.** The v1 report used it as a
  held-out test set (full system MRR 0.670, SBERT-only 0.865). Its profiles
  were then used to diagnose why the full system lost to SBERT-only, so
  they have shaped the Phase 1 changes and can no longer give independent
  evidence. Its v1 figures stay in the v1 report as they were; it is not
  used for claims about later configurations.
- **The synthetic and noisy sets are generated from the graph.** A
  correction to the graph data changes them, and they reward agreement with
  the graph they were drawn from. They remain valid for parameter choices on
  a fixed graph, but graph corrections are judged on graph-independent sets
  (task statements and hand-written profiles, below), and any change to
  these four sets is reported with its new hashes.
- **Noisy validation and test overlap slightly:** skills with a single
  alternative name are hidden in both, and 1 of 360 profiles coincides.

## Rules

1. Parameters, graph corrections and configurations are chosen on
   validation sets only. Development sets may guide where to look but are
   not evidence.
2. Before a test run, the configuration is frozen: committed, with its
   configuration identifier recorded (see manifests).
3. Each frozen configuration is evaluated on the test sets once. A test
   result never leads to another change that is then re-tested and reported
   as if it were independent.
4. Every hypothesis is reported, including negative and inconclusive
   results, with uncertainty where the sample allows it.
5. Labels are frozen by hash before they are used for any reported result.
6. Scoring weights stay as tuned in v1 throughout Phase 1.
7. Graph corrections never cite O*NET task statements as evidence, since
   they are evaluation inputs.

## How the rules are enforced

- **Test sets are locked.** The generators refuse the test seeds (2, 3, 4)
  unless called inside `open_test_sets()`. Later test sets (task-statement
  and hand-written test pools) use the same lock.
- **A test run needs a clean working tree.** `open_test_sets()` checks
  `git status` first and refuses if anything is uncommitted, before any test
  data is loaded, so every test result maps to a commit. New run folders
  under `data/results/` do not count as changes; everything else does,
  including untracked files. Validation and development runs may use a
  dirty tree, and their manifests record it.
- **Access is narrow.** Only `recommender/evaluate.py` opens the test sets,
  in one `with` block around loading them; the lock closes again when the
  block ends, including on errors.
- **Tests check this.** `tests/test_protocol.py` inspects the application
  source and fails if any module other than `evaluation.py` and
  `evaluate.py` names a test-set loader, test seed or the lock, and if
  `tuning.py` imports anything beyond the validation sets. Runtime tests
  confirm the lock refuses each test set, that a dirty tree is refused
  before loading, and that access does not carry over into tuning or the
  explanation scoring afterwards.

These checks stop accidental or casual access by code. They cannot stop a
deliberate edit to the guard, which would show up in review and in git
history.

## Result runs and manifests

Each run writes to its own new folder, `data/results/<run>/`, and never
replaces an existing folder or file; `v1` is reserved. Each folder has a
`manifest.json` recording:

- the run name and exact command
- start and finish times (UTC)
- the git commit, whether the working tree was clean, and what was uncommitted
- each profile set used: identifier, role, number of profiles and sha256
- the configuration: engine parameters (none for a grid search), SBERT
  model, sha256 of every processed data file, and a 12-character
  configuration identifier derived from them

The identifier names a frozen configuration: two runs with the same
identifier used the same parameters, model and graph data.

## Metrics

v1 metrics: Precision@1, Precision@3, Recall@3, Recall@5 and MRR, overall
and by profile size, with 95% bootstrap intervals for differences between
systems. Phase 1 adds nDCG@3 and nDCG@5 (for graded labels) and the
candidate rate (share of profiles that receive any recommendation).

Definitions:

- **nDCG@k**: DCG@k = Σ grade(rank) / log₂(rank + 1) over the top k
  recommendations, with linear gains (grade 3, 2, 1 or 0), divided by the
  DCG@k of the ideal ordering of that profile's labels. A profile with no
  recommendation scores 0.
- **Candidate rate**: share of profiles with at least one recommendation.
- **MRR**: reciprocal rank of the first relevant career (any grade ≥ 1),
  0 when none is recommended.

### Model selection versus reporting

**Selection** (validation sets only) chooses between configurations, such as
the B1 broad-match factors and B2 ESCO floors:

- **Primary metric: nDCG@5** on the graph-independent validation sets (the
  task-statement validation pool and the `hand-v2` validation profiles).
  nDCG uses the graded labels; MRR would ignore grades 1 and 2.
- **Guardrails**, each of which a candidate must pass whatever its nDCG@5:
  - **candidate rate** does not fall below the v1 baseline's;
  - all **known-answer probes** still pass;
  - **validation MRR** on `synthetic-validation` and `noisy-validation`
    does not fall by more than the width of its 95% bootstrap interval.
- **Ties**: if no candidate beats the baseline's nDCG@5 by more than its
  95% bootstrap interval, the simpler configuration (fewer graph changes)
  is kept.

**Final reporting** (test sets, once per frozen configuration) reports
everything: MRR, nDCG@3, nDCG@5, Precision@1, Precision@3, Recall@3,
Recall@5 and candidate rate, per set and per hypothesis, with 95% bootstrap
intervals for differences against the v1 baseline and SBERT-only. Negative
and inconclusive results are reported as they are; no test metric is used
to choose or adjust a configuration.

### Graded sets: relevance thresholds and supplementary reporting

On graded sets (`tasks-v1`, `hand-v2`) Precision@1 counts a hit when the
first career has grade ≥ 2 (a listing occupation or one with a
near-identical task). Recall@K and MRR keep grade ≥ 1, and nDCG uses the
grades. These do not change the selection rule above.

Because grade-1 labels are broad (a median of six relevant careers out of
24 on `tasks-v1`), the following are reported alongside, for information
only:

- MRR at grade ≥ 2, the same threshold as Precision@1
- Hit@3 and Hit@5 at grade ≥ 2: whether any such career is in the top K
- a strict view: Precision@1 and MRR counting grade 3 only, always shown
  next to Precision@1 at grade ≥ 2, with the number of profiles carrying a
  grade-2 label and the largest gap it allows between the two
  (`graded_metrics`, `graded_summary` and `graded_disclosure` in
  `evaluation.py`)
- the chance level of Precision@1, MRR and Hit@K for a random ranking,
  computed per profile from its number of relevant careers (`chance_*` in
  `evaluation.py`); on `tasks-v1` chance MRR at grade ≥ 1 is 0.42. No
  chance level is computed for nDCG or Recall@K.

**Planned, not yet implemented:** nDCG@5 broken down by thirds of
own-description cosine and by the graph-skill wording flag, to show how much
of a result comes from text overlap with the career descriptions or the
graph's vocabulary. The task set stores both covariates, but the reporting
code does not use them yet; this breakdown must be implemented before any
result on the frozen `tasks-v1` is reported.

## Planned sets (not yet built)

### Task-statement profiles (`tasks-v1`, frozen 2026-10-28)

O*NET task statements are written independently of the graph (the pipeline
never reads them), so they test graph corrections without circularity.
Built by `python -m recommender.task_sets nominate` and `build`
(`backend/recommender/task_sets.py`); neither step runs the recommender.

- **Inputs:** O*NET 31.0 Core task statements, one per profile, entered
  word for word as a single input.
- **Coverage:** 10 profiles per career drawn with seed 7: 240 profiles, 5
  validation and 5 test per career.
- **Graded relevance**, kept for ambiguous tasks rather than dropping them:
  - 3: an occupation that lists the task
  - 2: the occupation of a near-identical task, nominated at SBERT cosine
    ≥ 0.85 and accepted on review in `data/eval_sets/twin_review.csv`
    (similarity alone never sets a label). Of 22 nominated pairs, 18 are
    accepted. Four are rejected: one pair of different scope whose careers
    are only Primary-Long related, and three where the second occupation
    oversees or coordinates the analyst's task, since the Primary-Short
    relation already grades that career 1.
  - 1: an O*NET Primary-Short related occupation of a listing occupation,
    in O*NET's direction
- Primary-Long and Supplemental relations are stored, ungraded, for a
  sensitivity analysis.

**Evaluation-design decisions** (fixed before any recommender run on the set):

1. **Duplicate texts.** Task texts that are equal after lower-casing and
   removing punctuation and extra spacing are one profile. O*NET lists 15
   such texts under two occupations each; both occupations get grade 3,
   since the task is equally their own. Without this, the same input would
   appear twice with opposite correct answers.
2. **Quota ownership.** A merged profile counts toward the 10 of the
   listing occupation with the lowest Task ID; the other occupation's 10
   come from its remaining tasks. The rule is arbitrary but deterministic.
3. **Graph-skill wording flag.** A task is flagged when it contains a graph
   skill name of two or more words (any case) or a single-word tool name in
   its exact case. Single generic words ("data", "design") never count. On
   O*NET 31.0 no Core task contains a single-word tool name, so the flag
   marks tasks sharing a multi-word phrase with the graph's vocabulary
   ("business intelligence", "write reports"): an exact lexical route for
   the matcher, not a mention of a tool.
4. **Split.** Hard constraints: 5 validation and 5 test per career, and
   tasks linked by any nominated pair (accepted or rejected) in the same
   split. Within those, an exact search over every split of each career
   balances, in order: the career's flagged tasks, then its tasks in each
   third of own-description cosine (thirds of the 240 values, equal values
   together), then the overall totals. Result: flagged tasks 20 and 20,
   every career within one on the flag and on each third, and mean cosine
   0.444 (validation) against 0.439 (test).

- **Leakage, reported rather than filtered:** a task picks its own
  occupation from the 24 career descriptions 40% of the time (chance 4%).
  Each profile stores its cosine to its listing occupations' descriptions
  (the highest, to 2 decimals), its third, and the wording flag, for the
  planned breakdown above; SBERT-only is reported alongside the full
  system. The split is balanced on these covariates, never on recommender
  output.
- **Grade 2 is rare.** Identical texts are merged and graded 3, and only
  three reworded pairs are accepted, so 4 validation profiles and **1 test
  profile** carry a grade-2 label. On test, Precision@1 at grade ≥ 2 can
  differ from the strict grade-3 version by at most one profile (1/120);
  both are reported, and no claim about near-identical tasks is made from
  the test split. The labels are not changed to raise this count.
- **Reproducibility.** The frozen `tasks_v1.csv` is authoritative: nothing
  rewrites it, and SBERT values are only compared, never used to re-split.
  `python -m recommender.task_sets verify` checks it in three tiers:
  1. *Integrity:* the raw O*NET files and, once frozen, the frozen files
     match their sha256 (below). Fails on any difference.
  2. *Exact regeneration, without SBERT:* each selected task appears once;
     task IDs, texts, listing occupations and labels regenerate from the
     raw files and the reviewed pairs; each stored cosine third is the
     third of its stored cosine; and the split regenerates from the stored
     flag and thirds. Fails on any difference.
  3. *Covariate drift, with SBERT:* recomputed cosines must lie within
     ±0.01 of the stored ones (fails otherwise); a task whose recomputed
     third differs is reported as a warning, and the stored third and split
     stand. Cosines are stored to 2 decimals, so a harmless floating-point
     difference can cross a rounding edge and change a value by one step,
     0.01; a larger difference means a real change, such as another model
     version or edited descriptions.

  The stored flag and cosines describe the v1 data (`COVARIATE_DATA` in
  `task_sets.py`). After that data changes, for example through a graph
  correction, both stand as stored: the flag is no longer recomputed in
  tier 2 and cosine drift is no longer checked in tier 3, which says so in
  a warning. Residual limit: an edit that moves stored cosines by at most
  0.01 and adjusts thirds and split to match would pass tiers 2 and 3 with
  only warnings; once frozen, tier 1's hash rejects any edit. Selection and
  split use Python's seeded `random` and were built with Python 3.11.9.
- **Freezing:** `tasks_v1.csv` and `twin_review.csv` are frozen together;
  their sha256 values go in `task_sets.FROZEN` and the table below. Until
  then the loaders refuse to load either split, and the test split is
  locked like the other test sets.

| Field | Value |
|---|---|
| `Task Statements.txt` sha256 | `aee1788c7ce2ebf19c1700bc4a1d7aa69a59965736d56a521945256df3f68d08` |
| `Related Occupations.txt` sha256 | `af539f6f01a36e9514a0dd13cbe125df8cca1114c690505342837f338621906c` |
| `db_31_0_text.zip` sha256 | `6883548adf5fde64cf6f801b35d15519c9225f2732c3cab0e281c652d16b23a9` |
| Near-identical pairs reviewed and approved by | Sharon Kariuki (all 22 decisions) |
| Approval date | 2026-10-28 |
| `tasks_v1.csv` sha256 | `f6cc9db450c9b8fdb714e5f01f3ab2a91760868e8b1fca7661bcc410a2a2a84b` |
| `twin_review.csv` sha256 | `1b557b3b2f3c922a9c5b396b8e57a6b4f194164acb4a9fc54411d05b4e4dc6b4` |

### Hand-written profiles (`hand-v2`)

- 48 profiles, two per career: 24 validation and 24 test, balanced for
  writing style and skill specificity.
- Each profile lists its relevant careers with a one-line reason per label.
- Labels are reviewed by the project author before freezing; the frozen
  file's sha256 is recorded here.

| Field | Value |
|---|---|
| Drafted by | _to be recorded_ |
| Reviewed and approved by | _to be recorded_ |
| Approval date | _to be recorded_ |
| Frozen file and sha256 | _to be recorded_ |
