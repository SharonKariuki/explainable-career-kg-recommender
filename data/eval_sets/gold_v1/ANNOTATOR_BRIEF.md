# Annotator brief

You are one of two independent annotators (or the adjudicator) for AjiraGuide's gold
evaluation sets. Read ANNOTATION_GUIDE.md in this folder first; it is the rubric. The
independence rules there are strict: work only in C:\Users\sharo\Ajira-ai\m7_annotation, never
open or run AjiraGuide or anything in career-recommender or wt-* folders, and never open the
other annotator's folder, the `authored/` folder (author intent) or `adjudicated/` unless you
are told you are the adjudicator.

Tools: `python3 catalogue/search.py -n 10 "phrase one" "phrase two" ...` (word-overlap lookup;
search with several phrasings, batch many queries per call, and keep -n small to save space);
`python3 catalogue/search.py --node <id>` for a node's full record. Python 3 for checks.

Write your output as a JSON array to the path you are given, one record per task, same ids,
nothing skipped. Validate before finishing: every node id you use must exist in
catalogue/skill_nodes.json and every career code in catalogue/careers.json; write a short Python
check and run it. End with a short report (counts per label, anything uncertain).

## Mapping tasks (`mapping_*`, `inputs_*` packages)

Each task: `id`, `input`, and sometimes `shared_name_owners` (the input text is a name owned by
several nodes). Output per task:

    {"id": "m-0001", "label": "unambiguous"|"ambiguous"|"no_concept",
     "acceptable": ["<node id>", ...], "preferred": "<node id>"|null,
     "shared_owner_marks": {"<owner id>": "valid"|"not_valid", ...},   // only when owners were given; mark every owner
     "confidence": "high"|"low", "note": "short reason"}

Valid owners must be in `acceptable`. `acceptable` is empty and `preferred` null for no_concept.
Judge the phrase as a student would mean it in a skills box of a computing career tool.

## Profile tasks (`profiles_*` packages)

Each task: `id` and `wordings` (two or more phrasings of the same student's skills). Output:

    {"id": "s-0001", "sufficiency": "sufficient"|"insufficient"|"borderline",
     "reasons": ["I1", ...],            // codes I1-I5 for insufficient, ["B1"] for spread-across-areas borderline, else []
     "grades": {"<career code>": 1|2|3, ...},   // omit grade-0 careers
     "plausible_careers": ["<career code>", ...],
     "confidence": "high"|"low", "note": "one line"}

## Concept-pair tasks (`pairs_*` packages)

Each task: `pair`, `a`, `a_label`, `b`, `b_label`. Look nodes up with `--node`. Output:

    {"pair": "cp-001", "relationship": "same_capability"|"broader_narrower"|"related_distinct"|"unrelated",
     "note": "short reason"}
