# Label review approval form (Q2)

**Approval cannot be recorded until scoring is complete.** Do not sign, date or tick any decision below before `python -m pipeline.review_kit score --sheets review/` has been run on the completed sheets and the results are entered here. This form is blank. No review has been run and no approval exists.

## 1. Review details

| Item | Value |
|---|---|
| Supervisor / approver | [Approver name and role] |
| Reviewer 1 | [Reviewer 1] |
| Reviewer 2 | [Reviewer 2] |
| Adjudicator | [Adjudicator] |
| Sampling seed and code commit | [seed and commit hash] |
| Date scoring was run | [date] |

## 2. Sample sizes

| Sheet | Items sampled | Decided (agree or disagree) | Unsure |
|---|---|---|---|
| Mapping labels | [n] | [n] | [n] |
| Profile sufficiency | [n] | [n] | [n] |
| Profile career grades | [n] | [n] | [n] |

Items dropped after adjudication (low confidence), counted: [n]

## 3. Scored outcome

Acceptance level (fixed): lower bound of the clustered 95% interval of the agreement rate is at least 0.80.

| Set | Agreement | 95% lower | 95% upper | Outcome from scorer |
|---|---|---|---|---|
| Mapping labels | [ ] | [ ] | [ ] | [ ] |
| Profile sufficiency | [ ] | [ ] | [ ] | [ ] |
| Profile career grades | [ ] | [ ] | [ ] | [ ] |

Scorer output file or log attached: [path]

## 4. Decision (tick one, only after section 3 is complete)

- [ ] Approved: all three sets meet the acceptance level.
- [ ] Approved with changes: [list changes, items to re-annotate, and who does them]
- [ ] Not approved: results stay provisional; disagreed items are re-annotated.

Conditions or comments: [text]

## 5. Sign-off

| Role | Name | Signature | Date |
|---|---|---|---|
| Supervisor / approver | [name] | [signature] | [date] |
| Coordinator | [name] | [signature] | [date] |
