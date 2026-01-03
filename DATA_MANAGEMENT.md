# Data Management & Architecture Guide

## 1. Overview & Goals

This document outlines the data architecture for **AlbumExplore**. The system is designed to ingest music data from multiple sources (ProgArchives, Last.fm, Bandcamp), normalize it into a canonical format, and provide a rich query interface with a focus on **Tag Analysis** and **Music Discovery**.

### Core Principles
- **Provenance**: Every data point should be traceable to its source (e.g., "Rating: 4.5 from ProgArchives").
- **Immutability (Raw)**: Raw scraped data (HTML, JSON) is stored permanently in `raw_data/` before processing.
- **Normalization**: Data is cleaned and mapped to a canonical schema in the SQLite database.
- **Tag Intelligence**: A sophisticated tag system decomposes complex genre tags into "Atomic Tags" for better analysis.

---

## 2. Data Architecture Layers

### Layer 1: Raw Data (`raw_data/`)
Stores unmodified snapshots from external sources.
- **Structure**: `raw_data/<source>/<date>/<filename>`
- **Format**: HTML (ProgArchives), JSON (Last.fm API), CSV (Manual exports).
- **Manifest**: `raw_data/<source>/MANIFEST.json` tracks ingestion history.

### Layer 2: Staging & Transformation
Python scripts in `src/albumexplore/scraping/` and `src/albumexplore/data/` process raw files.
- **Parsers**: Extract structured data from HTML/JSON.
  - *Expanded Metadata (Dec 2025)*: Now extracts full release dates, record labels, production credits, guest musicians, and review IDs.
- **Cleaners**: Fix encoding, normalize dates, standardize artist names.
- **Tag Normalizer**: Maps raw tags to the canonical Tag Dictionary.

### Layer 3: Canonical Storage (`data/data.db`)
A SQLite database managed via **SQLAlchemy**.
- **Schema**: Defined in `src/albumexplore/database/models.py`.
- **Key Models**:
  - `Album`: The central entity.
  - `Artist`: Linked to albums.
  - `Track`: Tracklists.
  - `Review`: Text reviews and ratings.
  - `Tag` / `AtomicTag`: The tag intelligence layer.

---

## 3. The Tag Management System (TMS)

The project features a unique, advanced tagging system designed to handle the messiness of music genres.

### Concepts
1.  **Raw Tags**: Strings as they appear in sources (e.g., "Technical Progressive Death Metal").
2.  **Canonical Tags (`Tag`)**: The standardized version of a tag in our DB.
3.  **Atomic Tags (`AtomicTag`)**: Fundamental, indivisible concepts (e.g., "Technical", "Progressive", "Death Metal").
4.  **Decomposition**: The process of breaking a Composite Tag into Atomic Tags.
    - *Example*: "Symphonic Prog" -> `AtomicTag("Symphonic")` + `AtomicTag("Progressive Rock")`.

### Tag Tables
- `tags`: Main registry of tags.
- `atomic_tags`: The fundamental building blocks.
- `tag_decompositions`: Rules mapping `tags` -> `atomic_tags`.
- `tag_hierarchy`: Parent/Child relationships (e.g., "Thrash Metal" is a child of "Metal").
- `tag_variants`: Synonyms (e.g., "Prog Rock" -> "Progressive Rock").

---

## 4. ETL Pipeline & Workflows

### Standard Workflow
1.  **Scrape**: Run scrapers to fetch new data into `raw_data/`.
    ```bash
    python -m albumexplore.scraping.parse_progarchives_site
    ```
2.  **Transform**: Process raw data into intermediate structures.
    ```bash
    python -m albumexplore.scraping.transform_progarchives_data
    ```
3.  **Load/Merge**: Update the database.
    ```bash
    python -m albumexplore.database.update_manager
    ```

### Ad-Hoc Analysis
Scripts for specific analysis tasks should be placed in `src/albumexplore/scripts/` rather than the project root.

---

## 5. Directory Structure Plan

To maintain a clean workspace, we are migrating towards this structure:

```text
AlbumExplore/
├── data/                   # SQLite DB, active exports
├── raw_data/               # Immutable source data
├── src/
│   └── albumexplore/
│       ├── data/           # Data processing logic
│       ├── database/       # Models, CRUD, Loaders
│       ├── scraping/       # Scrapers & Parsers
│       ├── tags/           # Tag logic (normalization, hierarchy)
│       ├── scripts/        # (NEW) Place for ad-hoc analysis scripts
│       └── visualization/  # Plotting & UI code
├── tests/                  # Unit & Integration tests
└── DATA_MANAGEMENT.md      # This file
```

## 6. Implementation Roadmap

1.  **Consolidate Scripts**: Move root-level `analyze_*.py` and `check_*.py` scripts into `src/albumexplore/scripts/`.
2.  **Refine Tag Logic**: Centralize tag normalization logic in `src/albumexplore/tags/`.
3.  **Unified Loader**: Create a single entry point (`etl.py`) that orchestrates the Scrape -> Transform -> Load process.
4.  **Validation**: Add data quality checks (e.g., "Warn if Album has no Artist").

## 7. Operational Details

- **Backups**: Before any bulk operation, backup `data/data.db`.
- **Schema Changes**: Use Alembic for migrations (configured in `alembic.ini`).
- **Logging**: All ETL scripts should log to `logs/etl.log`.
