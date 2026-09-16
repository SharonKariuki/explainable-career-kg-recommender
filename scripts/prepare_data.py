"""
Clean the raw O*NET and ESCO files and restrict them to the technology scope.

Usage (from the project root, virtual environment active):

    python scripts/prepare_data.py

Input:  data/raw/ (verified by scripts/download_data.py)
        data/tech_occupations.csv (the approved technology occupation scope)
Output: data/processed/*.csv and data/processed/prep_report.json

This is data preparation only. It filters, reshapes, validates and joins
tables using identifiers published in the sources. It does not build graph
nodes or edges, compute embeddings, or apply any similarity-based mapping;
those steps belong to scripts/build_graph.py and scripts/build_embeddings.py
(Sprint 2).

Outputs:
    onet_occupations.csv          scope occupations with title, description, domain
    onet_occupation_ratings.csv   essential skills, transferable skills and knowledge,
                                  one row per (occupation, element) with IM and LV
    onet_elements.csv             descriptions of the rated skill/knowledge elements
    onet_software_skills.csv      technologies used by scope occupations
    onet_related_occupations.csv  related-occupation pairs with both ends in scope
    onet_job_titles.csv           alternate titles for scope occupations
    onet_esco_crosswalk.csv       crosswalk rows for scope occupations
    esco_occupation_skills.csv    ESCO skills of the crosswalked ESCO occupations
    esco_skills.csv               labels and metadata for those ESCO skills
    esco_skill_relations.csv      ESCO skill-to-skill relations within that set
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.data_manifest import (  # noqa: E402
    ALL_FILES,
    CROSSWALK_FILE,
    ESCO_VERSION,
    ONET_VERSION,
    PROCESSED_DIR,
    TECH_SCOPE_FILE,
)

log = logging.getLogger("prepare_data")

SOURCES = {source.key: source for source in ALL_FILES}
RATING_FILES = {
    "onet_essential_skills": "essential_skill",
    "onet_transferable_skills": "transferable_skill",
    "onet_knowledge": "knowledge",
}
ESCO_OCCUPATION_PREFIX = "http://data.europa.eu/esco/occupation/"
ESCO_ISCO_PREFIX = "http://data.europa.eu/esco/isco/"


def read_source(key):
    source = SOURCES[key]
    return pd.read_csv(
        source.path,
        sep=source.delimiter,
        dtype=str,
        keep_default_na=False,
        encoding=source.encoding,
        skiprows=source.header_offset,
    )


def strip_all(frame):
    return frame.apply(lambda column: column.str.strip())


def load_scope():
    scope = pd.read_csv(TECH_SCOPE_FILE, dtype=str, keep_default_na=False)
    if scope["onet_soc_code"].duplicated().any():
        raise ValueError(f"Duplicate occupation codes in {TECH_SCOPE_FILE}")
    return scope


def prepare_occupations(scope, report):
    raw = strip_all(read_source("onet_occupation_data"))
    report["raw_rows"]["onet_occupation_data"] = len(raw)
    missing = set(scope["onet_soc_code"]) - set(raw["O*NET-SOC Code"])
    if missing:
        raise ValueError(f"Scope codes not found in O*NET {ONET_VERSION}: {sorted(missing)}")
    occupations = raw.rename(
        columns={
            "O*NET-SOC Code": "onet_soc_code",
            "Title": "title",
            "Description": "description",
        }
    ).merge(scope[["onet_soc_code", "domain"]], on="onet_soc_code", how="inner")
    return occupations.sort_values("onet_soc_code").reset_index(drop=True)


def scale_bounds():
    scales = strip_all(read_source("onet_scales_reference")).set_index("Scale ID")
    bounds = {}
    for scale_id in ("IM", "LV"):
        bounds[scale_id] = (
            float(scales.loc[scale_id, "Minimum"]),
            float(scales.loc[scale_id, "Maximum"]),
        )
    return bounds


def prepare_ratings(codes, report):
    bounds = scale_bounds()
    report["scale_bounds"] = {k: {"min": v[0], "max": v[1]} for k, v in bounds.items()}
    frames = []
    for key, category in RATING_FILES.items():
        raw = strip_all(read_source(key))
        report["raw_rows"][key] = len(raw)
        subset = raw[raw["O*NET-SOC Code"].isin(codes)].copy()
        subset["Data Value"] = pd.to_numeric(subset["Data Value"], errors="raise")

        duplicated = subset.duplicated(["O*NET-SOC Code", "Element ID", "Scale ID"])
        if duplicated.any():
            raise ValueError(f"{key}: duplicate (occupation, element, scale) rows")

        values = subset.pivot(
            index=["O*NET-SOC Code", "Element ID", "Element Name"],
            columns="Scale ID",
            values="Data Value",
        )
        suppress = (
            subset.assign(flag=subset["Recommend Suppress"].eq("Y"))
            .groupby(["O*NET-SOC Code", "Element ID"])["flag"]
            .any()
        )
        not_relevant = (
            subset[subset["Scale ID"] == "LV"]
            .assign(flag=lambda f: f["Not Relevant"].eq("Y"))
            .set_index(["O*NET-SOC Code", "Element ID"])["flag"]
        )
        frame = values.reset_index().rename(
            columns={
                "O*NET-SOC Code": "onet_soc_code",
                "Element ID": "element_id",
                "Element Name": "element_name",
                "IM": "importance",
                "LV": "level",
            }
        )
        key_index = pd.MultiIndex.from_frame(frame[["onet_soc_code", "element_id"]])
        frame["recommend_suppress"] = suppress.reindex(key_index).to_numpy()
        frame["not_relevant"] = not_relevant.reindex(key_index).fillna(False).to_numpy()
        frame["category"] = category
        frames.append(frame)

    ratings = pd.concat(frames, ignore_index=True)
    if ratings[["importance", "level"]].isna().any().any():
        raise ValueError("Some rated elements lack an IM or LV value")

    im_min, im_max = bounds["IM"]
    lv_min, lv_max = bounds["LV"]
    ratings["importance_norm"] = ((ratings["importance"] - im_min) / (im_max - im_min)).round(4)
    ratings["level_norm"] = ((ratings["level"] - lv_min) / (lv_max - lv_min)).round(4)

    columns = [
        "onet_soc_code",
        "category",
        "element_id",
        "element_name",
        "importance",
        "level",
        "importance_norm",
        "level_norm",
        "recommend_suppress",
        "not_relevant",
    ]
    ratings = ratings[columns].sort_values(["onet_soc_code", "category", "element_id"])

    per_occupation = ratings.groupby(["onet_soc_code", "category"]).size().unstack(fill_value=0)
    report["ratings_per_occupation"] = {
        "min": per_occupation.min().to_dict(),
        "max": per_occupation.max().to_dict(),
    }
    unrated = sorted(set(codes) - set(ratings["onet_soc_code"]))
    report["occupations_without_ratings"] = unrated
    if unrated:
        log.warning("Scope occupations with no skill/knowledge ratings: %s", unrated)
    return ratings.reset_index(drop=True)


def prepare_elements(ratings):
    reference = strip_all(read_source("onet_content_model_reference")).rename(
        columns={
            "Element ID": "element_id",
            "Element Name": "element_name",
            "Description": "description",
        }
    )
    used = ratings[["element_id", "category"]].drop_duplicates()
    elements = used.merge(reference, on="element_id", how="left")
    if elements["description"].isna().any():
        raise ValueError("Rated elements missing from Content Model Reference")
    return elements[["element_id", "element_name", "category", "description"]].sort_values(
        "element_id"
    )


def prepare_software(codes, report):
    raw = strip_all(read_source("onet_software_skills"))
    report["raw_rows"]["onet_software_skills"] = len(raw)
    subset = raw[raw["O*NET-SOC Code"].isin(codes)].rename(
        columns={
            "O*NET-SOC Code": "onet_soc_code",
            "Workplace Example": "technology_name",
            "Element ID": "commodity_id",
            "Element Name": "commodity_name",
            "Hot Technology": "hot_technology",
            "In Demand": "in_demand",
        }
    )
    subset = subset.assign(
        hot_technology=subset["hot_technology"].eq("Y"),
        in_demand=subset["in_demand"].eq("Y"),
    ).drop_duplicates()
    return subset.sort_values(["onet_soc_code", "technology_name"]).reset_index(drop=True)


def prepare_related(codes, report):
    raw = strip_all(read_source("onet_related_occupations"))
    report["raw_rows"]["onet_related_occupations"] = len(raw)
    from_scope = raw[raw["O*NET-SOC Code"].isin(codes)]
    both = from_scope[from_scope["Related O*NET-SOC Code"].isin(codes)]
    report["related_pairs_from_scope_total"] = len(from_scope)
    related = both.rename(
        columns={
            "O*NET-SOC Code": "onet_soc_code",
            "Related O*NET-SOC Code": "related_onet_soc_code",
            "Relatedness Tier": "relatedness_tier",
            "Index": "relatedness_index",
        }
    ).astype({"relatedness_index": int})
    return related.sort_values(["onet_soc_code", "relatedness_index"]).reset_index(drop=True)


def prepare_job_titles(codes, report):
    raw = strip_all(read_source("onet_job_titles"))
    report["raw_rows"]["onet_job_titles"] = len(raw)
    titles = raw[raw["O*NET-SOC Code"].isin(codes)].rename(
        columns={
            "O*NET-SOC Code": "onet_soc_code",
            "Job Title": "job_title",
            "Short Title": "short_title",
            "Source(s)": "sources",
        }
    )
    titles = titles.assign(short_title=titles["short_title"].replace("n/a", ""))
    return (
        titles.drop_duplicates().sort_values(["onet_soc_code", "job_title"]).reset_index(drop=True)
    )


def prepare_crosswalk(codes, esco_occupations, report):
    raw = strip_all(read_source(CROSSWALK_FILE.key))
    raw = raw[raw["O*NET Id"] != ""]
    report["raw_rows"]["esco_onet_crosswalk"] = len(raw)
    report["crosswalk_match_types_all"] = raw["Type of Match"].value_counts().to_dict()

    subset = raw[raw["O*NET Id"].isin(codes)].rename(
        columns={
            "O*NET Id": "onet_soc_code",
            "ESCO or ISCO URI": "esco_uri",
            "ESCO or ISCO Title": "esco_title",
            "Type of Match": "match_type",
        }
    )[["onet_soc_code", "esco_uri", "esco_title", "match_type"]]

    subset["uri_type"] = "other"
    subset.loc[subset["esco_uri"].str.startswith(ESCO_OCCUPATION_PREFIX), "uri_type"] = (
        "esco_occupation"
    )
    subset.loc[subset["esco_uri"].str.startswith(ESCO_ISCO_PREFIX), "uri_type"] = "isco_group"
    known = set(esco_occupations["conceptUri"])
    subset["uri_in_esco"] = subset["esco_uri"].isin(known)

    stale = subset[(subset["uri_type"] == "esco_occupation") & ~subset["uri_in_esco"]]
    report["crosswalk_scope"] = {
        "rows": len(subset),
        "match_types": subset["match_type"].value_counts().to_dict(),
        "uri_types": subset["uri_type"].value_counts().to_dict(),
        "occupation_uris_not_in_esco_" + ESCO_VERSION: len(stale),
        "scope_occupations_with_esco_occupation_match": int(
            subset.loc[subset["uri_in_esco"], "onet_soc_code"].nunique()
        ),
        "scope_occupations_without_any_match": sorted(set(codes) - set(subset["onet_soc_code"])),
    }
    return (
        subset.drop_duplicates().sort_values(["onet_soc_code", "esco_uri"]).reset_index(drop=True)
    )


def prepare_esco(crosswalk, esco_occupations, report):
    relations = strip_all(read_source("esco_occupation_skill_relations"))
    skills = strip_all(read_source("esco_skills"))
    skill_relations = strip_all(read_source("esco_skill_skill_relations"))
    ict = strip_all(read_source("esco_ict_skills_collection"))
    report["raw_rows"].update(
        {
            "esco_occupations": len(esco_occupations),
            "esco_occupation_skill_relations": len(relations),
            "esco_skills": len(skills),
            "esco_skill_skill_relations": len(skill_relations),
            "esco_ict_skills_collection": len(ict),
        }
    )

    mapped = crosswalk[crosswalk["uri_in_esco"]][["onet_soc_code", "esco_uri", "match_type"]]
    occupation_skills = mapped.merge(
        relations, left_on="esco_uri", right_on="occupationUri", how="inner"
    ).rename(
        columns={
            "esco_uri": "esco_occupation_uri",
            "match_type": "crosswalk_match_type",
            "relationType": "relation_type",
            "skillType": "skill_type",
            "skillUri": "skill_uri",
        }
    )[
        [
            "onet_soc_code",
            "esco_occupation_uri",
            "crosswalk_match_type",
            "relation_type",
            "skill_type",
            "skill_uri",
        ]
    ]
    occupation_skills = occupation_skills.drop_duplicates().sort_values(
        ["onet_soc_code", "esco_occupation_uri", "relation_type", "skill_uri"]
    )

    used = set(occupation_skills["skill_uri"])
    missing = used - set(skills["conceptUri"])
    report["esco_skill_uris_missing_from_skills_file"] = len(missing)

    ict_uris = set(ict["conceptUri"])
    esco_skills = skills[skills["conceptUri"].isin(used)].copy()
    esco_skills = pd.DataFrame(
        {
            "skill_uri": esco_skills["conceptUri"],
            "preferred_label": esco_skills["preferredLabel"],
            # altLabels are newline separated in the ESCO CSV; store pipe separated.
            "alt_labels": esco_skills["altLabels"].map(
                lambda s: "|".join(part.strip() for part in s.splitlines() if part.strip())
            ),
            "skill_type": esco_skills["skillType"],
            "reuse_level": esco_skills["reuseLevel"],
            "status": esco_skills["status"],
            "in_ict_collection": esco_skills["conceptUri"].isin(ict_uris),
            "description": esco_skills["description"].str.replace(r"\s+", " ", regex=True),
        }
    ).sort_values("preferred_label")

    within = skill_relations[
        skill_relations["originalSkillUri"].isin(used)
        & skill_relations["relatedSkillUri"].isin(used)
    ].rename(
        columns={
            "originalSkillUri": "skill_uri",
            "relationType": "relation_type",
            "relatedSkillUri": "related_skill_uri",
        }
    )[
        ["skill_uri", "relation_type", "related_skill_uri"]
    ]

    report["esco_scope"] = {
        "occupation_skill_rows": len(occupation_skills),
        "relation_types": occupation_skills["relation_type"].value_counts().to_dict(),
        "distinct_skills": len(esco_skills),
        "skills_in_ict_collection": int(esco_skills["in_ict_collection"].sum()),
        "skill_types": esco_skills["skill_type"].value_counts().to_dict(),
        "alt_label_count": int(
            esco_skills["alt_labels"].map(lambda s: len(s.split("|")) if s else 0).sum()
        ),
    }
    return occupation_skills.reset_index(drop=True), esco_skills.reset_index(drop=True), within


def write(frame, name, report):
    path = PROCESSED_DIR / name
    frame.to_csv(path, index=False, encoding="utf-8")
    report["outputs"][name] = len(frame)
    log.info("Wrote %-32s %7d rows", name, len(frame))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare processed CSVs from raw sources.")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    missing = [str(s.path) for s in ALL_FILES if not s.path.exists()]
    if missing:
        log.error(
            "Raw files missing. Run `python scripts/download_data.py` first.\n  %s",
            "\n  ".join(missing),
        )
        return 1

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "onet_version": ONET_VERSION,
        "esco_version": ESCO_VERSION,
        "raw_rows": {},
        "outputs": {},
    }

    scope = load_scope()
    codes = set(scope["onet_soc_code"])
    report["scope_occupations"] = len(codes)
    report["scope_domains"] = scope["domain"].value_counts().to_dict()

    occupations = prepare_occupations(scope, report)
    ratings = prepare_ratings(codes, report)
    elements = prepare_elements(ratings)
    software = prepare_software(codes, report)
    related = prepare_related(codes, report)
    titles = prepare_job_titles(codes, report)

    esco_occupations = strip_all(read_source("esco_occupations"))
    crosswalk = prepare_crosswalk(codes, esco_occupations, report)
    occupation_skills, esco_skills, skill_relations = prepare_esco(
        crosswalk, esco_occupations, report
    )

    write(occupations, "onet_occupations.csv", report)
    write(ratings, "onet_occupation_ratings.csv", report)
    write(elements, "onet_elements.csv", report)
    write(software, "onet_software_skills.csv", report)
    write(related, "onet_related_occupations.csv", report)
    write(titles, "onet_job_titles.csv", report)
    write(crosswalk, "onet_esco_crosswalk.csv", report)
    write(occupation_skills, "esco_occupation_skills.csv", report)
    write(esco_skills, "esco_skills.csv", report)
    write(skill_relations, "esco_skill_relations.csv", report)

    report_path = PROCESSED_DIR / "prep_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    log.info("Report written to %s", report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
