# Album Explorer - Data Model Specification

## 1. Core Data Structures

### 1.1 Album Entity
```python
class Album:
	id: str                  # Unique identifier
	artist: str             # Artist name
	title: str              # Album title
	release_date: datetime  # Full release date
	release_year: int       # Extracted year
	length: str             # Album length (LP/EP)
	vocal_style: str        # Vocal classification
	country: str            # Country/location
	tags: List[str]         # Normalized tags
	raw_tags: List[str]     # Original tags before normalization
	platforms: Dict[str, str] # Platform links (Bandcamp, Spotify, etc.)
```

### 1.2 Tag System
```python
class Tag:
	id: str                 # Unique identifier
	name: str               # Normalized tag name
	category: str           # Primary category (genre, style, etc.)
	aliases: List[str]      # Alternative spellings/names
	parent_tags: List[str]  # Broader categories
	related_tags: List[str] # Similar or related tags
	frequency: int          # Usage count
```

### 1.3 Tag Relationships
```python
class TagRelation:
	tag1_id: str           # First tag ID
	tag2_id: str           # Second tag ID
	relationship_type: str  # Type of relationship
	strength: float        # Relationship strength (0-1)
```

## 2. Database Schema

### 2.1 Primary Tables
- albums
- tags
- tag_relationships
- album_tags
- update_history

### 2.2 Indexes
- artist_idx
- release_date_idx
- tag_name_idx
- tag_category_idx

## 3. Data Normalization

### 3.1 Tag Normalization Rules
- Convert to lowercase
- Remove special characters
- Handle common variations
- Merge similar tags
- Map to standard forms

### 3.2 Date Normalization
- Standard format: YYYY-MM-DD
- Year extraction rules
- Partial date handling
- Update tracking format

## 4. Data Relationships

### 4.1 Album-Tag Relationships
- Direct tags
- Inherited tags
- Tag weights
- Relationship strength calculation

### 4.2 Tag-Tag Relationships
- Hierarchical relationships
- Similarity relationships
- Complementary relationships
- Exclusion relationships

## 5. Update Management

### 5.1 Version Control
- Timestamp tracking
- Change history
- Conflict resolution
- Data validation rules

### 5.2 Data Migration
- Format conversion
- Schema updates
- Tag system evolution
- Historical data preservation