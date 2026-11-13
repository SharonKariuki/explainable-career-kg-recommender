# Adjudicator brief

You are the third, independent adjudicator. Read ANNOTATION_GUIDE.md and ANNOTATOR_BRIEF.md in
this folder; the rubric is unchanged. Each task in your adjudication package shows the task
(profile wordings, or a mapping input) and two independent annotations, `annotation_1` and
`annotation_2`, in no particular order. Decide the correct final label under the rubric. You may
agree with either, combine them, or decide differently; use catalogue/search.py and --node as
needed. Never open or run AjiraGuide, and never open authored/ (author intent) or assembled.json.

Output one record per task, same ids, in the annotator output format for that task type, plus:
- "confidence": "high" only if you are confident of the decision under the rubric; otherwise "low"
  (low-confidence items are dropped from the gold set and counted, per plan revision 3 R4 step 4);
- "note": one line with the reason for your decision (required).
Validate node ids and career codes with a Python check before finishing, and report counts.
