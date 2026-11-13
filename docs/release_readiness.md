# Student-ready release: plan, evidence and status

**Branch:** `feat/release-readiness`, from `main` at `9403ea0`. It has local commits only.

**Status: AjiraGuide is not ready for student-facing release.** §4 lists the gates that are still open. Nothing here changes the approved Measured Matching (M7) protocol, its targets or its locked test results. The M7 test splits were read once, and they are not used again.

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

## 5. Reproducing

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
