"""
Build the NetworkX knowledge graph from the processed CSVs.

SCAFFOLD ONLY (Sprint 1). Argument parsing, path handling, input checks and
logging work. The graph construction itself is the first task of Sprint 2;
running the script today checks the inputs, prints the build plan and exits
with status 2.

Usage (from the project root):

    python scripts/build_graph.py
    python scripts/build_graph.py --max-related-tier Primary-Short --dry-run

Planned stages (see docs/04-knowledge-graph-schema.md for node and edge types):

    Stage 1  Load inputs
             Read the processed CSVs listed in REQUIRED_INPUTS and
             prep_report.json. Refuse to build if the report's O*NET or ESCO
             version differs from scripts/data_manifest.py.

    Stage 2  Occupation nodes
             One node per row of onet_occupations.csv, id "occ:<soc code>",
             with title, description, domain and alternate job titles.

    Stage 3  Skill and KnowledgeArea nodes (O*NET)
             One node per element in onet_elements.csv, id "onet:<element id>".
             Essential and transferable skills become Skill nodes; knowledge
             elements become KnowledgeArea nodes.

    Stage 4  REQUIRES and REQUIRES_KNOWLEDGE edges (O*NET)
             From onet_occupation_ratings.csv. Edge attributes: importance,
             level, their normalised forms, recommend_suppress, not_relevant,
             provenance="onet". Rows flagged not_relevant are skipped; the
             handling of recommend_suppress is decided and logged here.

    Stage 5  Technology nodes and USES edges (O*NET)
             From onet_software_skills.csv, id "tech:<normalised name>", with
             hot_technology and in_demand flags, provenance="onet".

    Stage 6  RELATED_TO edges between occupations (O*NET)
             From onet_related_occupations.csv, limited to tiers up to
             --max-related-tier, with tier and index, provenance="onet".

    Stage 7  ESCO Skill nodes and REQUIRES edges via the crosswalk
             From esco_occupation_skills.csv and esco_skills.csv, id
             "esco:<uuid>", carrying preferred and alternative labels.
             Edge attributes: relation_type (essential/optional),
             crosswalk_match_type, provenance="esco_via_crosswalk".
             --crosswalk-match-types controls which match types are admitted.

    Stage 8  ESCO skill-to-skill edges
             From esco_skill_relations.csv, provenance="esco".

    Stage 9  Validate and serialise
             Check every edge endpoint exists, every edge carries a
             provenance attribute, and no occupation is isolated. Write the
             graph and a build summary (node and edge counts per type) to
             --output-dir.

No edge is created from embedding similarity in this script. Any such edge
is added in a separate, clearly labelled step (provenance="derived_similarity").
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.data_manifest import PROCESSED_DIR, PROJECT_ROOT  # noqa: E402

log = logging.getLogger("build_graph")

REQUIRED_INPUTS = [
    "prep_report.json",
    "onet_occupations.csv",
    "onet_occupation_ratings.csv",
    "onet_elements.csv",
    "onet_software_skills.csv",
    "onet_related_occupations.csv",
    "onet_job_titles.csv",
    "onet_esco_crosswalk.csv",
    "esco_occupation_skills.csv",
    "esco_skills.csv",
    "esco_skill_relations.csv",
]

RELATED_TIERS = ["Primary-Short", "Primary-Long", "Supplemental"]
# SKOS match types that point at ESCO occupations. The fifth type in the
# crosswalk, exactISCO, points at an ISCO group, which has no ESCO skill
# relations, so it is never used to attach skills.
CROSSWALK_MATCH_TYPES = ["exactMatch", "closeMatch", "broadMatch", "narrowMatch"]
NOT_IMPLEMENTED_EXIT = 2

STAGES = [
    "Load and version-check processed inputs",
    "Create Occupation nodes",
    "Create O*NET Skill and KnowledgeArea nodes",
    "Create REQUIRES / REQUIRES_KNOWLEDGE edges from O*NET ratings",
    "Create Technology nodes and USES edges",
    "Create RELATED_TO edges between occupations",
    "Create ESCO Skill nodes and crosswalk REQUIRES edges",
    "Create ESCO skill-to-skill edges",
    "Validate provenance and serialise graph",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Build the career knowledge graph.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=PROCESSED_DIR,
        help="Directory holding the processed CSVs (default: data/processed).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "graph",
        help="Directory for the serialised graph (default: data/graph).",
    )
    parser.add_argument(
        "--max-related-tier",
        choices=RELATED_TIERS,
        default="Primary-Long",
        help="Least strong O*NET relatedness tier to include as RELATED_TO edges.",
    )
    parser.add_argument(
        "--crosswalk-match-types",
        nargs="+",
        choices=CROSSWALK_MATCH_TYPES,
        default=CROSSWALK_MATCH_TYPES,
        help=(
            "Crosswalk match types admitted when attaching ESCO skills. All are admitted "
            "by default because Software Developers has only broadMatch rows; the match "
            "type is kept on every edge so it can be weighted later."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check inputs and print the plan without writing anything.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args(argv)


def check_inputs(input_dir):
    missing = [name for name in REQUIRED_INPUTS if not (input_dir / name).exists()]
    if missing:
        log.error(
            "Missing processed inputs in %s: %s\nRun `python scripts/prepare_data.py` first.",
            input_dir,
            ", ".join(missing),
        )
        return False
    return True


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    log.info("Input directory:  %s", args.input_dir)
    log.info("Output directory: %s", args.output_dir)
    log.info("Related tiers up to: %s", args.max_related_tier)
    log.info("Crosswalk match types: %s", ", ".join(args.crosswalk_match_types))

    if not check_inputs(args.input_dir):
        return 1
    log.info("All %d processed inputs present.", len(REQUIRED_INPUTS))

    for number, stage in enumerate(STAGES, start=1):
        log.info("Stage %d: %s", number, stage)

    log.warning(
        "Graph construction is not implemented yet (scheduled for Sprint 2). "
        "Nothing was written."
    )
    return NOT_IMPLEMENTED_EXIT


if __name__ == "__main__":
    sys.exit(main())
