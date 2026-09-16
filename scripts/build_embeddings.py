"""
Precompute Sentence-BERT embeddings for the knowledge graph's skill nodes.

SCAFFOLD ONLY (Sprint 1). Argument parsing, configuration lookup, path
handling and logging work. Loading the model and computing embeddings is a
Sprint 2 task; running the script today checks its inputs, prints the plan
and exits with status 2. It does not download model weights.

Usage (from the project root):

    python scripts/build_embeddings.py
    python scripts/build_embeddings.py --batch-size 64 --device cpu

Planned stages:

    Stage 1  Load the graph
             Read the serialised graph from --graph-dir (written by
             scripts/build_graph.py) and select Skill, KnowledgeArea and
             Technology nodes.

    Stage 2  Assemble the text to embed for each node
             The label, each alternative label (ESCO), and the element
             description (O*NET). Each label is embedded separately so a user
             phrase can match an alternative label directly; the mapping from
             label row back to node id is kept.

    Stage 3  Encode
             Load the model named by SBERT_MODEL_NAME from the environment
             (sentence-transformers/all-mpnet-base-v2; weights download on
             first use), encode in batches of --batch-size, L2-normalise so
             that a dot product equals cosine similarity.

    Stage 4  Save
             Write the embedding matrix (.npy), the row-to-node index and a
             metadata file (model name, model revision, graph build id,
             embedding dimension, row count, creation time) to --output-dir.
             The engine refuses to load embeddings whose metadata does not
             match the loaded graph.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.data_manifest import PROJECT_ROOT  # noqa: E402

log = logging.getLogger("build_embeddings")

NOT_IMPLEMENTED_EXIT = 2
DEFAULT_GRAPH_DIR = PROJECT_ROOT / "data" / "graph"

STAGES = [
    "Load serialised graph and select Skill / KnowledgeArea / Technology nodes",
    "Assemble label and description texts with a row-to-node index",
    "Encode texts with Sentence-BERT and L2-normalise",
    "Save embedding matrix, index and metadata",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Precompute skill node embeddings.")
    parser.add_argument(
        "--graph-dir",
        type=Path,
        default=DEFAULT_GRAPH_DIR,
        help="Directory holding the serialised graph (default: data/graph).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_GRAPH_DIR,
        help="Directory for embeddings and index (default: data/graph).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the SBERT model name (default: SBERT_MODEL_NAME from .env).",
    )
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args(argv)


def resolve_model_name(override):
    load_dotenv(PROJECT_ROOT / ".env")
    name = override or os.environ.get("SBERT_MODEL_NAME")
    if not name:
        log.error("SBERT_MODEL_NAME is not set. Add it to .env (see .env.example).")
    return name


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    model_name = resolve_model_name(args.model)
    if not model_name:
        return 1
    if args.batch_size < 1:
        log.error("--batch-size must be at least 1")
        return 1

    log.info("Model:            %s", model_name)
    log.info("Graph directory:  %s", args.graph_dir)
    log.info("Output directory: %s", args.output_dir)
    log.info("Batch size: %d, device: %s", args.batch_size, args.device)

    if not args.graph_dir.exists():
        log.error("Graph directory %s does not exist.", args.graph_dir)
        return 1

    for number, stage in enumerate(STAGES, start=1):
        log.info("Stage %d: %s", number, stage)

    log.warning(
        "Embedding computation is not implemented yet (scheduled for Sprint 2). "
        "No model was loaded and nothing was written."
    )
    return NOT_IMPLEMENTED_EXIT


if __name__ == "__main__":
    sys.exit(main())
