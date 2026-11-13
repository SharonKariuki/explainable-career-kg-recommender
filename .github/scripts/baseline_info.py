"""Print the approved baseline's pins as GitHub Actions outputs (Measured Matching C1, #157).

    python .github/scripts/baseline_info.py backend/tests/snapshots >> "$GITHUB_OUTPUT"

Outputs: approved (true/false), status, base_image_digest, model_revision. Uses only the
standard library, so it runs on the runner before any project dependency is installed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from recommender.invariance import approval_state, read_baseline  # noqa: E402


def main(folder):
    state = approval_state(folder)
    document = read_baseline(folder) if state == 'approved' else None   # pins come only from an approved baseline
    fp = (document or {}).get('fingerprint', {})
    print(f'approved={"true" if state == "approved" else "false"}')
    print(f'status={state}')
    print(f'base_image_digest={fp.get("base_image_digest", "")}')
    print(f'model_revision={fp.get("model_revision", "")}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
