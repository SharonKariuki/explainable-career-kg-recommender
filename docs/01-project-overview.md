# 01. Project Overview

**Title:** An Explainable Knowledge Graph-Driven Career Guidance Recommender for
the Cold-Start Recommendation Problem Using Semantic Similarity

**Author:** Sharon Mugure Kariuki (169276), BSc Informatics and Computer
Science, Strathmore University

**Supervisor:** Mr. Kevin Ochieng Omondi

This summary is drawn from the approved proposal (June 2026).

## Problem statement

Career recommendation systems help students and young professionals find
suitable career paths, but most of them depend on a user's interaction
history. Collaborative filtering cannot model the preferences of a user it
knows nothing about, and content-based filtering needs a detailed profile.
Students and recent graduates are exactly the people with the least history
and the sparsest profiles, so they receive the weakest recommendations. This
is the **cold-start problem**.

Existing systems also tend to work as black boxes. They return a list of
careers without saying why each one was suggested. That lowers user trust and
leaves users unable to judge whether a suggestion fits them, or what they
would need to learn to pursue it. This is the **explainability problem**.

Knowledge graph approaches model rich relationships between skills,
occupations and learning resources, but their use in career recommendation
that is both explainable and designed for cold-start users remains limited.

This project addresses both problems together:

1. **Cold start.** A user who declares only one or two skills must still
   receive useful, ranked career recommendations.
2. **Explainability.** Every recommendation must be traceable to the evidence
   that produced it. An explanation is built from that evidence, never
   written separately to sound plausible.

## Approach

* An occupational **knowledge graph** built from O*NET 31.0, with ESCO v1.1.0
  skill vocabulary attached through the official ESCO-O*NET crosswalk.
* **Sentence-BERT** (`sentence-transformers/all-mpnet-base-v2`) matching of the
  user's own skill wording against skill nodes in the graph, so "coding" and
  "programming" are treated alike.
* **Breadth-first traversal** from the matched skills to candidate
  occupations.
* A **transparent additive score** whose individual terms are stored and
  reused to produce the explanation and the skills gap:

  `FinalScore(o) = 0.5 * SkillCoverage(o) + 0.2 * GraphProximity(o) - 0.3 * MissingPenalty(o)`

  The weights are configuration values and will be tuned during evaluation.

## Objectives

General objective: to develop an explainable knowledge graph-based career
recommendation system that addresses the cold-start problem through semantic
similarity.

Specific objectives:

1. Analyse the current state of career recommendation systems for cold-start
   users.
2. Study existing approaches, frameworks and techniques for career
   recommendation, explainable recommendation, semantic similarity and
   knowledge graph-based recommendation.
3. Identify the challenges, limitations and research gaps in existing career
   recommendation systems.
4. Design and develop an explainable knowledge graph-driven career
   recommendation framework using semantic similarity and occupational data.
5. Test and validate the system's personalised recommendations for cold-start
   users.

## Research questions

1. What is the current state of career recommendation systems for cold-start
   users?
2. What approaches, frameworks and techniques have been applied in career
   recommendation, explainable recommendation, semantic similarity and
   knowledge graph-based recommendation?
3. What challenges, limitations and research gaps exist for cold-start users?
4. How can an explainable knowledge graph-driven framework be designed and
   developed to support career recommendation?
5. To what extent does the proposed system improve recommendation relevance
   and explainability for cold-start users?

## Scope

* Users: students and early-career professionals.
* Domain: technology careers only (software engineering, data science,
  cybersecurity, cloud computing, artificial intelligence). The 24 O*NET
  occupations in scope are listed in `03-data-sources.md`.
* Inputs: declared skills, education, interests.
* Outputs: ranked careers, a relevance score, a plain-language explanation, a
  skills gap and, later, learning resources.
* Platform: web application only, English only.

## Delimitations and limitations

* Only publicly available O*NET and ESCO data; no proprietary datasets.
* O*NET describes the United States labour market, so some requirements may
  not match the Kenyan market.
* Recommendation quality depends on the quality of self-reported skills.
* The system supports career decisions; it does not replace a career
  counsellor.

## Evaluation plan

Performance will be measured on a held-out 20 percent of synthesised user
profiles using Precision@K, Recall@K and Mean Reciprocal Rank, plus an
Explainability Quality Score. Cold-start performance will be measured
separately on profiles with three or fewer skills and compared with a
content-based baseline. The target is Precision@K of at least 0.60 on sparse
profiles.

## Sprint plan

| Sprint | Focus |
|---|---|
| 1 | Data preparation and development environment (this sprint) |
| 2 | Knowledge graph construction and skill embeddings |
| 3 | Semantic matching, traversal and scoring engine |
| 4 | Explanation and skills-gap modules |
| 5 | API, React interface and integration |
| 6 | System testing, evaluation and documentation |
