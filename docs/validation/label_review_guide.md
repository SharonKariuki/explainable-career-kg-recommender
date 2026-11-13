# Label review guide (Q2): two independent human reviewers

This guide covers the human review of the AI-produced gold labels (mapping items and student profiles). Status: not yet run. No result exists.

## 1. Who qualifies

Two reviewers, each with computing-careers knowledge, for example a careers adviser and a lecturer. Each reviewer must be:

- able to judge what a Kenyan IT or computer-science student means by a skills phrase;
- not involved in writing or labelling the gold sets, and not a developer of AjiraGuide;
- willing to follow the independence rules in section 3.

A third reviewer (the adjudicator) has the same qualifications and is also independent of the first two. Names are recorded in the approval form, not here: reviewer 1 [Reviewer 1], reviewer 2 [Reviewer 2], adjudicator [Adjudicator].

## 2. Generating the sheets

From `backend/`, once, by the study coordinator [Coordinator]:

```
python -m pipeline.review_kit sample --out review/
```

This writes two sheets (seeded, so the sample is reproducible):

- `mapping_review.csv`: up to 25 items per (split, label) cell.
- `profile_review.csv`: up to 20 profiles per (split, sufficiency) cell.

Make one copy of the `review/` folder per reviewer and give each reviewer only their own copy. Do not generate a new sample after any review has started.

## 3. Independence rules

- Use only the sheet, `data/eval_sets/gold_v1/ANNOTATION_GUIDE.md` and the catalogue files in `data/eval_sets/gold_v1/catalogue/`.
- Never open, run or query AjiraGuide, its API, any similarity model or ranking. Never guess what the system would output.
- Do not confer with the other reviewer, and do not look at their sheet, until both have finished and submitted.
- Judge as a careful human expert would. The gold label is shown to you; you judge whether it is correct.

## 4. How to mark

Fill the verdict columns with exactly one of `agree`, `disagree` or `unsure`. Enter your name or code in `reviewer`. Add a short `comment` for every `disagree` and `unsure`. Any other value makes scoring fail.

Mapping sheet (`verdict`): apply section A of the annotation guide and Rubric amendment 1.

- `agree`: the gold label and the acceptable nodes are what a careers adviser would give (unambiguous, ambiguous or no_concept; the listed acceptable nodes are right).
- `disagree`: the label class is wrong, or the acceptable set is wrong.
- `unsure`: you cannot decide even after searching the catalogue with several phrasings.

Profile sheet:

- `sufficiency_verdict`: apply section B (sufficient, insufficient, borderline and the reason codes) to the skill list only.
- `grades_verdict`: apply section C. Agree if the listed grade-3 careers are the ones the profile was written for and no clear grade-3 career is missing.

Use `unsure` honestly. Unsure items are excluded from the agreement rate but are counted.

## 5. Submitting

Save the CSV (UTF-8, same file names) and return the whole folder to [Coordinator] by [agreed secure channel]. Do not edit other columns. Do not return partial sheets unless the coordinator agrees.

## 6. Tracking and adjudicating disagreements

When both sheets are in, the coordinator compares them item by item and records every item where the two verdicts differ in `adjudication_log_template.csv` (copy it to `review/adjudication_log.csv`). `disagreement_type` names the kind (for example label class, acceptable set, sufficiency, career grades, or one reviewer unsure).

- The adjudicator (third reviewer) sees the item, the gold label and both comments, never AjiraGuide output.
- The adjudicator records `decision`, `confidence` (high or low), a `reason` and the `date`.
- An item keeps an adjudicated label only with a confident decision and a reason. Low-confidence decisions are dropped from that label set and counted, and the count is reported.
- AjiraGuide output is never used to break a tie, select items or adjust labels.

## 7. Scoring

When all sheets are complete:

```
python -m pipeline.review_kit score --sheets review/
```

The scorer reports, for mapping labels, profile sufficiency and profile career grades: decided items, unsure items, the agreement rate, a clustered 95% interval (Kish-Wilson, clustered by mapping group or by profile) and an outcome.

Acceptance level (fixed in the code before any review, not to be changed): the lower bound of the 95% interval must be at least 0.80 for each of the three reported sets.

Run the scorer on each reviewer's sheets, and on the sheets after adjudication, and report all runs. Do not change the acceptance level after seeing results.

## 8. If scoring fails

- The M7 and release results stay provisional. Do not describe the labels as human-approved.
- Items the reviewers disagreed on go back through the annotation procedure (a dated rubric amendment if needed, then a blind re-label), as in the annotation guide.
- Report the failure as it is, with the numbers.

## 9. Approval

The supervisor completes `label_review_approval_form.md` only after scoring is complete.
