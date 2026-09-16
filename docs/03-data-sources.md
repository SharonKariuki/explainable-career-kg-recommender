# 03. Data Sources

This document records every external data file the system uses: where it comes
from, its licence, its real filename and columns, how many rows were observed,
and which component consumes it. All figures were read from the files
downloaded on 16 September 2026, not taken from older documentation.

Raw files live in `data/raw/` and are never committed. Run
`python scripts/download_data.py` to fetch and verify them, then
`python scripts/prepare_data.py` to produce the cleaned files in
`data/processed/`. The expected filenames and columns are defined once in
`scripts/data_manifest.py`, which both the download script and
`tests/test_data_integrity.py` use.

## 1. Summary

| Source | Version | Download URL | Size | SHA-256 (zip or file) |
|---|---|---|---|---|
| O*NET Database, text format | 31.0 (August 2026) | https://www.onetcenter.org/dl_files/database/db_31_0_text.zip | 13,183,034 bytes | `6883548adf5fde64cf6f801b35d15519c9225f2732c3cab0e281c652d16b23a9` |
| ESCO classification, English, CSV | v1.1.0 | https://ec.europa.eu/esco/download/ESCO%20dataset%20-%20v1.1.0%20-%20classification%20-%20en%20-%20csv.zip | 7,472,561 bytes | `3b2ed440310d85edda9594773abbf113246eb11d07de83393879b3f167e5e45a` |
| ESCO-O*NET occupation crosswalk | Version 1, September 2022 | https://esco.ec.europa.eu/system/files/2023-08/ONET_%28Occupations%29_0_updated.csv | 2,986,823 bytes | `82179a0a3340da97b63df90134d8d941ec3c2c478334d855b69e4dd57a91b620` |

The download script records these values, with the retrieval time, in
`data/raw/download_manifest.json`. A clean end-to-end download on 16 September
2026 produced files byte-identical to an earlier manual download.

## 2. Licences and attribution

### O*NET

The O*NET 31.0 Database is released under the Creative Commons Attribution 4.0
International licence (CC BY 4.0). Source: https://www.onetcenter.org/license_db.html

Required attribution, to appear in the application and the final report:

> This page includes information from the O*NET 31.0 Database by the U.S.
> Department of Labor, Employment and Training Administration (USDOL/ETA).
> Used under the CC BY 4.0 license.

Because this project filters and reshapes the data, the following must also be
stated:

> Users have modified all or some of this information, and the USDOL/ETA has
> not approved, endorsed, or tested these modifications.

O*NET is a trademark of USDOL/ETA. It should be used as an adjective ("O*NET
data", "the O*NET database"), not as a noun, verb, plural or possessive.

### ESCO and the crosswalk

Under Commission Decision 2011/833/EU on the reuse of Commission documents, the
ESCO classification can be downloaded, used, reproduced and reused free of
charge. Conditions: use must be acknowledged, and modified versions must be
marked as modified. Source: https://esco.ec.europa.eu/en/about-esco/faq

Required acknowledgement:

> This service uses the ESCO classification of the European Commission.

(Use "This publication uses the ESCO classification of the European
Commission." in the written report.) The crosswalk was published by the ESCO
Secretariat in collaboration with USDOL/ETA and is reused on the same terms.
Technical report:
https://esco.ec.europa.eu/en/about-esco/publications/publication/crosswalk-between-esco-and-onet-technical-report

## 3. How the files were obtained

**O*NET.** The download page (https://www.onetcenter.org/database.html) links
only the Excel, JSON-LD, SQL and RDF zips. The tab-delimited text zip is served
at the conventional URL above, which returned HTTP 200. The text format was
chosen because it parses without extra dependencies.

**ESCO.** The ESCO download page builds a package through a multi-step web
form. The form's confirmation page links the package at a stable URL of the
form `https://ec.europa.eu/esco/download/ESCO dataset - <version> - classification - <lang> - <format>.zip`.
The English CSV package for v1.1.0 is fetched from that URL directly. If the
URL stops working, `download_data.py` prints these manual steps:

1. Open https://esco.ec.europa.eu/en/use-esco/download
2. Choose version ESCO v1.1.0, content "classification", language "en", type "csv".
3. Add to the package and download the zip.
4. Save it as `data/raw/esco/ESCO_dataset_v1.1.0_classification_en_csv.zip` and
   extract it into `data/raw/esco/ESCO_v1.1.0/`.

**Crosswalk.** Linked from https://esco.ec.europa.eu/en/use-esco/other-crosswalks.
Manual fallback: download "ONET_(Occupations)_0_updated.csv" from that page and
save it as `data/raw/esco/ONET_Occupations_0_updated.csv`.

**Why ESCO v1.1.0 and not the newest release (v1.2.1).** The crosswalk metadata
states that it maps O*NET-SOC 2019 to ESCO v1.1.0. Using the same ESCO release
guarantees that every ESCO URI in the crosswalk resolves. This was verified:
all 102 in-scope ESCO occupation URIs are present in `occupations_en.csv`.

## 4. O*NET 31.0 files used

Location: `data/raw/onet/db_31_0_text/`. All files are tab-delimited UTF-8 with
CRLF line endings and one header row. Row counts exclude the header.

**Change from older O*NET releases.** O*NET 31.0 no longer ships `Skills.txt` or
`Technology Skills.txt`. The 35 skill descriptors are now split across
`Essential Skills.txt` (the 10 basic skills, element IDs `2.A.*`) and
`Transferable Skills.txt` (the 25 cross-functional skills, element IDs
`2.B.*`). The O*NET 31.0 data dictionary confirms that "Technology Skills" was
renamed "Software Skills", and that its columns "Example", "Commodity Code" and
"Commodity Title" were renamed "Workplace Example", "Element ID" and "Element
Name". The text version of Software Skills has no Title column, although the
Excel version does.

| File | Columns | Rows observed | What it contributes | Consumed by |
|---|---|---|---|---|
| `Occupation Data.txt` | O*NET-SOC Code, Title, Description | 1,016 | Occupation identity, title and description text | Occupation nodes; description embedded in Sprint 2 |
| `Essential Skills.txt` | O*NET-SOC Code, Element ID, Element Name, Scale ID, Data Value, N, Standard Error, Lower CI Bound, Upper CI Bound, Recommend Suppress, Not Relevant, Date, Domain Source | 18,200 | Importance (IM, 1 to 5) and Level (LV, 0 to 7) of 10 basic skills per occupation | REQUIRES edge weights; SkillCoverage and MissingPenalty; skills gap |
| `Transferable Skills.txt` | same 13 columns as above | 45,500 | IM and LV of 25 cross-functional skills per occupation | as above |
| `Knowledge.txt` | same 13 columns as above | 60,060 | IM and LV of 33 knowledge areas per occupation | KnowledgeArea nodes and REQUIRES_KNOWLEDGE edges |
| `Software Skills.txt` | O*NET-SOC Code, Workplace Example, Element ID, Element Name, Hot Technology, In Demand | 31,821 | Named technologies (8,753 distinct) grouped into 134 commodity classes, with Hot Technology and In Demand flags (Y/N) | Technology nodes and USES edges |
| `Related Occupations.txt` | O*NET-SOC Code, Related O*NET-SOC Code, Relatedness Tier, Index | 18,460 | Published occupation-to-occupation relatedness: 4,615 Primary-Short, 4,615 Primary-Long, 9,230 Supplemental | RELATED_TO edges; GraphProximity |
| `Job Titles.txt` | O*NET-SOC Code, Job Title, Short Title, Source(s) | 54,269 | Alternate titles, including "Cloud Engineer" and "Machine Learning Engineer" | Occupation display names and interest matching; also justified the scope list |
| `Content Model Reference.txt` | Element ID, Element Name, Description | 3,006 | Definitions of every descriptor element | Skill and KnowledgeArea node descriptions (embedded in Sprint 2) |
| `Scales Reference.txt` | Scale ID, Scale Name, Minimum, Maximum | 33 | Scale bounds: IM is 1 to 5, LV is 0 to 7 | Normalising importance and level to 0 to 1 |

Notes on the rating files:

* Each (occupation, element) pair has one IM row and one LV row.
* `Recommend Suppress = Y` marks estimates that O*NET considers unreliable
  (low sample size or high error). The flag is kept in the processed data so
  the graph builder can decide how to treat it; the decision will be recorded
  in `04-knowledge-graph-schema.md`.
* `Not Relevant = Y` appears on LV rows only (IM rows read `n/a`) and marks a
  skill that analysts judged not relevant to the occupation.

The distribution contains 37 other files (abilities, work styles, work
context, tasks and so on). They are downloaded with the zip but not used.

## 5. ESCO v1.1.0 files used

Location: `data/raw/esco/ESCO_v1.1.0/`. Comma-delimited UTF-8 CSV with one
header row. Multi-valued fields such as `altLabels` hold several labels
separated by newlines inside a quoted cell.

| File | Columns | Rows observed | What it contributes | Consumed by |
|---|---|---|---|---|
| `skills_en.csv` | conceptType, conceptUri, skillType, reuseLevel, preferredLabel, altLabels, hiddenLabels, status, modifiedDate, scopeNote, definition, inScheme, description | 13,891 | Skill and knowledge concepts with preferred and alternative labels | ESCO Skill nodes; alternative labels widen what SBERT can match |
| `occupations_en.csv` | conceptType, conceptUri, iscoGroup, preferredLabel, altLabels, hiddenLabels, status, modifiedDate, regulatedProfessionNote, scopeNote, definition, inScheme, description, code | 3,008 | ESCO occupations | Validating crosswalk URIs |
| `occupationSkillRelations_en.csv` | occupationUri, relationType, skillType, skillUri | 123,852 | ESCO's published essential/optional skills for each ESCO occupation | REQUIRES edges from O*NET occupations to ESCO skills, via the crosswalk |
| `skillSkillRelations_en.csv` | originalSkillUri, originalSkillType, relationType, relatedSkillType, relatedSkillUri | 5,899 | Published skill-to-skill relations (essential/optional) | Candidate skill-to-skill edges |
| `ictSkillsCollection_en.csv` | conceptType, conceptUri, skillType, reuseLevel, preferredLabel, status, altLabels, description, broaderConceptUri, broaderConceptPT | 21 | ESCO's official ICT skills collection | Flag on ESCO Skill nodes. Of limited value: it holds only 21 broad concepts, and 1 appears in scope |

The zip also contains 11 other files (skill hierarchy, green and language
skill collections, ISCO groups and so on) that are not used.

## 6. ESCO-O*NET crosswalk

File: `data/raw/esco/ONET_Occupations_0_updated.csv` (UTF-8 with byte-order mark).

The file starts with **16 metadata lines** (project name, author, versions,
landing pages, then two blank lines) before the header row. The metadata
confirms: author "ESCO Secretariat in collaboration with the U.S. Department of
Labor/Employment and Training Administration", version 1, dated Sep-22,
mapping O*NET-SOC 2019 to ESCO v1.1.0.

Columns: O*NET Id, O*NET Title, O*NET Description, ESCO or ISCO URI, ESCO or
ISCO Title, ESCO or ISCO Description, Type of Match.

Rows observed: 4,253 mapping rows. (The file has 5,316 physical lines because
some quoted descriptions span several lines.) Match types across the whole
file:

| Type of Match | Rows | Meaning |
|---|---|---|
| broadMatch | 2,053 | ESCO concept is broader than the O*NET occupation |
| closeMatch | 1,432 | Concepts are close enough to be used interchangeably in some contexts |
| exactMatch | 498 | Concepts are equivalent |
| narrowMatch | 227 | ESCO concept is narrower |
| exactISCO | 43 | Mapped to an ISCO group rather than an ESCO occupation |

**What the crosswalk is and is not.** It maps occupations to occupations. It
does not map skills. O*NET skills and ESCO skills are therefore never joined
directly. ESCO skills reach an O*NET occupation only through this path:

`O*NET occupation --(crosswalk row)--> ESCO occupation --(occupationSkillRelations)--> ESCO skill`

Both links are published by official bodies. No similarity-based mapping is
used to join the two vocabularies.

## 7. Technology scope

The approved proposal limits the system to technology careers: software
engineering, data science, cybersecurity, cloud computing and artificial
intelligence. The scope is the list of 24 O*NET-SOC codes in
`data/tech_occupations.csv` (committed to the repository). Each row records
the domain and the evidence for including it.

| Domain | Occupations |
|---|---|
| Software engineering (8) | 15-1251.00 Computer Programmers; 15-1252.00 Software Developers; 15-1253.00 Software Quality Assurance Analysts and Testers; 15-1254.00 Web Developers; 15-1255.00 Web and Digital Interface Designers; 15-1211.00 Computer Systems Analysts; 15-1299.07 Blockchain Engineers; 15-1299.09 Information Technology Project Managers |
| Data science (6) | 15-2051.00 Data Scientists; 15-2051.01 Business Intelligence Analysts; 15-1242.00 Database Administrators; 15-1243.00 Database Architects; 15-1243.01 Data Warehousing Specialists; 15-2041.00 Statisticians |
| Cybersecurity (4) | 15-1212.00 Information Security Analysts; 15-1299.04 Penetration Testers; 15-1299.05 Information Security Engineers; 15-1299.06 Digital Forensics Analysts |
| Cloud computing (5) | 15-1299.08 Computer Systems Engineers/Architects; 15-1241.00 Computer Network Architects; 15-1244.00 Network and Computer Systems Administrators; 15-1231.00 Computer Network Support Specialists; 15-1232.00 Computer User Support Specialists |
| Artificial intelligence (1) | 15-1221.00 Computer and Information Research Scientists |

O*NET has no dedicated SOC codes for cloud engineers or machine learning
engineers. Those roles were placed using O*NET's own `Job Titles.txt`. For
example, "Machine Learning Engineer" and "Machine Learning Scientist" are
listed under 15-1221.00, and "Cloud Engineer" is listed under 15-1231.00,
15-1251.00 and 15-1299.05. Each occupation belongs to exactly one domain in the
scope file. Where an occupation fits two domains, the domain of its core
title was used.

Excluded on purpose: management roles (11-3021.00), hardware and electronics
engineering (17-2061.00, 17-2072.00), video game design (15-1255.01), and
mathematical occupations with little computing content (actuaries,
mathematicians, operations research analysts).

## 8. Processed outputs

`scripts/prepare_data.py` writes these files to `data/processed/`, plus
`prep_report.json` with every count below. Row counts are from the run on 16
September 2026.

| File | Rows | Content |
|---|---|---|
| `onet_occupations.csv` | 24 | onet_soc_code, title, description, domain |
| `onet_occupation_ratings.csv` | 1,632 | One row per (occupation, element): category (essential_skill, transferable_skill, knowledge), element_id, element_name, importance, level, importance_norm, level_norm, recommend_suppress, not_relevant. 24 occupations x 68 elements. 136 rows flagged recommend_suppress, 290 flagged not_relevant |
| `onet_elements.csv` | 68 | element_id, element_name, category, description (10 essential skills, 25 transferable skills, 33 knowledge areas) |
| `onet_software_skills.csv` | 5,299 | onet_soc_code, technology_name, commodity_id, commodity_name, hot_technology, in_demand. 1,247 distinct technologies, 164 flagged hot, 127 in demand |
| `onet_related_occupations.csv` | 299 | Pairs with both ends in scope (out of 480 pairs starting in scope): 96 Primary-Short, 86 Primary-Long, 117 Supplemental |
| `onet_job_titles.csv` | 1,152 | Alternate titles for scope occupations |
| `onet_esco_crosswalk.csv` | 103 | onet_soc_code, esco_uri, esco_title, match_type, uri_type, uri_in_esco. 50 broadMatch, 31 closeMatch, 17 exactMatch, 4 narrowMatch, 1 exactISCO. 102 point at ESCO occupations, 1 at an ISCO group |
| `esco_occupation_skills.csv` | 7,158 | onet_soc_code, esco_occupation_uri, crosswalk_match_type, relation_type, skill_type, skill_uri. 2,402 essential and 4,756 optional, across 70 ESCO occupations |
| `esco_skills.csv` | 856 | skill_uri, preferred_label, alt_labels (pipe separated, 3,713 in total), skill_type (506 skill/competence, 349 knowledge, 1 blank), reuse_level, status, in_ict_collection, description |
| `esco_skill_relations.csv` | 330 | ESCO skill-to-skill relations with both ends in the 856 skills: 49 essential, 281 optional |

Cleaning steps applied:

* Whitespace trimmed on every field; all fields read as text first, so codes
  such as `15-1252.00` keep their format.
* Ratings checked for duplicate (occupation, element, scale) rows (none found)
  and pivoted so IM and LV sit on one row.
* Importance and level normalised to 0 to 1 using the bounds read from
  `Scales Reference.txt`, not hardcoded.
* Every scope code confirmed present in `Occupation Data.txt`, and every scope
  occupation confirmed to have all 68 rated elements.
* Duplicate rows dropped from software skills and job titles; "n/a" short
  titles blanked.
* Crosswalk rows classified by URI type; ISCO-group rows kept but marked, since
  ISCO groups have no ESCO skill relations.
* Every ESCO skill URI reached through the crosswalk confirmed present in
  `skills_en.csv` (0 missing).

## 9. Data quality observations for Sprint 2

1. **Software Developers (15-1252.00) has no exactMatch or closeMatch
   crosswalk row.** It has one exactISCO row and 12 broadMatch rows (for
   example "software developer", "mobile application developer", "gambling
   games developer"). Database Architects (15-1243.00) and Blockchain Engineers
   (15-1299.07) also lack exact or close matches. 21 of 24 scope occupations
   have at least one exact or close match. Admitting only exact and close
   matches would remove ESCO skills from the most central occupation, so the
   graph builder admits all four occupation match types by default and keeps
   the match type on each edge for weighting.
2. One ESCO skill in scope ("implement cloud security and compliance") has a
   blank `skillType`.
3. The ESCO ICT skills collection is too small (21 concepts) to be a useful
   filter.
4. O*NET describes the United States labour market, as noted in the
   proposal's limitations.
