# ProgArchives Data Collection Strategy (Local Files)

## Overview

This document outlines the strategy for processing locally downloaded HTML files from ProgArchives.com to build a comprehensive progressive music database. This approach replaces the previous plan of live-scraping the website.

## Requirements

### Data Points
- Album Information
  - Title
  - Artist
  - Genre/Subgenre
  - Record Type (only Studio & Singles/EPs/Fan Club/Promo)
  - Year
  - Ratings
  - Reviews
- Artist Information
  - Names
  - Instrumentation
  - Band Biography/Description

### Technical Requirements
- Parsing of local HTML files.
- Deduplication with existing CSV data.
- Integration with existing tag system.

## Architecture

### Components

1.  **ProgArchivesScraper (Local File Parser)**
    *   Core HTML parsing functionality for local files.
    *   Locates and reads files from a defined local data root.
    *   Error handling for file I/O and parsing.

2.  **ProgArchivesParser (Data Extractor)**
    *   Extracts structured data from parsed HTML content.
    *   Data validation.
    *   Genre mapping.

3.  **ProgArchivesImporter**
    *   Database integration.
    *   Deduplication logic.
    *   Tag system integration.
    *   Data cleaning.

### Data Flow

1.  File Identification Phase:
    ```
    Identify Target HTML Files (e.g., albumXXXX.html, artistYYYY.html) in Local Storage
    ```

2.  Parsing Phase:
    ```
    Local HTML File -> Read Content -> Parse HTML -> Raw Data -> Validated Data -> Structured Records
    ```

3.  Import Phase:
    ```
    Structured Records -> Deduplication -> Tag Integration -> Database
    ```

## Implementation Guidelines

### File Structure
- Assumes a local directory structure mirroring the ProgArchives website (e.g., `ProgArchives Data/Website/ProgArchives/www.progarchives.com/`).
- The `ProgArchivesScraper` will use a base path (`LOCAL_DATA_ROOT`) to locate these files.

### Error Handling
- Log all file reading and parsing errors.
- Skip problematic files/records and report them.
- Save partial results if feasible during batch processing.

## Usage Guide

### Command Line Interface (Updated for Local Files)
The CLI will be adapted to point to local files or directories instead of URLs.

```bash
# Example: Process a single local album HTML file
python -m albumexplore.cli.scraper_cli process-album <path_to_album_html_file>

# Example: Process a single local artist HTML file
python -m albumexplore.cli.scraper_cli process-artist <path_to_artist_html_file>

# Example: Bulk import from a directory of HTML files
python -m albumexplore.cli.scraper_cli import-local-dump --source-dir <path_to_progarchives_data_root>
```

### Scripts (Updated for Local Files)
Scripts will be updated to iterate over local file structures.

#### Example: Processing all downloaded album files
```bash
# This script would internally use ProgArchivesScraper to find and parse files
python -m albumexplore.scripts.process_local_progarchives_dump --data-root "ProgArchives Data/Website/ProgArchives/www.progarchives.com/"
```

## Development Guidelines

### Code Structure
- Keep file reading, parsing, and importing logic separate.
- Use dependency injection where appropriate.
- Write comprehensive tests for local file parsing.
- Document all public methods and their expected file inputs.

### Testing Strategy
- Create a small, representative set of sample HTML files (album pages, artist pages, review pages) for testing.
- Test parsing logic against these local samples.
- Verify correct extraction of all required data points.
- Test handling of malformed or missing HTML elements gracefully.
- Test resolution of relative links within the local file structure (if applicable, e.g., an artist page linking to album files by relative paths that need to be resolved to actual file names).