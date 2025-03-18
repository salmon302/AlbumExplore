# ProgArchives Data Collection Strategy

## Overview

This document outlines the strategy for ethically collecting data from ProgArchives.com to build a comprehensive progressive music database.

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
- Ethical rate limiting
- Caching to minimize requests
- Deduplication with existing CSV data
- Integration with existing tag system

## Architecture

### Components

1. **ProgArchivesScraper**
   - Core scraping functionality
   - Rate limiting and caching
   - HTML parsing
   - Error handling

2. **ProgArchivesParser**
   - Parse cached HTML files
   - Extract structured data
   - Data validation
   - Genre mapping

3. **ProgArchivesImporter**
   - Database integration
   - Deduplication logic
   - Tag system integration
   - Data cleaning

### Data Flow

1. Scraping Phase:
   ```
   URL -> Rate Limited Request -> Cache -> HTML
   ```

2. Parsing Phase:
   ```
   HTML -> Raw Data -> Validated Data -> Structured Records
   ```

3. Import Phase:
   ```
   Structured Records -> Deduplication -> Tag Integration -> Database
   ```

## Implementation Guidelines

### Rate Limiting

- Minimum 5 seconds between requests
- Maximum 1000 requests per day
- Respect robots.txt
- Back off on errors

### Caching

- Cache all HTML responses
- Cache parsed results
- Use local file system storage
- JSON format for parsed data

### Error Handling

- Retry failed requests (max 3 times)
- Log all errors
- Skip problematic records
- Save partial results

## Usage Guide

### Command Line Interface

```bash
# Basic album scraping
python -m albumexplore.cli.scraper_cli scrape <url>

# Search and scrape
python -m albumexplore.cli.scraper_cli search <query>

# Bulk import
python -m albumexplore.cli.scraper_cli import-albums --from-file urls.txt
```

### Scripts

#### Random Sampling
```bash
python -m albumexplore.scripts.scrape_progarchives --max-bands 10 --random-sample
```

#### Full Collection
```bash
python -m albumexplore.scripts.scrape_progarchives --cache-dir cache/progarchives
```

## Development Guidelines

### Code Structure
- Keep scraping, parsing, and importing logic separate
- Use dependency injection
- Write comprehensive tests
- Document all public methods

### Testing Strategy
- Mock HTTP requests in tests
- Use sample HTML fixtures
- Test edge cases
- Validate output format

## Data Quality Checks

- Validate all required fields
- Check date formats
- Verify genre mappings
- Ensure unique records
- Validate artist names

## Monitoring

- Track request rates
- Monitor cache hits/misses
- Log parsing errors
- Track import success rates

## Future Improvements

1. Parallel processing for parsing
2. API development for data access
3. Better genre mapping algorithms
4. Enhanced deduplication logic