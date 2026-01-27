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

1.  **ProgArchivesCollector**
    *   Manages the collection of files (downloading or identifying local files).
    *   Locates and reads files from a defined local data root.

2.  **ProgArchivesParser** (formerly ProgArchivesScraper)
    *   Core HTML parsing functionality.
    *   Extracts structured data from parsed HTML content.
    *   Data validation and genre mapping.

3.  **ProgArchivesTransformer**
    *   Database integration.
    *   Deduplication logic.
    *   Tag system integration.
    *   Data cleaning and Source-agnostic transformation.

### Data Flow

1.  File Identification Phase:
    
    Identify Target HTML Files (e.g., albumXXXX.html, artistYYYY.html) in Local Storage via Collector
    

2.  Parsing Phase:
    
    Local HTML File -> ProgArchivesParser -> Structured Records (JSON/Dict)
    

3.  Extraction Phase (Batch):
    
    Structured Records -> CSV Extraction (extract_csvs.py)
    

4.  Import Phase:
    
    CSV Data -> ProgArchivesTransformer -> Database (AlbumSource/ArtistSource tables)
    

## Implementation Guidelines

### File Structure
- Assumes a local directory structure mirroring the ProgArchives website (e.g., ProgArchives Data/Website/ProgArchives/www.progarchives.com/).
- The ProgArchivesParser will use a base path (LOCAL_DATA_ROOT) to locate these files.

### Error Handling
- Log all file reading and parsing errors.
- Skip problematic files/records and report them.
- Save partial results if feasible during batch processing.

## Usage Guide

### Command Line Interface (Updated for Local Files)
The CLI will be adapted to point to local files or directories instead of URLs.

`ash
# Example: Process a single local album HTML file
python -m albumexplore.scripts.process_single_file <path_to_album_html_file>
`

### Scripts (Updated for Local Files)
Scripts will be updated to iterate over local file structures.

#### Example: Processing all downloaded album files
`ash
# This script internally uses ProgArchivesParser to extract data to CSVs
python -m albumexplore.scraping.extract_csvs
`

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
- Test resolution of relative links within the local file structure.
