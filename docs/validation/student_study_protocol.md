# AjiraGuide student study protocol

Status: draft, not approved, not run. Expands `docs/release_readiness.md` section 3.2. The release criteria in section 9 are copied from there and are fixed before the study. They must not be changed after any data is seen.

Principal investigator: [Principal investigator]. Supervisor: [Supervisor]. Version and date: [version, date].

## 1. Aims

1. Find out whether the top careers AjiraGuide recommends are relevant to students' own skills, compared with a careers adviser's grades for the same profile.
2. Find out whether students understand the explanations and the uncertainty notes.
3. Measure usability (System Usability Scale).
4. Check that no statement reads as a promise of job readiness, and that no student is left at a dead end in the journey.

This is a validation of a guidance tool, not a test of the students.

## 2. Ethics approval

The study must be approved by the Strathmore University Institutional Research Ethics Committee (IREC), or an equivalent committee, before it starts. No recruitment, session or data collection happens before written approval. Approval reference: [IREC approval number and date]. Any change to this protocol, the consent form or the information sheet goes back to the committee first. Research permit requirements, if any: [check with the committee].

## 3. Eligibility

Include: current IT or computer-science undergraduates of [institution], any year, aged 18 or over, able to give consent and to use the app in English.

Exclude: anyone who helped build or label AjiraGuide, and anyone who has already used it in this study.

Aim for a spread across years of study [and gender, if the committee agrees to record it].

## 4. Recruitment

- Open invitation by notice or class announcement, with the information sheet attached.
- Participation is voluntary. No marks, grades, credit, course access or other advantage or penalty depends on taking part or declining. Small refreshments or a transport allowance may be offered only if the committee approves, equally to all.
- Students must not be recruited by their own lecturer where grades could be influenced. Use the researcher, a student leader, or a lecturer who does not teach or grade them.
- Students may decline without giving a reason.

## 5. Sample size rationale

Target 30 to 40 participants. This is a pragmatic size for a usability and relevance study: with about 3 ratings per student the mean top-3 relevance and its 95% interval can be estimated, with the interval clustered by student because ratings from one student are not independent. It is enough to detect gross problems (confusing explanations, dead ends) but not small differences between subgroups. Stopping rule: [stop at 40, or earlier if 30 are complete and the committee agrees]. Recruitment is not extended to reach a threshold.

## 6. Procedure

Individual session, about 40 minutes, with one facilitator, using `study_session_script.md`.

1. Welcome, information sheet, consent (about 5 min).
2. Enter their own skills in AjiraGuide (about 5 min).
3. Review the top recommendations and rate the top 3 careers (about 8 min).
4. Read one explanation and answer three comprehension questions; answer the uncertainty-note questions (about 8 min).
5. Inspect the skills gap, browse the career catalogue, view history (about 7 min).
6. SUS and the open question on job readiness (about 5 min).
7. Debrief. The student may delete their account or data at the end if they choose, and the facilitator shows how (about 2 min).

The facilitator does not explain or defend the tool during tasks, and records any point where the student is stuck or cannot go on (a dead end).

Adviser grading: an adviser ([Adviser]) who has not seen AjiraGuide output grades each participant's skill list for the same careers (0 to 3 scale as in the annotation guide section C), from the skills only, blind to the tool's ranking. The adviser sees only the pseudonymous ID and the skill list.

## 7. Measures

Recorded per participant (see `study_results_template.csv`):

1. Relevance of each of the top 3 careers, rated 1 to 5, and the adviser's grade for the same profile.
2. Explanation understanding: three comprehension questions per explanation read; scored correct or not by a key written before the study.
3. Whether the uncertainty notes were noticed and whether they were understood.
4. System Usability Scale (10 items, standard scoring, 0 to 100).
5. An open question on whether anything read as a promise of job readiness (quote recorded verbatim). Two people code each answer; any disagreement is resolved by the supervisor.
6. Dead ends: any point where the participant could not continue without help.

## 8. Data handling

- Each participant gets a pseudonymous ID (for example P01). The link between ID and name, if one is kept at all (for example the signed consent form), is stored separately from responses, on [secure location], accessible only to [named people].
- No names, student numbers or contact details are stored with responses or in the results file.
- The study account in AjiraGuide uses a study email that carries no personal identifier [method to be set]. Participants may delete the account or their data at the end of the session.
- Storage location for responses: [storage location placeholder]. Encrypted, access limited to the research team.
- Retention and deletion: raw responses and consent forms are deleted [N] months after analysis is complete and by [date], as the committee requires. Only anonymous aggregate results are kept in the report.
- Withdrawal: a participant may withdraw at any time without penalty; their data is deleted on request up to [date] when the data are aggregated.
- Compliance with the Kenya Data Protection Act, 2019 and the committee's conditions: [confirm].

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Students over-trust the recommendations | The debrief states the tool is guidance, not a placement or job promise; it can be wrong; talk to a careers adviser |
| Feeling judged on their skills | Stress it tests the tool; no marks; skills lists are not shared with staff |
| Pressure to take part | Recruitment rules in section 4; consent confirms voluntariness |
| Privacy of skills data | Pseudonymous IDs, secure storage, deletion plan |
| Distress about career prospects | Debrief with careers-service contact [contact] |
| Tool failure during session | Facilitator notes it, session can stop at any time |

## 10. Analysis plan and release criteria

Pre-registered thresholds (copied from `docs/release_readiness.md` section 3.2; fixed before the study):

- mean top-3 relevance ≥ 3.5 with a 95% lower bound ≥ 3.0;
- comprehension ≥ 80%;
- SUS ≥ 68;
- no student reads a job-readiness promise;
- no participant left at a dead end in the journey.

Analysis:

- Relevance: mean of the 1 to 5 ratings over the top 3 careers, 95% interval clustered by student. Also report agreement with the adviser's grades (for example mean rating by adviser grade) as supporting evidence, not as a threshold.
- Comprehension: share of correct answers over all questions, reported with an interval clustered by student.
- SUS: mean score with its interval; also report the distribution.
- Uncertainty notes: share of participants who noticed and who understood; reported, with no release threshold.
- Job readiness: count of participants whose answer, coded by two people, shows a promise read. The target is zero.
- Dead ends: count and description.
- No thresholds are changed, and no participants are dropped, after data is seen. Missing data is reported.

## 11. What blocks release

Release as "student-ready" is blocked if any one of these is true:

- any criterion in section 10 is not met;
- the study did not receive ethics approval before it started, or deviated from the approved protocol;
- fewer than 30 participants completed it;
- the label review (Q2) is not approved;
- the other open gates in `docs/release_readiness.md` section 4 remain open.

A failed result is reported as it is. The tool may then be offered only as a supervised pilot, as stated in that document, until the cause is fixed and the study repeated.
