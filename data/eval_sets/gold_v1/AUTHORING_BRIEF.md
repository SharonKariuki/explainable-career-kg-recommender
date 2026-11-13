# Authoring brief (shared by every author)

You are writing evaluation inputs for AjiraGuide, a career recommender for university students
in Kenya (e.g. Strathmore University IT and computer science students) that maps typed skills to a
catalogue of 2,030 skill nodes and ranks 24 computing careers.

Rules:
- Work only in C:\Users\sharo\Ajira-ai\m7_annotation. Read ANNOTATION_GUIDE.md and the files in
  catalogue/. Never open, run or query AjiraGuide (career-recommender, wt-* folders, any API,
  similarity model or ranking) and do not guess what it would output. Do not open other authors'
  or annotators' files.
- Write the way real students type into a "your skills" box: short phrases, mixed case,
  abbreviations, spelling slips occasionally, local context (MS Excel, Packet Tracer, M-Pesa/Daraja
  API, attachment/internship work), CV-style and casual styles. Vary wording; avoid copying
  catalogue labels except where your category requires it. No two items with the same text.
- Your intended category or label is a design note only; independent annotators assign the gold
  labels later. Be honest in `author_note` about what you meant.
- Python 3 is available as `python3`; `python3 catalogue/search.py "phrase"` finds catalogue nodes
  by word overlap.
- Write valid UTF-8 JSON arrays, in files of at most 120 records, named as your task says. Validate
  each file with `python3 -c "import json,sys;json.load(open(sys.argv[1],encoding='utf-8'))" FILE`.
- Finish with a short report: files written, counts per category/family/code, and anything you
  could not meet.
