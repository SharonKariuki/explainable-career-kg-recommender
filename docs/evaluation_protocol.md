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

## Planned sets (not yet built)

### Task-statement profiles

O*NET task statements are written independently of the graph, so they test
the graph corrections without circularity.

- Inputs: Core task statements only, split per career into validation and
  test pools.
- Graded relevance, kept for ambiguous tasks rather than dropping them:
  - 3: the source occupation
  - 2: an occupation with a near-identical task, nominated at SBERT cosine
    ≥ 0.85 and confirmed by semantic review (similarity alone never sets a
    label)
  - 1: an O*NET Primary-Short related occupation
- Other O*NET relatedness tiers are recorded for a sensitivity analysis.
- Known risk: a single task picks its own occupation from the 24 career
  descriptions 38% of the time (chance is 4%), which favours text
  similarity. SBERT-only is reported alongside the full system on these
  sets.

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
