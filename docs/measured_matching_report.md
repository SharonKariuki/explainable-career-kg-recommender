# Measured Matching (M7): final report

**Date:** 13 November 2026. **Milestone:** M7 · Measured Matching. **Issues:** #157 (C1) to #162 (C6).

**Specification:** the Measured Matching plan, revision 6, with revisions 2 to 5 as amended. Its decision record is kept with the plan.

**Status: provisional.** Every gold label was produced by AI annotators. A human has not yet reviewed them (decision Q2), so the results below stand until that review is done.

## 1. What Measured Matching adds

Measured Matching keeps three things apart:

- **How a career ranks.** The ranking itself is unchanged.
- **How confidently each skill was read.** This is mapping confidence.
- **Whether the profile gives enough evidence to judge fit.** This is evidence sufficiency.

| Phase | PR | What it added |
|---|---|---|
| C1 | #163, #167 | Ranking-invariance snapshot and its approval. PR invariance gate, weekly upstream-drift job, evaluation statistics and runners |
| C2 | #168 | Each skill reading reports its runner-up, the margin to it, the other owners of a shared name (aliases included), `uncertain` and its reasons. These are added to the API |
| C3 | #169 | The `mapping_v1` and `students_v1` gold sets, frozen. The full annotation record, agreement statistics and δ calibration |
| C4 | #170 | The evidence-sufficiency rule on the full ranking. `insufficient` and `evidence` in the API, with calibrated thresholds |
| C5 | #171 | Explanation disclosures: uncertain readings, shared names, near ties, and the insufficient-evidence wording (behind a setting) |
| C6 | this PR | The single test read, this report, and the AC3/AC11 acceptance tests |

## 2. Data

| Set | sha256 | Validation | Test |
|---|---|---|---|
| `mapping_v1.json` | `94f1bd30…638d6c` | 399 items (274 unambiguous, 31 ambiguous, 94 no-concept) | 404 items (278, 29, 97) |
| `students_v1.json` | `49d0f88e…7082a` | 266 profiles (135 sufficient, 118 insufficient, 13 borderline) | 260 profiles (133, 113, 14) |

Development holds 224 mapping items and 149 profiles. The authoring, splits, annotation, agreement and adjudication are described in `docs/evaluation_protocol.md` and recorded in `data/eval_sets/gold_v1/`.

Agreement met every freeze condition:

- sufficiency κ: 0.95 to 0.97;
- grade κ (quadratic): 0.92 to 0.93;
- mapping κ: 0.72 to 0.82;
- student-input κ: 0.78, after one rubric amendment and a blind re-label.

## 3. Calibration (development only)

- **δ (close-runner-up margin):** no δ keeps false uncertainty within both targets. M6 on development C\* is already 0.1575 at δ = 0, so `close_runner_up` stays off.
- **`narrow_concept`:** off. No detector exists for it in Phase 1.
- **Evidence thresholds:** `w_min 1.5891, cap 3.2, W_min 3.5, G_min 2, ε 0.02`. No setting within the plan's constraints met the targets on development: false insufficient was at least 0.97.

## 4. Acceptance criteria

Outcomes follow the C3 rule:

- **Pass:** the whole 95% interval meets the target.
- **Fail:** the whole interval misses it.
- **Inconclusive:** the interval crosses the target.
- **Not assessable:** an effective n below 60 or fewer than 30 clusters.

Gate figures are from the single test read (`data/results/m7-final-test`). Validation figures are from the single validation reads.

| # | Criterion | Validation | Test | Outcome |
|---|---|---|---|---|
| AC1 | Ranking invariance | — | Snapshot identical on every PR (#168 to #171) and on `main` after each merge | **Pass** |
| AC2 | API compatibility | — | Existing keys, types and values unchanged; new keys are additive (contract tests) | **Pass** |
| AC3 | Shared names, including aliases | — | Every shared name and the 4 alias collisions carry `shared_name`; selection unchanged | **Pass** |
| AC4 | False uncertainty, M6-clean-excl (U ≤ 0.05) | 0.000 (U 0.010), synthetic validation | — | **Pass** |
| AC4 | False uncertainty, M6 on C\* (U ≤ 0.15) | 0.140 (0.094 to 0.205) | 0.180 (0.132 to 0.239) | **Inconclusive** |
| AC5 | Close-candidate detection (L ≥ 0.70) | — | `close_runner_up` is off, so the population is undefined | **Not assessable** |
| AC6 | Ambiguous detection, M3 (L ≥ 0.50) | 4/31 | 8/29 (n_eff 26) | **Not assessable**: only about 30 items per split were labelled ambiguous |
| AC9 | Insufficient recall (L ≥ 0.80) | 1.000 (0.984 to 1.000) | 1.000 (0.983 to 1.000) | **Pass** |
| AC10 | False insufficient (U ≤ 0.10) | 0.963 (0.923 to 0.983) | 0.940 (0.890 to 0.968) | **Fail** |
| AC11 | Evidence independence of `top`, detail view and repeats | — | Identical | **Pass** |
| AC12 | E1 to E11, fixture and calibrated thresholds; E9 invariance | — | All pass | **Pass** |
| AC13 | Explanations | — | Fidelity 100%; C4 disclosure 100%; no fit label when insufficient (when enabled); mean grade 9.9 | **Pass** |
| AC14 | Annotation reliability | — | Every frozen split meets its condition (student inputs after the re-label) | **Met** (AI annotators) |
| AC17 | CI coverage and drift | — | The PR gate runs on every recommender, data or image change. The drift job was run manually; see §7 | See §7 |
| AC18 | Mixed profiles: E10 and E11 | — | Pass in AC12 | **Pass** |

Report-only results on the test split:

| # | Measure | Result |
|---|---|---|
| AC4b, AC7 | No-concept detection (M4) | Recall 0.92 (0.83 to 0.96); precision 0.48; false-positive rate on C\* 0.18; high-similarity no-concept 0.08 |
| AC8 | Confidently incorrect (M7) | Primary 0.111 (0.083 to 0.148), against 0.116 for the behaviour before Measured Matching; conditional 0.24. 30 clear-winner errors are listed in `mapping_readings.csv` |
| — | Mapping accuracy | M1 exact concept 0.72 (0.66 to 0.77); M2 top two 0.79; wrong-mapping recall (M5) 0.62 |
| AC8b | Evidence contamination (M8) | M8a 3.1% (1.9% to 4.9%); M8b decision flips 0.2%; M8c 16 wrong but meaningful |
| AC15 | Grouping sensitivity (exploratory) | 23 approved groups; 0% of decisions change; agreement with humans 0.49 either way |
| AC16 | Careers: full engine against keyword baseline | P@1 0.40 against 0.20; Recall@3 0.53 against 0.32; MRR 0.73 against 0.49; nDCG@5 0.62 against 0.35. Wording agreement 0.56. By family (exploratory): MRR from 0.58 (user support) to 0.87 (networking) |
| AC18 | Mixed-profile subgroup, human sufficient | Flagged insufficient in 78% (counts only) |

## 5. Compared with the C1 baseline

Rankings, scores, the skills gap and proximity paths are identical to the approved C1 baseline. The invariance gate confirms this on every PR.

What changed is information added beside the ranking:

- **Per-skill readings:** with `close_runner_up` off, the matcher flags readings below the similarity threshold, as before, and now also shared names.
- **Evidence:** the evidence assessment is new.
- **Explanations:** explanations now disclose uncertain readings and near ties.

Against the behaviour before Measured Matching, confidently incorrect readings fall only slightly, from 0.116 to 0.111 of test items. The new shared-name flag accounts for the difference.

## 6. Findings

1. **The evidence rule cannot separate real profiles.** It finds every insufficient profile, but it also marks 94% of human-sufficient test profiles insufficient.
   - **Cause:** the plan's constraint `w_min > ln(24)/2` counts only rare skills that are core to their career as meaningful. The specific skills students actually list (Cisco IOS, Wireshark, pandas, CSS, Selenium) weigh 0.1 to 1.2.
   - **What was done:** the rule is kept as approved. The insufficient wording stays off in explanations (`EXPLAIN_INSUFFICIENT_EVIDENCE=false`) so students are not misinformed. `insufficient` and `evidence` are still reported in the API.
2. **The close-runner-up flag cannot be calibrated under the current targets.** Existing flags already exceed the false-uncertainty budget on correct readings.
   - **Cause:** the low-similarity threshold and shared-name flags. Of the 35 test flags on correct readings, 3 are unjustified shared-name warnings.
3. **Ambiguous phrasing is rare once annotated.** Annotators judged most phrases written to be ambiguous as unambiguous, so ambiguous-input detection could not be assessed.
4. **Mapping quality is moderate.**
   - **Accuracy:** 72% of unambiguous test phrases map to an acceptable concept.
   - **Unflagged errors:** 30 wrong readings are clear winners that no flag can catch, for example "T-SQL" read as Microsoft SQL Server and "DSA" read as signal processing.

## 7. CI

- **PR job (AC17a):** `invariance-pr` passed on every M7 PR and on `main` after each merge.
- **Drift job (AC17b):** run manually on `main` (`upstream-drift`, runs 43400955788 and 43400964745). Its results are recorded in the PR for this report. Until it runs, AC17b is assessed only by its unit tests and the configuration review.

## 8. Limitations

- **AI annotation.** Two AI annotators and an AI adjudicator produced every gold label. They may share biases, so agreement may overstate human reliability. Their temporary scratch area was shared, and blinding rests on their own reports. Human review (Q2) is outstanding.
- **Annotation coverage.** The authored profiles were written to be clearly sufficient or clearly insufficient, which inflates agreement and makes the sufficiency gates easier than real data would.
- **Test environment.** The test read ran on the development machine (Windows, portable arithmetic). The CI gate environment differs in the last bits of floating point. Rankings were verified identical there separately (AC1).
- **No AC5 or AC6 evidence.** Close-candidate detection and ambiguous-input detection were not tested.
- **Repeated final read.** The final test read was run twice: the second run added report-only outputs (families, keyword baseline, grouping). Every gate figure was identical; no threshold was changed after either run.

## 9. Readiness for student-facing use

- **Safe to ship:** the ranking (unchanged and verified) and the per-skill uncertainty disclosures. These are additive, and their wording passes fidelity and readability checks.
- **Not ready:** evidence sufficiency. It must not be shown to students, and it stays switched off in explanations. The `insufficient` field should not be surfaced in the UI until the rule passes AC10 on held-out data.
- **No job-readiness claims.** The system makes none, and a test checks that.

## 10. Recommended next steps (each a separate decision)

1. **Revise the evidence rule.** For example, base it on requirement-weighted support within one career rather than the IDF floor. Validate it on fresh development data, then a new held-out split.
2. **Reduce false uncertainty on correct readings.** Revisit the 0.60 similarity threshold, and break shared-name ties deterministically (the C1 decision deferred to after Phase 1). Then re-run δ calibration.
3. **Human review of the gold labels (Q2)**, and a larger ambiguous-input set if AC6 is still wanted.
4. **Pin the model revision and base image in production (Q18).**

## 11. Reproducing

All commands run from `backend/`, with the portable-arithmetic environment described in `backend/tests/snapshots/README.md` for the invariance check.

```
python -m pipeline.gold_sets build                              # rebuild both gold sets; hashes match FROZEN
python -m pipeline.gold_sets agreement                          # agreement.json
python -m recommender.calibration --run c3-delta-calibration    # δ on development
python -m recommender.mapping_eval --run c3-mapping-validation --split validation
python -m recommender.evidence_calibration --run c4-evidence-calibration
python -m recommender.student_report --run c4-students-validation --split validation
python -m recommender.explanation_quality --run c5-explanation-quality
python -m recommender.evaluate --run m7-final-test --measured-matching   # test read; needs a clean tree
python -m recommender.invariance check --baseline tests/snapshots
```

**Provenance:**

- Every result folder's `manifest.json` records its git commit, set hashes and configuration.
- The final test read ran at commit `820e967` (C6 branch, from `main` at `1fbfc68`).
- The model is `all-MiniLM-L6-v2` at revision `1110a243`.
