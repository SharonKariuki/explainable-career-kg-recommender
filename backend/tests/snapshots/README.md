# Ranking-invariance baseline

This folder holds the approved ranking baseline for Measured Matching (#157). It starts empty:
there is **no approved baseline yet**, so the `Ranking invariance (PR)` workflow fails closed.

| File | Written by | Purpose |
|---|---|---|
| `ranking_invariance_v1.json.gz` | `python -m recommender.invariance generate`, in the pinned Linux environment | Canonical ranking record for the fixed corpus, plus provenance and the environment fingerprint. Always `"status": "provisional"` |
| `requirements_lock_v1.txt` | the same command | The exact package set of the generating environment; the PR job installs from it with `--no-deps` |
| `approval_v1.json` | **a reviewer, by hand** | Adopts one snapshot, named by the sha256 of its content |

## Approving a provisional baseline

1. When no baseline is approved, the PR workflow generates a provisional one in the pinned environment:
   - base image `python:3.11-slim` at a resolved digest;
   - the model at the resolved revision, loaded offline;
   - the run uses `--network none`;
   - the ranking sources are checked against `739956a`.

   It uploads the result as the artifact `provisional-ranking-baseline-<sha>`, then fails.
2. Review the artifact:
   - `model_provision.json`: the model files checked against Hugging Face's published hashes;
   - `expected_sources_739956a.json`;
   - the fingerprint and profile count in the snapshot.
3. Copy `ranking_invariance_v1.json.gz` and `requirements_lock_v1.txt` into this folder. Add `approval_v1.json`:

   ```json
   {
     "status": "approved",
     "approved_by": "<name>",
     "approved_on": "<YYYY-MM-DD>",
     "snapshot_sha256": "<content_sha256 printed by generate>",
     "note": "<what was reviewed>"
   }
   ```

   The sha256 is of the **decompressed** snapshot content. `generate` prints it as `content_sha256`.
4. The check accepts the baseline only if the approval file names exactly this snapshot. Regenerating or editing the snapshot makes it provisional again.

The baseline changes only through an approved PR that regenerates it at a stated commit, with the reason recorded (for example, an upstream-drift report).
