# 04. Knowledge Graph Schema

Status: **planned**. The graph is built in Sprint 2 by `scripts/build_graph.py`
from the processed CSVs described in `03-data-sources.md`. This document fixes
the node types, relationship types and, most importantly, where each
relationship comes from.

The graph is a NetworkX `MultiDiGraph` held in memory by the Django process.
It covers the 24 technology occupations in `data/tech_occupations.csv`.

## 1. Node types

| Node type | ID format | Source file (processed) | Key attributes | Expected count |
|---|---|---|---|---|
| Occupation | `occ:<O*NET-SOC code>`, e.g. `occ:15-1252.00` | `onet_occupations.csv`, `onet_job_titles.csv` | title, description, domain, alternate_titles | 24 |
| Skill (O*NET) | `onet:<element id>`, e.g. `onet:2.A.1.a` | `onet_elements.csv` (category essential_skill or transferable_skill) | label, description, category | 35 |
| Skill (ESCO) | `esco:<uuid>` taken from the ESCO URI | `esco_skills.csv` | label (preferred), alt_labels, description, esco_skill_type, reuse_level, uri | 856 |
| KnowledgeArea | `onet:<element id>`, e.g. `onet:2.C.3.a` | `onet_elements.csv` (category knowledge) | label, description | 33 |
| Technology | `tech:<normalised name>` | `onet_software_skills.csv` | label, commodity_id, commodity_name, hot_technology, in_demand | about 1,247 |

Every node also carries `node_type` and `source` ("onet" or "esco").

Both O*NET skills and ESCO skills are `Skill` nodes, so semantic matching
treats them the same way. The `source` attribute keeps them distinguishable.
Note that ESCO's own "knowledge" skill type (349 of the 856 ESCO concepts, for
example "Lean project management") stays a `Skill` node with
`esco_skill_type = "knowledge"`. It is not merged into O*NET's 33 broad
knowledge areas, because no published mapping exists between the two.

## 2. Relationship types

| Relationship | Direction | Attributes |
|---|---|---|
| REQUIRES | Occupation -> Skill | For O*NET skills: importance (1 to 5), level (0 to 7), importance_norm, level_norm, recommend_suppress. For ESCO skills: relation_type (essential or optional), crosswalk_match_type, via_esco_occupation (URI). All: provenance |
| REQUIRES_KNOWLEDGE | Occupation -> KnowledgeArea | importance, level, importance_norm, level_norm, recommend_suppress, provenance |
| USES | Occupation -> Technology | hot_technology, in_demand, provenance |
| RELATED_TO | Occupation -> Occupation | relatedness_tier (Primary-Short, Primary-Long, Supplemental), relatedness_index (1 = most related), provenance |
| SKILL_RELATED_TO | Skill (ESCO) -> Skill (ESCO) | relation_type (essential or optional), provenance |
| SIMILAR_TO | Skill -> Skill | cosine_similarity, model_name, threshold, provenance. **Derived; see section 3** |

The REQUIRES importance weight is O*NET's own IM rating. For ESCO skills, the
weight will be set from relation_type (essential above optional). The exact
numbers are a Sprint 2 decision and will be recorded here with the reason.

Rules applied when building REQUIRES and REQUIRES_KNOWLEDGE edges:

* Rows with `not_relevant = true` (290 of 1,632) produce no edge, because O*NET
  analysts judged the element not relevant to that occupation.
* How rows with `recommend_suppress = true` (136 of 1,632) are treated is
  decided in Sprint 2. The flag is carried onto the edge either way, so the
  decision can be audited.

## 3. Provenance: how we know each edge is true

Every edge stores a `provenance` attribute with one of the values below.
`build_graph.py` refuses to save a graph containing an edge without one.

| Relationship | Provenance value | Where the assertion comes from | Who asserted it | Can it be wrong? |
|---|---|---|---|---|
| Occupation REQUIRES Skill (O*NET) | `onet` | `Essential Skills.txt`, `Transferable Skills.txt` | O*NET analysts and job incumbent surveys, with published sample size and standard error | Only as far as the O*NET estimate is wrong; low-confidence estimates are flagged `recommend_suppress` |
| Occupation REQUIRES_KNOWLEDGE KnowledgeArea | `onet` | `Knowledge.txt` | O*NET incumbent surveys | As above |
| Occupation USES Technology | `onet` | `Software Skills.txt` | O*NET, from employer job postings and occupational experts | As above |
| Occupation RELATED_TO Occupation | `onet` | `Related Occupations.txt` | O*NET's published relatedness model | As above |
| Occupation REQUIRES Skill (ESCO) | `esco_via_crosswalk` | Two published links: a crosswalk row (O*NET occupation to ESCO occupation) and an `occupationSkillRelations_en.csv` row (ESCO occupation to ESCO skill) | Crosswalk: ESCO Secretariat with USDOL/ETA. Skill relation: ESCO (European Commission) | Yes, in one specific way: a broadMatch row links to an ESCO occupation broader than the O*NET one, so its skills may be less specific. The edge keeps `crosswalk_match_type` and `via_esco_occupation` so this can be seen and weighted |
| Skill SKILL_RELATED_TO Skill (ESCO) | `esco` | `skillSkillRelations_en.csv` | ESCO (European Commission) | Only as far as ESCO is wrong |
| Skill SIMILAR_TO Skill | `derived_similarity` | Cosine similarity of Sentence-BERT embeddings above a stated threshold | **This project**, not a published source | Yes. These edges are a model's judgement and are never presented as fact |

Rules that follow from this table:

1. **No edge joins the O*NET and ESCO vocabularies by similarity.** The only
   bridge is the published crosswalk, which links occupations, not skills.
2. **Derived edges are optional and labelled.** If SIMILAR_TO edges are added
   in Sprint 2, they are created in a separate step, carry `derived_similarity`
   together with the model name and threshold, and can be switched off to
   measure their effect.
3. **Explanations state provenance.** When an explanation cites a path, each
   hop names its source, so a user or examiner can tell "O*NET rates this
   skill as important for this occupation" apart from "the model judged these
   two skills similar".
4. **The user-to-graph link is not an edge.** A user's typed skill is matched to
   a Skill node at request time by SBERT similarity. That match is stored with
   its similarity score in the Explanation record (`matched_skills`), not in
   the graph.

## 4. Traversal (for reference)

A recommendation request starts from the Skill nodes matched to the user's
input and searches breadth-first along REQUIRES (reversed), SKILL_RELATED_TO
and RELATED_TO edges, up to `MAX_TRAVERSAL_DEPTH` hops (configured in `.env`).
The depth at which each occupation is reached, and the path that reached it,
feed GraphProximity and the explanation. Traversal is implemented in Sprint 3.

## 5. Serialisation

`build_graph.py` will write the graph and a `build_summary.json` (node and edge
counts per type and per provenance value, source versions, build time) to
`data/graph/`. `build_embeddings.py` records the graph build it was computed
from, so the engine can refuse mismatched files. Both outputs are gitignored.
