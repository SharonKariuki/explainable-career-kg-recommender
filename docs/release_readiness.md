# Student-ready release: plan, evidence and status

**Branch:** `feat/release-readiness`, from `main` at `9403ea0`. It has local commits only.

**Status (updated 13 November 2026, see §0): safe for a controlled, supervised pilot; not ready for general student release.** §4 lists the gates that are still open. Nothing here changes the approved Measured Matching (M7) protocol, its targets or its locked test results. The M7 test splits were read once, and they are not used again.

## 0. Student-ready round (13 November 2026)

| # | Work | Evidence | Result |
|---|---|---|---|
| 1 | Reproducible image (#173) | The cache is built with the gate's arithmetic, `wheel` is removed, and the build fails on any package difference (PR #175). Drift on `main` (43422358521): **no drift**, 77 packages as locked, 0 ranking differences. The dry run fails as required | **Pass**, #173 closed. The cache-hash anomaly is tracked in #176 |
| 2 | Ambiguous skill names | An `ambiguous_term` flag for generic one-word skills (off by default). Validation: M7 0.158 → 0.143; ambiguous recall 4/31 → 14/31; M6 on C\* 0.140 → 0.158 | **Needs your decision.** Fewer confident errors, but slightly more false flags, and it changes the approved flag definition |
| 3 | Evidence safety rule (`recommender/presentation.py`, **on**) | A strong or good label needs at least 2 confident, specific skills (required by 10 careers or fewer). Validation: exposure of human-insufficient profiles to a strong or good label **0.093 (U 0.142 ≤ 0.15): Pass**, down from about 0.70. Cost: 48% of confident labels on sufficient profiles are kept | **Done.** The API adds `fit_shown` and `evidence_support`; `fit` and rankings are unchanged (snapshot `b0f2952e` with the same cache) |
| 4 | Human label review | Guide, adjudication log, approval form (`docs/validation/`), and `pipeline.review_kit` | **Needs reviewers** |
| 5 | Student study | Protocol, information sheet, consent form, session script, results template (`docs/validation/`) | **Needs ethics approval and students** |
| 6 | Browser journey | `tests/test_browser_journey.py` (Playwright, Chromium, desktop and 390-pixel mobile): sign-up, empty profile, invalid input, a thin profile shown as possible, a specific profile, the explanation, skills plan, history, an API error, and account deletion with refused sign-in | **Pass**, with no uncaught page errors |
| 7 | Checks | Backend 449 passed, 5 xfailed (browser tests included). Frontend 57 tests, oxlint clean, Vite build. Invariance gate and drift on `main` pass | **Pass** |

### Release checklist

| Gate | Status |
|---|---|
| Ranking reproducible in production (AC1, #173) | **Pass** |
| Strong or good labels limited to adequate evidence (S1) | **Pass** on validation |
| Explanations: fidelity, disclosure, readability (AC13) | Pass (M7); new wording passes fidelity |
| Browser journey, desktop and mobile | **Pass** |
| False uncertainty within target (AC4) | **Inconclusive** (M7) |
| Ambiguous-term flag adopted | Awaiting decision |
| Evidence sufficiency as a classifier (AC9, AC10) | **Not met**; replaced for students by the S1 safety rule |
| Gold labels reviewed by humans (Q2) | **Open:** needs reviewers |
| Student study criteria | **Open:** needs ethics approval and students |
| Confidently incorrect mappings | About 14–16% of validation items; a known limitation |

**Verdict.** AjiraGuide is safe for a **controlled pilot**: supervised, with consenting students, clearly labelled as guidance, and run alongside the study. It is **not ready for general student release** until human label review and the student study pass their pre-registered criteria.

## 1. Work done, in priority order

| # | Area | Change | Evidence | Result |
|---|---|---|---|---|
| P0 | Production reproducibility | The API image installs exactly the approved lock (`--no-deps`, the same lock and command as the invariance gate). The app loads the approved model revision (`MODEL_REVISION`), and the invariance fingerprint resolves that same revision | `test_release_reproducibility.py`. The local invariance snapshot under the pinned model is byte-identical (`profiles_sha256 b0f2952e…`) | **Done locally.** Not yet confirmed by a CI image build and a drift run, which need a push |
| P1 | Uncertainty calibration | The flag's similarity threshold is now a separate setting, defaulting to the approved 0.60. `python -m recommender.calibration --joint` searches it with δ on development; `mapping_eval --tau` runs the validation read | Development choice: τ 0.51, δ 0.025. Validation read: M7 0.218 (approved flag: 0.158); M6 on C\* 0.187 (approved: 0.140); no-concept recall 0.66 (approved: 0.86) | **Rejected:** worse on validation. The approved flag stays |
| P2 | Evidence sufficiency redesign | `python -m recommender.evidence_study` searches specificity rules (career or domain support, similarity and requirement floors) and a logistic model under grouped 5-fold cross-validation, on development only | No setting meets recall ≥ 0.80 and false insufficient ≤ 0.10. Best balance: 0.81 and 0.19 (logistic) | **No candidate qualifies**, so no validation read was spent. evidence-v1 stays as approved, with its wording off |
| P3 | Mapping accuracy | An unapproved candidate behind `SkillMatcher(candidate=True)`: 52 aliases written from general usage and development errors only, plus dropping filler words such as "stuff". `mapping_eval --candidate` evaluates it | Development M1 0.765 → 0.888 (overfit). Validation M1 0.639 → 0.653, M2 0.726 → 0.748, M7 0.158 → 0.163 | **Not recommended.** The gain is within noise and does not justify a new ranking baseline. It stays off; production rankings are unchanged |
| P4 | Application journey | `test_live_journey.py` drives every route the web app calls, over HTTP against a live server: sign-up through account deletion, including token rotation on password change | Passes. Frontend: 54 tests, oxlint and Vite build pass | **Verified at the API level.** The UI was not driven in a browser |
| P5 | Human and student validation | `python -m pipeline.review_kit sample / score` (Q2 label review), and the study protocol in §3 | Materials and scorer tested | **Blocked:** it needs people (§3) |

## 2. What the evidence says

1. **The recommendation ranking** is reproducible and unchanged. It beats the keyword baseline on held-out profiles (M7 test: MRR 0.73 against 0.49).
2. **Skill mapping** is the main quality limit. About 64% to 72% of clear phrases map to an acceptable concept, and narrow fixes such as aliases do not generalise. A real improvement needs a different matcher (for example a re-ranker over the top candidates, or context from the rest of the profile), validated on new data.
3. **Uncertainty flags** behave as approved. Recalibrating them with the existing signals (similarity and margin) does not generalise.
4. **Evidence sufficiency** cannot meet its approved targets with graph-derived features. Either a different kind of evidence (for example asking the student about their goals) or a reviewed change to the targets is needed. Weakening the targets is a decision for you, not part of this work.

## 3. Human and student validation (to be run)

### 3.1 Review of the gold labels (Q2)

- **Who:** two reviewers with computing-careers knowledge, such as a careers adviser and a lecturer.
- **What they see:** `python -m pipeline.review_kit sample --out review/` writes:
  - 25 mapping items per (split, label) cell;
  - 20 profiles per (split, sufficiency) cell.

  Reviewers see each item and its gold label, never AjiraGuide output. They mark each label `agree`, `disagree` or `unsure`.
- **Scoring:** `python -m pipeline.review_kit score --sheets review/`.
- **Acceptance (fixed in the code before any review):** the lower bound of the clustered 95% interval of the agreement rate must be at least 0.80. If it fails, the M7 and release results remain provisional, and the disagreements go back through the annotation procedure.

### 3.2 Student study (needs ethics approval, e.g. Strathmore IREC)

- **Participants:** about 30 to 40 IT and computer-science students across years. They give informed consent; their data is pseudonymous and deleted after analysis.
- **Tasks:** enter their own skills, then read their top recommendations, one explanation, the skills gap and the career catalogue.
- **Measures, recorded per student:**
  1. Relevance of their top 3 careers (each rated 1 to 5), compared with an adviser's grades for the same profile.
  2. Explanation understanding: three comprehension questions per explanation.
  3. Whether the uncertainty disclosures were noticed and understood.
  4. System Usability Scale.
  5. Any statement the student read as a promise of job readiness. The target is none.
- **Release criteria (fixed before the study):**
  - mean top-3 relevance ≥ 3.5 with a 95% lower bound ≥ 3.0;
  - comprehension ≥ 80%;
  - SUS ≥ 68;
  - no student reads a job-readiness promise;
  - no participant left at a dead end in the journey.

### 3.3 New held-out data

The M7 test splits are spent, and examples from them appear in the M7 report. A release claim about any changed component needs a new held-out set:

- written and labelled under `pipeline.gold_sets`;
- human-reviewed;
- frozen before any tuning;
- read once.

## 4. Release gates

| Gate | Status |
|---|---|
| Rankings reproducible in production (P0) | Done locally; needs a CI image build and a drift run after a push |
| Ranking invariance (AC1) and API compatibility (AC2) | Pass (M7) |
| Explanations: fidelity, disclosure, readability (AC13) | Pass (M7) |
| False uncertainty within target (AC4) | **Inconclusive** (M7), with no better calibration found |
| Evidence sufficiency shown to students (AC9, AC10) | **Not met.** It stays off |
| Ambiguous and close-candidate detection (AC5, AC6) | **Not assessable** |
| Gold labels reviewed by humans (Q2) | **Open** (§3.1) |
| Student study criteria (§3.2) | **Open** |
| Full journey verified | API over HTTP: pass. Browser walkthrough: **open** |

**What can be offered now, clearly as a pilot under supervision:** the ranking with its explanations and the per-skill uncertainty disclosures, with evidence sufficiency hidden. Calling it student-ready requires the open gates above.

## 5. Upstream-drift investigation (#173)

The drift run on the merged release branch (43412084468) still failed with "upstream drift (ranking changed)".

**What matched the approved baseline:** the base image digest, the model revision and files, and the embedding probe.

**What differed:** `packages_sha256`, 4 categorical ranking differences, and at least 20 float differences beyond 1e-9. The report caps that list at 20, and the values differ by about 1e-8.

**Correction:** the M8 PR description and issue comment said no ranking score changed. That was wrong: I read a field the report does not have, and the floats do differ.

### How the two jobs build their environments

| | PR gate (`invariance-pr`) | Drift job (`upstream-drift`) |
|---|---|---|
| Packages | A fresh virtual environment with exactly the 77 locked packages | The production image: the base image's system Python, plus the lock installed `--no-deps` |
| Embedding cache (`data/cache`, git-ignored) | Computed at run time, after `pin_threads()`, under the portable arithmetic settings | Baked at image build time by `warm_up()`, before this change with default threads and kernels and without `pin_threads()` |
| Comparison | Exact | Pass or fail on the fields in `DRIFT_FIELDS` (base image, package hash, model revision, model files, probe), plus the ranking within 1e-9 |

### Each remaining difference

1. **Ranking: 4 categorical differences and 20 or more float differences.**
   - **Cause: the embedding cache.** The image's cache was computed with different arithmetic from the gate's.
   - **Evidence:** reproduced on one machine with everything else held fixed.
     - The cache built the old way differs from the gate's in every one of its 5,025 vectors, by up to 2.6e-7.
     - Taking the snapshot with each cache in turn gives exactly the drift job's pattern: 4 categorical differences, all near-tied shared names such as "ERP systems" and "Mathematics", with the career order following, plus 20 or more float differences.
     - The drift job's own differences were "ERP systems" and "Selenium", which is the same class.
   - **Fix (this branch):** the image now builds the cache under the gate's settings, with `pin_threads()`, for that build step only. Built that way on this machine, the cache is byte-identical to the one the gate path produces (`74872679…`).
   - **Side effect:** the production image's cached vectors change in their last bits, towards the approved baseline. Ranking logic is unchanged. A few near-tied shared-name readings may resolve to the other owner, as the baseline does.
   - **Not fixed:** the running server still encodes the student's own skills with default arithmetic. This is the M7 C1 limitation: the gate checks code under a fixed numeric regime.
2. **Package hash.**
   - **Evidence:** the build log shows pip installed 74 locked packages and found the other 3 (`packaging==26.3`, `pip==24.0`, `setuptools==79.0.1`) already in the base image at exactly the locked versions. So every locked package is present at its locked version.
   - **Cause:** the remaining difference must be distributions the base image ships that the lock does not list. This is not yet confirmed, because the report recorded only the hash.
   - **Change (this branch):** the drift report now records the image's full inventory and compares it with the baseline's (`only_installed`, `only_baseline`, `version_differs`). It also records both embedding-cache hashes. These are diagnostics only: the pass/fail fields and the 1e-9 tolerance are unchanged.
   - **Next step:** the next drift run will name the extra packages. Whether to remove them from the image or to fingerprint only the locked set is a decision to make once they are known. This branch does neither.

**Status of #173:** open. Its remaining criterion, a drift run with no package drift, needs:

1. this branch merged;
2. a drift run that shows the inventory;
3. the package decision above.

Correction to §1 (P0): the byte-identical local snapshots (`b0f2952e…`) all used the same pre-existing cache, which had been built with default arithmetic. With a freshly built portable cache the local snapshot is `0b352247…`. Snapshots are only comparable when they use the same cache.

## 6. Reproducing

All commands run from `backend/`:

```
python -m pytest                                                     # full backend suite
python -m recommender.calibration --run NAME --joint                 # P1, development
python -m recommender.mapping_eval --run NAME --split validation --tau 0.51 --delta 0.025
python -m recommender.evidence_study --run NAME                      # P2, development
python -m recommender.mapping_eval --run NAME --split development --candidate      # P3
python -m recommender.mapping_eval --run NAME --split validation --candidate
python -m pipeline.review_kit sample --out review/                   # P5
```

From `frontend/`: `npm ci && npm test && npm run lint && npm run build`.

The result folders under `data/results/release-*` hold manifests with the commit and set hashes.
