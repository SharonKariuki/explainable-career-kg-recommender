"""
Fetch and verify the raw O*NET and ESCO source files.

Usage (from the project root, virtual environment active):

    python scripts/download_data.py              # download anything missing, then verify
    python scripts/download_data.py --verify-only
    python scripts/download_data.py --force      # re-download even if present

What it does:
    1. For each archive in scripts/data_manifest.py (O*NET 31.0 text, ESCO
       v1.1.0 CSV), download the zip if its extracted files are missing, then
       extract it.
    2. Download the ESCO-O*NET crosswalk CSV if missing.
    3. Verify every expected file: it exists, is non-empty, and its header row
       contains exactly the expected columns.
    4. Write data/raw/download_manifest.json recording URL, size, SHA-256 and
       retrieval time for every downloaded artefact.

If a download fails, the script prints the manual download steps for that
source and exits with status 1. It never passes silently over a missing file.
Uses only the standard library so it can run before pandas is installed.
"""

import argparse
import csv
import hashlib
import json
import logging
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.data_manifest import (  # noqa: E402
    ARCHIVES,
    CROSSWALK_FILE,
    CROSSWALK_URL,
    ESCO_RAW_DIR,
    RAW_DIR,
)

log = logging.getLogger("download_data")

USER_AGENT = "career-recommender-capstone/0.1 (academic research; Strathmore University)"
CROSSWALK_MANUAL_STEPS = (
    "1. Open https://esco.ec.europa.eu/en/use-esco/other-crosswalks\n"
    "2. Download the ESCO - O*NET crosswalk CSV (ONET_(Occupations)_0_updated.csv).\n"
    "3. Save it as data/raw/esco/ONET_Occupations_0_updated.csv"
)


class DataError(Exception):
    """A source file is missing or malformed."""


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    log.info("Downloading %s", url)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response, open(partial, "wb") as out:
        total = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            total += len(chunk)
    partial.replace(destination)
    log.info("Saved %s (%.1f MB)", destination, total / 1e6)
    return {
        "url": url,
        "path": str(destination.relative_to(RAW_DIR.parent.parent)),
        "bytes": destination.stat().st_size,
        "sha256": sha256_of(destination),
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def extract(zip_path, extract_dir):
    log.info("Extracting %s -> %s", zip_path.name, extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_dir)


def read_header(source):
    """Return the header row of a source file, honouring its metadata offset."""
    with open(source.path, encoding=source.encoding, newline="") as handle:
        for _ in range(source.header_offset):
            handle.readline()
        reader = csv.reader(handle, delimiter=source.delimiter)
        return next(reader)


def verify_file(source):
    """Raise DataError if the file is absent, empty or has unexpected columns."""
    if not source.path.exists():
        raise DataError(f"Missing file: {source.path}")
    if source.path.stat().st_size == 0:
        raise DataError(f"Empty file: {source.path}")
    header = [column.strip() for column in read_header(source)]
    if tuple(header) != tuple(source.columns):
        raise DataError(
            f"Unexpected columns in {source.path.name}.\n"
            f"  expected: {list(source.columns)}\n"
            f"  found:    {header}"
        )


def files_missing(files):
    return [source for source in files if not source.path.exists()]


def load_manifest(path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--verify-only", action="store_true", help="Do not download; only check files."
    )
    parser.add_argument("--force", action="store_true", help="Re-download sources even if present.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    manifest_path = RAW_DIR / "download_manifest.json"
    manifest = load_manifest(manifest_path)
    problems = []

    if not args.verify_only:
        for archive in ARCHIVES:
            if files_missing(archive.files) or args.force:
                try:
                    if args.force or not archive.zip_path.exists():
                        manifest[archive.name] = download(archive.url, archive.zip_path)
                    extract(archive.zip_path, archive.extract_dir)
                except Exception as exc:  # network, HTTP or zip errors
                    problems.append(
                        f"Could not obtain {archive.name}: {exc}\n"
                        f"Manual download steps:\n{archive.manual_steps}"
                    )
            else:
                log.info("%s already present, skipping download", archive.name)

        if not CROSSWALK_FILE.path.exists() or args.force:
            try:
                manifest["ESCO-O*NET crosswalk"] = download(CROSSWALK_URL, CROSSWALK_FILE.path)
            except Exception as exc:
                problems.append(
                    f"Could not obtain the ESCO-O*NET crosswalk: {exc}\n"
                    f"Manual download steps:\n{CROSSWALK_MANUAL_STEPS}"
                )
        else:
            log.info("ESCO-O*NET crosswalk already present, skipping download")

        ESCO_RAW_DIR.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    all_sources = [(archive, source) for archive in ARCHIVES for source in archive.files]
    all_sources.append((None, CROSSWALK_FILE))
    for archive, source in all_sources:
        try:
            verify_file(source)
            log.info("OK  %s", source.path.relative_to(RAW_DIR))
        except DataError as exc:
            steps = archive.manual_steps if archive else CROSSWALK_MANUAL_STEPS
            problems.append(f"{exc}\nTo fix, run without --verify-only or follow:\n{steps}")

    if problems:
        log.error("Data check FAILED with %d problem(s):", len(problems))
        for problem in problems:
            log.error("\n%s\n", problem)
        return 1

    log.info("All %d source files present and well-formed.", len(all_sources))
    return 0


if __name__ == "__main__":
    sys.exit(main())
