# data/

Nothing under `raw/`, `processed/` or `graph/` is committed. Each folder keeps a
`.gitkeep` so the layout survives cloning. Full details of every file, with
licences and row counts, are in `docs/03-data-sources.md`.

| Path | Contents | Produced by | Committed |
|---|---|---|---|
| `tech_occupations.csv` | The 24 O*NET-SOC codes in scope, with domain and evidence | Hand-curated | Yes |
| `raw/onet/` | `db_31_0_text.zip` and its extracted folder `db_31_0_text/` (O*NET 31.0, tab-delimited) | `scripts/download_data.py` | No |
| `raw/esco/` | `ESCO_dataset_v1.1.0_classification_en_csv.zip`, its extracted folder `ESCO_v1.1.0/`, and the crosswalk `ONET_Occupations_0_updated.csv` | `scripts/download_data.py` | No |
| `raw/download_manifest.json` | URL, size, SHA-256 and retrieval time of each download | `scripts/download_data.py` | No |
| `processed/` | Cleaned, scope-filtered CSVs and `prep_report.json` | `scripts/prepare_data.py` | No |
| `graph/` | Serialised knowledge graph, skill embeddings (`.npy`) and their index and metadata | `scripts/build_graph.py`, `scripts/build_embeddings.py` (Sprint 2) | No |

## How to obtain the data

From the project root, with the virtual environment active:

```bash
python scripts/download_data.py      # fetch anything missing, then verify
python scripts/prepare_data.py       # build data/processed/
```

If an automatic download fails, the script prints the manual steps for that
source. In short:

* **O*NET 31.0 text:** https://www.onetcenter.org/database.html, "Text" zip.
  Extract into `raw/onet/` so that `raw/onet/db_31_0_text/Occupation Data.txt`
  exists.
* **ESCO v1.1.0, English CSV:** https://esco.ec.europa.eu/en/use-esco/download.
  Extract into `raw/esco/ESCO_v1.1.0/`.
* **ESCO-O*NET crosswalk:** https://esco.ec.europa.eu/en/use-esco/other-crosswalks.
  Save as `raw/esco/ONET_Occupations_0_updated.csv`.

Check what you have with `python scripts/download_data.py --verify-only` or
`pytest -m data`.
