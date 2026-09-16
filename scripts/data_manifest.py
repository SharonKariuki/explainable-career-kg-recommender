"""
Single source of truth for the raw data files the project depends on.

scripts/download_data.py uses this manifest to fetch and verify files, and
tests/test_data_integrity.py uses it to assert that the files are present and
have the expected shape. Filenames and columns below were read from the
actual downloaded files (O*NET 31.0, ESCO v1.1.0, ESCO-O*NET crosswalk v1),
not assumed from older documentation.
"""

from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
ONET_RAW_DIR = RAW_DIR / "onet"
ESCO_RAW_DIR = RAW_DIR / "esco"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TECH_SCOPE_FILE = PROJECT_ROOT / "data" / "tech_occupations.csv"


@dataclass(frozen=True)
class SourceFile:
    key: str
    path: Path
    columns: tuple
    delimiter: str
    consumer: str
    # Number of metadata lines that precede the header row (crosswalk only).
    header_offset: int = 0
    encoding: str = "utf-8"
    min_rows: int = 1


@dataclass(frozen=True)
class Archive:
    name: str
    url: str
    zip_path: Path
    extract_dir: Path
    manual_steps: str
    files: list = field(default_factory=list)


# O*NET 31.0 (August 2026), tab-delimited text distribution

ONET_VERSION = "31.0"
ONET_ZIP_URL = "https://www.onetcenter.org/dl_files/database/db_31_0_text.zip"
ONET_TEXT_DIR = ONET_RAW_DIR / "db_31_0_text"

RATING_COLUMNS = (
    "O*NET-SOC Code",
    "Element ID",
    "Element Name",
    "Scale ID",
    "Data Value",
    "N",
    "Standard Error",
    "Lower CI Bound",
    "Upper CI Bound",
    "Recommend Suppress",
    "Not Relevant",
    "Date",
    "Domain Source",
)

ONET_FILES = [
    SourceFile(
        key="onet_occupation_data",
        path=ONET_TEXT_DIR / "Occupation Data.txt",
        columns=("O*NET-SOC Code", "Title", "Description"),
        delimiter="\t",
        consumer="Occupation nodes (title, description); description text is embedded.",
        min_rows=900,
    ),
    SourceFile(
        key="onet_essential_skills",
        path=ONET_TEXT_DIR / "Essential Skills.txt",
        columns=RATING_COLUMNS,
        delimiter="\t",
        consumer="REQUIRES edges (basic skills, element ids 2.A.*) with importance/level.",
        min_rows=1000,
    ),
    SourceFile(
        key="onet_transferable_skills",
        path=ONET_TEXT_DIR / "Transferable Skills.txt",
        columns=RATING_COLUMNS,
        delimiter="\t",
        consumer=(
            "REQUIRES edges (cross-functional skills, element ids 2.B.*) with importance/level."
        ),
        min_rows=1000,
    ),
    SourceFile(
        key="onet_knowledge",
        path=ONET_TEXT_DIR / "Knowledge.txt",
        columns=RATING_COLUMNS,
        delimiter="\t",
        consumer="KnowledgeArea nodes and REQUIRES_KNOWLEDGE edges with importance/level.",
        min_rows=1000,
    ),
    SourceFile(
        key="onet_software_skills",
        path=ONET_TEXT_DIR / "Software Skills.txt",
        columns=(
            "O*NET-SOC Code",
            "Workplace Example",
            "Element ID",
            "Element Name",
            "Hot Technology",
            "In Demand",
        ),
        delimiter="\t",
        consumer="Technology nodes and USES edges (hot / in-demand flags).",
        min_rows=1000,
    ),
    SourceFile(
        key="onet_related_occupations",
        path=ONET_TEXT_DIR / "Related Occupations.txt",
        columns=("O*NET-SOC Code", "Related O*NET-SOC Code", "Relatedness Tier", "Index"),
        delimiter="\t",
        consumer="RELATED_TO edges between occupations (tier and index).",
        min_rows=1000,
    ),
    SourceFile(
        key="onet_job_titles",
        path=ONET_TEXT_DIR / "Job Titles.txt",
        columns=("O*NET-SOC Code", "Job Title", "Short Title", "Source(s)"),
        delimiter="\t",
        consumer=(
            "Alternate occupation titles (for example 'Cloud Engineer') used for display and "
            "interest matching."
        ),
        min_rows=1000,
    ),
    SourceFile(
        key="onet_content_model_reference",
        path=ONET_TEXT_DIR / "Content Model Reference.txt",
        columns=("Element ID", "Element Name", "Description"),
        delimiter="\t",
        consumer="Descriptions of skill and knowledge elements; description text is embedded.",
        min_rows=100,
    ),
    SourceFile(
        key="onet_scales_reference",
        path=ONET_TEXT_DIR / "Scales Reference.txt",
        columns=("Scale ID", "Scale Name", "Minimum", "Maximum"),
        delimiter="\t",
        consumer="Min/max of the IM (1-5) and LV (0-7) scales for normalising weights.",
        min_rows=2,
    ),
]

# ESCO v1.1.0, English, CSV. v1.1.0 is the ESCO version the crosswalk targets.

ESCO_VERSION = "v1.1.0"
ESCO_ZIP_URL = (
    "https://ec.europa.eu/esco/download/"
    "ESCO%20dataset%20-%20v1.1.0%20-%20classification%20-%20en%20-%20csv.zip"
)
ESCO_CSV_DIR = ESCO_RAW_DIR / "ESCO_v1.1.0"

ESCO_FILES = [
    SourceFile(
        key="esco_skills",
        path=ESCO_CSV_DIR / "skills_en.csv",
        columns=(
            "conceptType",
            "conceptUri",
            "skillType",
            "reuseLevel",
            "preferredLabel",
            "altLabels",
            "hiddenLabels",
            "status",
            "modifiedDate",
            "scopeNote",
            "definition",
            "inScheme",
            "description",
        ),
        delimiter=",",
        consumer=(
            "Skill node labels: preferred and alternative labels widen the vocabulary SBERT "
            "matches against."
        ),
        min_rows=10000,
    ),
    SourceFile(
        key="esco_occupations",
        path=ESCO_CSV_DIR / "occupations_en.csv",
        columns=(
            "conceptType",
            "conceptUri",
            "iscoGroup",
            "preferredLabel",
            "altLabels",
            "hiddenLabels",
            "status",
            "modifiedDate",
            "regulatedProfessionNote",
            "scopeNote",
            "definition",
            "inScheme",
            "description",
            "code",
        ),
        delimiter=",",
        consumer="Validates crosswalk ESCO URIs and supplies ESCO occupation labels.",
        min_rows=2000,
    ),
    SourceFile(
        key="esco_occupation_skill_relations",
        path=ESCO_CSV_DIR / "occupationSkillRelations_en.csv",
        columns=("occupationUri", "relationType", "skillType", "skillUri"),
        delimiter=",",
        consumer=(
            "ESCO essential/optional skills per ESCO occupation, reached from O*NET through the "
            "crosswalk."
        ),
        min_rows=50000,
    ),
    SourceFile(
        key="esco_skill_skill_relations",
        path=ESCO_CSV_DIR / "skillSkillRelations_en.csv",
        columns=(
            "originalSkillUri",
            "originalSkillType",
            "relationType",
            "relatedSkillType",
            "relatedSkillUri",
        ),
        delimiter=",",
        consumer="Candidate skill-to-skill edges (published by ESCO, not derived).",
        min_rows=1000,
    ),
    SourceFile(
        key="esco_ict_skills_collection",
        path=ESCO_CSV_DIR / "ictSkillsCollection_en.csv",
        columns=(
            "conceptType",
            "conceptUri",
            "skillType",
            "reuseLevel",
            "preferredLabel",
            "status",
            "altLabels",
            "description",
            "broaderConceptUri",
            "broaderConceptPT",
        ),
        delimiter=",",
        consumer="Flags ESCO skills that belong to the official ICT skills collection.",
        min_rows=10,
    ),
]

# ESCO-O*NET occupation crosswalk (ESCO Secretariat with US DOL/ETA), v1, Sep 2022

CROSSWALK_URL = (
    "https://esco.ec.europa.eu/system/files/2023-08/ONET_%28Occupations%29_0_updated.csv"
)
CROSSWALK_FILE = SourceFile(
    key="esco_onet_crosswalk",
    path=ESCO_RAW_DIR / "ONET_Occupations_0_updated.csv",
    columns=(
        "O*NET Id",
        "O*NET Title",
        "O*NET Description",
        "ESCO or ISCO URI",
        "ESCO or ISCO Title",
        "ESCO or ISCO Description",
        "Type of Match",
    ),
    delimiter=",",
    consumer=(
        "Joins O*NET-SOC occupations to ESCO occupations; the only link between the two "
        "vocabularies."
    ),
    header_offset=16,
    encoding="utf-8-sig",
    min_rows=1000,
)

ARCHIVES = [
    Archive(
        name=f"O*NET {ONET_VERSION} text database",
        url=ONET_ZIP_URL,
        zip_path=ONET_RAW_DIR / "db_31_0_text.zip",
        extract_dir=ONET_RAW_DIR,
        manual_steps=(
            "1. Open https://www.onetcenter.org/database.html\n"
            "2. Under 'All Files', download the 'Text' zip for O*NET 31.0 (db_31_0_text.zip).\n"
            "3. Save it as data/raw/onet/db_31_0_text.zip and extract it there, so that\n"
            "   data/raw/onet/db_31_0_text/Occupation Data.txt exists."
        ),
        files=ONET_FILES,
    ),
    Archive(
        name=f"ESCO {ESCO_VERSION} classification (English, CSV)",
        url=ESCO_ZIP_URL,
        zip_path=ESCO_RAW_DIR / "ESCO_dataset_v1.1.0_classification_en_csv.zip",
        extract_dir=ESCO_CSV_DIR,
        manual_steps=(
            "1. Open https://esco.ec.europa.eu/en/use-esco/download\n"
            "2. Choose version ESCO v1.1.0, content 'classification', language 'en', type 'csv'.\n"
            "3. Add to package and download the zip.\n"
            "4. Save it as data/raw/esco/ESCO_dataset_v1.1.0_classification_en_csv.zip and\n"
            "   extract it into data/raw/esco/ESCO_v1.1.0/ so that skills_en.csv sits\n"
            "   directly inside."
        ),
        files=ESCO_FILES,
    ),
]

ALL_FILES = ONET_FILES + ESCO_FILES + [CROSSWALK_FILE]
