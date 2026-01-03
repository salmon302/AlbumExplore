# Data Source Expansion Plan & Analysis

## Executive Summary

This document analyzes your proposed data source expansion plan against the existing AlbumExplore implementation. The current architecture is **well-suited** for multi-source data integration, with established patterns for raw data storage, transformation, and database loading.

**Status: Phase 1 (Last.fm) IMPLEMENTED ✅**

---

## Implementation Status

### ✅ Phase 1: Last.fm Integration — COMPLETE

| Component | Status | Location |
|-----------|--------|----------|
| API Client | ✅ Done | `src/albumexplore/scraping/lastfm/client.py` |
| Batch Fetcher | ✅ Done | `src/albumexplore/scraping/lastfm/fetcher.py` |
| Data Transformer | ✅ Done | `src/albumexplore/scraping/lastfm/transform_lastfm_data.py` |
| Database Schema | ✅ Done | Added `mbid`, `lastfm_*` fields to Album/Artist models |
| Alembic Migration | ✅ Done | `alembic/versions/6e2f5522bc50_add_lastfm_mbid_and_source_tracking.py` |
| Album Matcher | ✅ Done | `src/albumexplore/data/matcher.py` |
| ETL Integration | ✅ Done | `src/albumexplore/etl.py` |
| Environment Config | ✅ Done | `.env` with API credentials |
| Unit Tests | ✅ Done | `tests/test_lastfm_client.py`, `tests/test_lastfm_fetcher.py` |

### 🔶 Phase 2: ProgArchives — IMPLEMENTED ✅

| Component | Status | Notes |
|-----------|--------|-------|
| HTML Parser | ✅ Ready | `progarchives_scraper.py` (1546 lines) - Verified with new crawler output |
| Transform Pipeline | ✅ Ready | `transform_progarchives_data.py` |
| Targeted Crawler | ✅ Ready | `src/albumexplore/scraping/progarchives/crawler.py` implemented with pagination |
| Parser Integration | ✅ Ready | `parse_progarchives_site.py` verified to handle new crawler files |

### ❌ Phase 3: Bandcamp — Deferred

Awaiting legal/ethical review before implementation.

---

## How to Use the New Last.fm Integration

### Quick Start

```bash
# 1. Set up environment (already done)
cp .env.template .env
# Edit .env with your API key (already configured)

# 2. Fetch Last.fm data for existing albums (sample of 10)
python -m albumexplore.etl --mode lastfm-fetch --limit 10

# 3. Transform fetched data into database
python -m albumexplore.etl --mode lastfm-transform

# 4. Or run both in one command
python -m albumexplore.etl --mode lastfm-full --limit 100
```

### ETL Commands

| Command | Description |
|---------|-------------|
| `--mode lastfm-fetch` | Fetch Last.fm data for albums in DB |
| `--mode lastfm-transform` | Process raw JSON into database |
| `--mode lastfm-full` | Run fetch + transform |
| `--limit N` | Process only N albums |
| `--force` | Re-fetch even if already cached |
| `--dry-run` | Don't commit DB changes |

### Using the Client Directly

```python
from albumexplore.scraping.lastfm import LastFmClient, LastFmFetcher

# Simple API calls
client = LastFmClient()
album = client.get_album_info("Tool", "Lateralus")
print(f"Playcount: {album['playcount']}")

# Batch fetching with caching
fetcher = LastFmFetcher()
results = fetcher.fetch_albums_batch([
    ("Pink Floyd", "The Wall"),
    ("Tool", "Lateralus"),
])
for r in results:
    if r.success:
        print(f"Got data for {r.artist} - {r.album}")
```

### Using the Album Matcher

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from albumexplore.data.matcher import AlbumMatcher

engine = create_engine("sqlite:///albumexplore.db")
Session = sessionmaker(bind=engine)
session = Session()

matcher = AlbumMatcher(session)

# Match a single album
result = matcher.match(
    artist="Pink Floyd",
    title="The Wall",
    year=1979
)

if result.is_match:
    print(f"Matched: {result.album.title} ({result.confidence:.0%})")
```

---

## Gap Analysis: Your Plan vs. Current State

### 1) Last.fm Integration

**Status: COMPLETE**
- API Client, Fetcher, and Transformer are implemented.
- Schema has been updated with `lastfm_playcount`, `lastfm_listeners`, `lastfm_url`, and `mbid`.
- `etl.py` orchestrator is fully functional.
- Unit tests are passing.

**Your Plan:**
> Build a small connector module (`src/scraping/lastfm.py`) that fetches by `artist+album`

**Current State Analysis:**
- ✅ **API Dependencies Ready**: `requests` is already in `pyproject.toml`
- ✅ **Raw Data Structure Ready**: `raw_data/lastfm/` path follows existing convention
- ✅ **Schema Updated**: Album model now includes Last.fm-specific fields

**Completed Schema Additions:**
```python
# In models.py - Album class
lastfm_playcount = Column(Integer, nullable=True)
lastfm_listeners = Column(Integer, nullable=True)
lastfm_mbid = Column(String, nullable=True, index=True)  # MusicBrainz ID
lastfm_url = Column(String, nullable=True)
```

**Implementation Path:**
```
src/albumexplore/scraping/
├── lastfm/
│   ├── __init__.py
│   ├── client.py           # API wrapper with rate limiting
│   ├── fetcher.py          # Batch fetch logic
│   └── transform_lastfm_data.py  # Normalize to schema
```

**Rate Limiting Consideration:**
Last.fm API allows ~5 requests/second. For 1k albums:
- Sequential: ~3-4 minutes
- With backoff/retries: ~10 minutes
- Recommendation: Add `backoff` decorator (already in dependencies)

---

### 2) ProgArchives Scraping

**Your Plan:**
> Strategy: crawl index pages for target genres / top lists rather than full site

**Current State Analysis:**
- ✅ **Parser Ready**: `progarchives_scraper.py` has comprehensive HTML parsing
- ✅ **Transform Ready**: `transform_progarchives_data.py` is production-ready
- ❌ **Crawler Missing**: `parse_progarchives_site.py` is empty
- ✅ **Raw CSVs Exist**: `pa_raw_albums.csv`, etc. in `raw_data/`

**The "Link Problem" You Mentioned:**
Your concern about "accounting for the massive amount of links" is valid. The current scraper expects local HTML files, not live crawling.

**Recommended Targeted Crawl Strategy:**

```python
# Proposed: src/albumexplore/scraping/progarchives/crawler.py

TARGETED_ENTRY_POINTS = {
    # Genre top lists (curated, manageable)
    "prog_metal": "https://www.progarchives.com/subgenre.asp?style=23",
    "progressive_rock": "https://www.progarchives.com/subgenre.asp?style=1",
    
    # Top rated (quality filter)
    "top_100": "https://www.progarchives.com/top-prog-albums.asp",
}

class TargetedCrawler:
    """Crawl only high-value pages, not the entire site."""
    
    def __init__(self, max_albums_per_genre: int = 500):
        self.max_albums = max_albums_per_genre
        self.seen_urls = set()
        
    def crawl_genre_list(self, genre_url: str) -> List[str]:
        """Get album URLs from a genre listing page."""
        # Parse pagination, extract album links
        # Stop when max_albums reached
        pass
```

**Crawl Budget Estimation:**
| Target | Albums | Pages | Est. Time (2s delay) |
|--------|--------|-------|---------------------|
| Prog Metal Top 500 | 500 | ~25 list + 500 album | ~17 min |
| All Subgenres Top 100 | ~2500 | ~125 list + 2500 album | ~85 min |
| Full Site | ~100,000+ | Massive | Days |

**Recommendation:** Phase 2 should focus on **genre top lists**, not full crawl.

---

### 3) Bandcamp

**Your Plan:**
> Treat Bandcamp as low-priority until legal/ethical clearance

**Agreed.** However, some safe options exist:

**Safe Data Sources from Bandcamp:**
1. **MusicBrainz Links**: Many Bandcamp releases have MBID links embedded
2. **Bandcamp Daily**: Public editorial content (not user data)
3. **Official API**: Bandcamp does have a label API for partners

**Recommendation:** Park this until Phase 3. If pursuing, start with:
- Checking if any of your ProgArchives artists have verified Bandcamp profiles
- Using Bandcamp URLs only as "external links" (store URL, don't scrape content)

---

### 4) Cross-Source Matching

**Your Plan:**
> Primary strategy: Resolve to MusicBrainz MBIDs

**Current State Analysis:**
- ❌ **No MBID fields** in current schema
- ❌ **No fuzzy matching** utilities
- ✅ **Artist name normalization** exists in `enhanced_normalizer.py`

**Schema Changes Needed:**
```python
# models.py additions

class Album(Base):
    # ... existing fields ...
    
    # Cross-source identifiers
    mbid = Column(String(36), nullable=True, index=True)  # MusicBrainz Release ID
    lastfm_url = Column(String, nullable=True)
    discogs_id = Column(Integer, nullable=True)
    
class Artist(Base):
    # ... existing fields ...
    
    mbid = Column(String(36), nullable=True, index=True)  # MusicBrainz Artist ID
    lastfm_url = Column(String, nullable=True)

# New: Source provenance tracking
class AlbumSource(Base):
    """Track which sources contributed to an album's data."""
    __tablename__ = "album_sources"
    
    id = Column(Integer, primary_key=True)
    album_id = Column(String, ForeignKey('albums.id'), nullable=False)
    source_name = Column(String, nullable=False)  # 'progarchives', 'lastfm', 'bandcamp'
    source_id = Column(String, nullable=True)     # Source-specific ID
    confidence = Column(Float, default=1.0)
    last_fetched = Column(DateTime)
    raw_data_path = Column(String, nullable=True) # Path to raw JSON/HTML
```

**Matching Algorithm Recommendation:**
```python
# src/albumexplore/data/matcher.py

from rapidfuzz import fuzz  # Already using Levenshtein

class AlbumMatcher:
    """Match albums across data sources."""
    
    MATCH_THRESHOLDS = {
        'mbid_exact': 1.0,          # Perfect match
        'artist_album_fuzzy': 0.85, # High confidence
        'tracklist_jaccard': 0.70,  # Moderate confidence
    }
    
    def match(self, source_album: dict, target_album: Album) -> float:
        """Return confidence score 0-1 for match."""
        
        # 1. MBID exact match (if both have it)
        if source_album.get('mbid') and target_album.mbid:
            if source_album['mbid'] == target_album.mbid:
                return 1.0
        
        # 2. Artist + Album fuzzy match
        artist_score = fuzz.ratio(
            source_album['artist'].lower(),
            target_album.pa_artist_name_on_album.lower()
        ) / 100
        
        title_score = fuzz.ratio(
            source_album['title'].lower(),
            target_album.title.lower()
        ) / 100
        
        combined = (artist_score * 0.4) + (title_score * 0.6)
        
        # 3. Year tolerance bonus
        if source_album.get('year') and target_album.release_year:
            year_diff = abs(source_album['year'] - target_album.release_year)
            if year_diff <= 1:
                combined *= 1.1  # Boost
        
        return min(combined, 1.0)
```

---

## Revised Implementation Plan

### Phase 1: Last.fm Integration (Week 1) — **HIGH PRIORITY**

| Day | Task |
|-----|------|
| 1 | Create `src/albumexplore/scraping/lastfm/client.py` with rate limiting |
| 1 | Add Alembic migration for `lastfm_*` fields |
| 2 | Implement `fetcher.py` to query by artist+album |
| 2 | Store raw JSON in `raw_data/lastfm/` |
| 3 | Create `transform_lastfm_data.py` following ProgArchives pattern |
| 3 | Map Last.fm tags to existing tag normalizer |
| 4 | Add to `etl.py` orchestrator |
| 5 | Test with sample of 100 albums from existing DB |

**Deliverables:**
- [ ] `src/albumexplore/scraping/lastfm/` module
- [ ] Alembic migration for schema changes
- [ ] Integration into `etl.py --source lastfm`

### Phase 2: ProgArchives Targeted Crawl (Weeks 2-3) — **MEDIUM PRIORITY**

| Day | Task |
|-----|------|
| 1-2 | Implement `crawler.py` with targeted entry points |
| 3 | Add `robots.txt` compliance and rate limiting |
| 4-5 | Test crawl of single subgenre (Prog Metal top 100) |
| 6-7 | Validate data quality against existing transforms |
| 8-10 | Full crawl of priority subgenres |

**Key Decisions:**
- Use `pyppeteer` (already in deps) only if JavaScript rendering needed
- Default to `requests + BeautifulSoup` for static pages
- Implement checkpoint/resume for long crawls

### Phase 3: Cross-Source Matching (Week 4) — **FOUNDATIONAL**

| Day | Task |
|-----|------|
| 1-2 | Add `AlbumSource` model and migration |
| 3 | Implement `matcher.py` with fuzzy matching |
| 4 | Create merge policy (keep all values with provenance) |
| 5 | Test matching between ProgArchives and Last.fm data |

### Phase 4: Bandcamp Investigation (Future)

- Legal review of Bandcamp TOS
- Explore MusicBrainz as proxy for Bandcamp data
- Consider official API partnership for labels

---

## Dependencies to Add

```toml
# pyproject.toml additions
dependencies = [
    # ... existing ...
    "rapidfuzz>=3.0.0",      # Better fuzzy matching (drop python-Levenshtein)
    "musicbrainzngs>=0.7.1", # MusicBrainz API client
    "aiohttp>=3.8.0",        # Async HTTP for parallel fetching (optional)
]
```

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Last.fm API deprecation | Store raw JSON; fields are stable |
| ProgArchives blocks scraping | Respect robots.txt; consider contacting site owner |
| Duplicate albums across sources | Implement matcher.py before large imports |
| Schema migrations break existing data | Use Alembic; always backup before migration |

---

## Metrics for Success

1. **Last.fm Coverage**: 80%+ of existing albums enriched with playcount/tags
2. **ProgArchives**: 5,000+ new albums from targeted crawl
3. **Match Rate**: 90%+ albums successfully matched across sources
4. **Data Quality**: <5% albums with missing critical fields after merge

---

## Next Steps

1. **Confirm Phase 1 scope**: Start with Last.fm connector?
2. **Review schema changes**: Approve MBID + AlbumSource additions?
3. **Set up test environment**: Isolated DB for integration testing?

---

## Appendix: Your API Credentials

```
Last.fm API Key: 269626a765bbfeb27f2661cbdfdcce47
Shared Secret: a652f4625d3159fdb7c142f989e01595
```

**Security Note:** These should be moved to environment variables or a `.env` file (not committed to git) before implementation.
