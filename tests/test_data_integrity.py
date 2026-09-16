"""
Source data presence and shape checks.

Raw files are defined once in scripts/data_manifest.py. If a check fails
because data is missing, run `python scripts/download_data.py` and then
`python scripts/prepare_data.py` (see docs/05-setup-guide.md).
"""

import json

import pandas as pd
import pytest

from scripts.data_manifest import (
    ALL_FILES,
    CROSSWALK_FILE,
    ESCO_VERSION,
    ONET_VERSION,
    PROCESSED_DIR,
    TECH_SCOPE_FILE,
)

pytestmark = pytest.mark.data

FIX_HINT = "Run `python scripts/download_data.py` (see docs/05-setup-guide.md)."
PREP_HINT = "Run `python scripts/prepare_data.py` after downloading the data."

SOURCES = {source.key: source for source in ALL_FILES}


def read(source, **kwargs):
    return pd.read_csv(
        source.path,
        sep=source.delimiter,
        dtype=str,
        keep_default_na=False,
        encoding=source.encoding,
        skiprows=source.header_offset,
        **kwargs,
    )


@pytest.fixture(scope="module")
def scope_codes():
    scope = pd.read_csv(TECH_SCOPE_FILE, dtype=str)
    return set(scope["onet_soc_code"])


@pytest.fixture(scope="module")
def frames():
    """Parse each raw file once per test module."""
    cache = {}

    def load(key):
        if key not in cache:
            cache[key] = read(SOURCES[key])
        return cache[key]

    return load


# Raw files


@pytest.mark.parametrize("source", ALL_FILES, ids=lambda s: s.key)
def test_raw_file_exists_and_non_empty(source):
    assert source.path.exists(), f"Missing {source.path}. {FIX_HINT}"
    assert source.path.stat().st_size > 0, f"Empty {source.path}. {FIX_HINT}"


@pytest.mark.parametrize("source", ALL_FILES, ids=lambda s: s.key)
def test_raw_file_parses_with_expected_columns(source, frames):
    if not source.path.exists():
        pytest.fail(f"Missing {source.path}. {FIX_HINT}")
    frame = frames(source.key)
    assert tuple(frame.columns) == source.columns
    assert (
        len(frame) >= source.min_rows
    ), f"{source.path.name} has {len(frame)} rows, expected at least {source.min_rows}"


def test_scope_file_is_valid(scope_codes, frames):
    scope = pd.read_csv(TECH_SCOPE_FILE, dtype=str)
    assert set(scope.columns) == {"onet_soc_code", "title", "domain", "evidence"}
    assert not scope["onet_soc_code"].duplicated().any()
    assert set(scope["domain"]) == {
        "software engineering",
        "data science",
        "cybersecurity",
        "cloud computing",
        "artificial intelligence",
    }
    occupations = frames("onet_occupation_data").set_index("O*NET-SOC Code")["Title"]
    for _, row in scope.iterrows():
        assert row["onet_soc_code"] in occupations.index
        assert occupations[row["onet_soc_code"]] == row["title"]


def test_onet_skill_ratings_cover_35_elements_per_scope_occupation(scope_codes, frames):
    essential = frames("onet_essential_skills")
    transferable = frames("onet_transferable_skills")
    assert essential["Element ID"].str.startswith("2.A").all()
    assert transferable["Element ID"].str.startswith("2.B").all()
    combined = pd.concat([essential, transferable])
    combined = combined[combined["O*NET-SOC Code"].isin(scope_codes)]
    per_occupation = combined.groupby("O*NET-SOC Code")["Element ID"].nunique()
    assert set(per_occupation.index) == scope_codes
    assert (per_occupation == 35).all()
    assert set(combined["Scale ID"]) == {"IM", "LV"}
    pd.to_numeric(combined["Data Value"], errors="raise")


def test_onet_scales_have_expected_bounds(frames):
    scales = frames("onet_scales_reference").set_index("Scale ID")
    assert (scales.loc["IM", "Minimum"], scales.loc["IM", "Maximum"]) == ("1", "5")
    assert (scales.loc["LV", "Minimum"], scales.loc["LV", "Maximum"]) == ("0", "7")


def test_onet_software_skills_cover_scope(scope_codes, frames):
    software = frames("onet_software_skills")
    covered = set(software.loc[software["O*NET-SOC Code"].isin(scope_codes), "O*NET-SOC Code"])
    assert covered == scope_codes
    assert set(software["Hot Technology"]) <= {"Y", "N"}
    assert set(software["In Demand"]) <= {"Y", "N"}


def test_related_occupations_reference_known_codes(frames):
    related = frames("onet_related_occupations")
    known = set(frames("onet_occupation_data")["O*NET-SOC Code"])
    assert set(related["O*NET-SOC Code"]) <= known
    assert set(related["Related O*NET-SOC Code"]) <= known


def test_crosswalk_metadata_and_scope(scope_codes):
    with open(CROSSWALK_FILE.path, encoding=CROSSWALK_FILE.encoding) as handle:
        head = [next(handle) for _ in range(CROSSWALK_FILE.header_offset)]
    metadata = dict(line.rstrip("\n").split(",", 1) for line in head if line.strip(",\n"))
    assert metadata["Mapping project name"].strip(",") == "ESCO-O*NET Crosswalk"
    assert metadata["Classification 2 Version"].strip(",") == ESCO_VERSION

    crosswalk = read(CROSSWALK_FILE)
    crosswalk = crosswalk[crosswalk["O*NET Id"] != ""]
    assert scope_codes <= set(crosswalk["O*NET Id"])


def test_crosswalk_esco_uris_resolve_in_esco_release(scope_codes, frames):
    crosswalk = read(CROSSWALK_FILE)
    in_scope = crosswalk[crosswalk["O*NET Id"].isin(scope_codes)]
    occupation_uris = in_scope.loc[
        in_scope["ESCO or ISCO URI"].str.startswith("http://data.europa.eu/esco/occupation/"),
        "ESCO or ISCO URI",
    ]
    known = set(frames("esco_occupations")["conceptUri"])
    unresolved = set(occupation_uris) - known
    assert not unresolved, f"Crosswalk URIs not in ESCO {ESCO_VERSION}: {sorted(unresolved)}"


def test_esco_skill_relations_reference_known_skills(frames):
    relations = frames("esco_occupation_skill_relations")
    skills = set(frames("esco_skills")["conceptUri"])
    assert set(relations["relationType"]) <= {"essential", "optional"}
    assert set(relations["skillUri"]) <= skills


def test_esco_skills_have_labels(frames):
    skills = frames("esco_skills")
    assert (skills["preferredLabel"].str.strip() != "").all()
    assert skills["conceptUri"].is_unique


# Processed outputs (written by scripts/prepare_data.py)

PROCESSED_OUTPUTS = [
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


@pytest.fixture(scope="module")
def prep_report():
    path = PROCESSED_DIR / "prep_report.json"
    if not path.exists():
        pytest.fail(f"Missing {path}. {PREP_HINT}")
    return json.loads(path.read_text(encoding="utf-8"))


def test_prep_report_versions(prep_report, scope_codes):
    assert prep_report["onet_version"] == ONET_VERSION
    assert prep_report["esco_version"] == ESCO_VERSION
    assert prep_report["scope_occupations"] == len(scope_codes)
    assert prep_report["occupations_without_ratings"] == []


@pytest.mark.parametrize("name", PROCESSED_OUTPUTS)
def test_processed_output_matches_report(name, prep_report):
    path = PROCESSED_DIR / name
    assert path.exists(), f"Missing {path}. {PREP_HINT}"
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    assert len(frame) > 0
    assert len(frame) == prep_report["outputs"][name]


def test_processed_occupations_match_scope(scope_codes):
    occupations = pd.read_csv(PROCESSED_DIR / "onet_occupations.csv", dtype=str)
    assert set(occupations["onet_soc_code"]) == scope_codes
    assert (occupations["description"].str.len() > 0).all()


def test_processed_ratings_are_normalised():
    ratings = pd.read_csv(PROCESSED_DIR / "onet_occupation_ratings.csv")
    assert ratings["importance_norm"].between(0, 1).all()
    assert ratings["level_norm"].between(0, 1).all()
    assert set(ratings["category"]) == {"essential_skill", "transferable_skill", "knowledge"}
    assert not ratings.duplicated(["onet_soc_code", "element_id"]).any()


def test_processed_esco_links_are_consistent(scope_codes):
    crosswalk = pd.read_csv(PROCESSED_DIR / "onet_esco_crosswalk.csv", dtype=str)
    occupation_skills = pd.read_csv(PROCESSED_DIR / "esco_occupation_skills.csv", dtype=str)
    skills = pd.read_csv(PROCESSED_DIR / "esco_skills.csv", dtype=str, keep_default_na=False)
    assert set(occupation_skills["onet_soc_code"]) <= scope_codes
    assert set(occupation_skills["esco_occupation_uri"]) <= set(crosswalk["esco_uri"])
    assert set(occupation_skills["skill_uri"]) == set(skills["skill_uri"])
