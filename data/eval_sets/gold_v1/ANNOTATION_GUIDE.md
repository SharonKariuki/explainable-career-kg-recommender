# AjiraGuide gold sets: annotation guide (mapping_v1, students_v1)

Rubrics as approved in the Measured Matching plan (revision 2 §4.2, §6.2; revision 3 R2, R4;
revision 4 §C1, §C2; revision 5 §C6.1). Do not change them while labelling.

## Independence rules (all roles)

- Work only from the files in this folder: `catalogue/` (node catalogue, career list, shared
  names, `search.py`) and the item files you are given.
- Never open, run or query AjiraGuide itself (the `career-recommender`, `wt-*` folders, the API,
  any similarity model or ranking). Never use another annotator's labels. Never guess what the
  system would output; label what a careful human expert would say the student meant.
- `search.py` is a plain word-overlap lookup over the catalogue. It does not rank by meaning.
  Search with several phrasings; judge candidates yourself.

## The catalogue

- `catalogue/skill_nodes.json`: every skill node: `id`, `label`, `type` (tool, knowledge,
  skill/competence, transferable, essential), every `names` entry, and the careers requiring it.
- `catalogue/careers.json`: the 24 careers (O*NET code, title, domain, description).
- `catalogue/shared_names.json`: names (lower-cased) owned by more than one node.
- `catalogue/name_index.tsv`: one line per name.

## A. Mapping labels (mapping_v1 items, and each student input for M8)

For one input phrase, as a student would type it in a "your skills" box:

| Field | Meaning |
|---|---|
| `label` | `unambiguous`: one intended meaning, and at least one node expresses it. `ambiguous`: several clearly different readings are plausible, or none is clearly best. `no_concept`: no node fits the intended meaning (the concept is absent from the catalogue, or the phrase is not a skill). |
| `acceptable` | Every node id that correctly expresses the intended meaning. Several nodes when the concept is split across nodes (e.g. a tool node and a knowledge node for the same thing). For `ambiguous`, list the nodes for each plausible reading. Empty for `no_concept`. |
| `preferred` | The single best node in `acceptable` (null if empty). |
| `shared_owner_marks` | Only when the input text (lower-cased, trimmed) is a key of `shared_names.json`: mark **each** owner `valid` or `not_valid` for the meaning the student intended. Valid owners must also be in `acceptable`. |
| `confidence` | `high` or `low`. |
| `note` | One short reason; required for `ambiguous`, `no_concept` and low confidence. |

Acceptability: list every node a careers adviser would agree expresses what the student
meant. `acceptable` may list several nodes when the concept is split across nodes (revision 1
§6.1: e.g. Cisco and Cisco IOS). The plan's worked example: "routing" → the ICT network routing
node; the `Route` command is a narrower tool, not what the student meant.

Examples: "routing" → the network-routing knowledge node(s) (unambiguous). "TCP/IP" → if no
node expresses the TCP/IP protocol suite itself, `no_concept`. "web pages" → `ambiguous`
(building, designing or browsing). "playing guitar" → `no_concept`.

## B. Sufficiency (students_v1 profiles)

Annotators see only the skill list. Label each profile `sufficient`, `insufficient` or
`borderline`, judging the profile as a whole across its wordings (they are the same skills).

**Sufficient.** A careers adviser reading only these skills could name a small set of career
areas (one to three) with reasonable confidence, **and** the profile contains at least two
*distinct, specific* capabilities that point there. A specific capability is a named tool,
technology, method, domain or task. Examples: "Cisco IOS, OSPF routing, VLANs"; "pandas,
statistics, Power BI". Several plausible careers is **not** a reason for insufficient: a
profile that clearly fits both Network Administrators and Network Support is sufficient.

**Insufficient**, with every reason code that applies:
- I1: only generic skills that most tech careers share (Python, SQL, Excel, "computers", "coding");
- I2: only soft or transferable skills (communication, teamwork, problem solving);
- I3: all inputs restate a single capability ("Python, Python programming, coding in Python");
- I4: most inputs are too vague or ambiguous to interpret ("web pages, networking, analysis");
- I5: a single specific item with nothing to support it ("Solidity").

**Borderline.** You are unsure. Use code **B1** for "specific but spread across areas": the
skills are specific, distinct and clear, but no single career area has two distinct specific
capabilities pointing to it (e.g. one blockchain tool, one security-compliance tool, one
data-engineering tool, one AI library).

Also record `plausible_careers` (codes) and a one-line `note`.

## C. Career relevance grades (students_v1 profiles)

For every profile, grade each of the 24 careers (unlisted = 0), using the career descriptions
and your own knowledge:

| Grade | Meaning |
|---|---|
| 3 | A career this profile was written for: its core daily work uses these skills |
| 2 | A career an adviser would also seriously recommend: substantial overlap in core work |
| 1 | Related: shares tools or domain, but is not a natural target |
| 0 | Unrelated (implicit) |

An insufficient profile may have no grade-3 career; that is a valid answer.

## D. Concept pairs (sensitivity analysis only; revision 3 R2)

For a pair of nodes: `same_capability`, `broader_narrower`, `related_distinct` or `unrelated`.
Granularity rule: two concepts are the *same capability* only if a student who lists one almost
always has the other, **and** an adviser judging the profile would count them once. The plan's
analysis: Git / GitHub are related but distinct tools; Cisco / Cisco IOS and Excel / "use
spreadsheets software" are broader and narrower; Excel / Google Sheets are two products for one
capability; Python / pandas is related but distinct.

## Reliability and adjudication (revision 3 R4, revision 4 §C2)

Two annotators label independently; agreement is computed per split before adjudication.
Freeze conditions: sufficiency 3-class raw agreement ≥ 0.75, 3-class κ ≥ 0.60 and min(κ with
borderline→sufficient, κ with borderline→insufficient) ≥ 0.60; career grades quadratic-weighted
κ ≥ 0.60 and mean grade-3 Jaccard ≥ 0.70 (both empty = 1); mapping class κ ≥ 0.60 and mean
acceptable-set Jaccard ≥ 0.70 on items both call unambiguous. If a condition fails: a dated
rubric amendment, one blind re-label of the disagreed items, and otherwise the label type and
split is not frozen and its metrics are exploratory. The adjudicator resolves disagreements; an
item keeps an adjudicated label only with a confident decision and a reason, otherwise it is
dropped and counted. AjiraGuide output is never used to break a tie, select items or adjust labels.

## Rubric amendment 1 (13 November 2026, after the first agreement check)

Written under the plan's failure procedure (revision 3 R4, step 1) because mapping-class
agreement on student inputs was κ 0.47 (< 0.60). Most disagreements were products or terms
absent from the catalogue that one annotator mapped to a category node and the other called
`no_concept`. It clarifies, and does not replace, section A:

1. **Instance of a category node → `unambiguous`.** When the input names a specific product,
   framework or standard that the catalogue lacks, but a node is a category that clearly
   contains it (the input is an instance of that category), that category node is acceptable
   and the item is `unambiguous`: "FortiGate" → Firewall software; "Nginx" → Web server
   software; "Gatsby" → JavaScript framework software. Use confidence `low` if containment is
   arguable.
2. **Only a different, narrower or merely related node → `no_concept`.** If the nearest nodes
   are a different product, a narrower tool or command, or a related but different concept, no
   node expresses the meaning: "TCP/IP" (only ipconfig/netstat-type tools) → `no_concept`.
3. **Content-free phrases → `no_concept`.** "tech stuff", "IT things", "computer stuff" carry no
   interpretable capability.
4. **Two or more concrete readings → `ambiguous`.** "networking", "design", "testing", "web
   pages": list the nodes for each reading.
5. **Soft skills and traits.** A soft skill that a node names (communication, teamwork, problem
   solving, critical thinking, time management) is `unambiguous` to that node. A personal trait
   or attitude no node names (hardworking, honest, passionate, God-fearing) is `no_concept`.
