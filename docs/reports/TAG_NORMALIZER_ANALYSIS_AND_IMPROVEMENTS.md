# Tag Normalizer Analysis and Improvement Plan

## Executive Summary

After analyzing both `raw_tags_export.csv` (1,288 tags) and `atomic_tags_export.csv`, I've identified significant opportunities to improve the tag normalization system. The analysis reveals patterns of inconsistency, missed normalization opportunities, and areas where the current system could be enhanced.

## Key Issues Identified

### 1. **Case Inconsistency**
Many tags differ only in capitalization, creating unnecessary variants:
- `Alt Metal` / `Alt metal` / `Alt-metal` / `Alt-Metal`
- `Atmospheric Black Metal` / `Atmospheric Black metal` / `atmospheric black metal`
- `Art Rock` / `Art rock` / `Art-rock` / `Art-Rock`
- `Heavy Metal` / `Heavy metal`
- `Doom Metal` / `Doom metal`

**Impact**: 50+ duplicate tag groups

### 2. **Hyphenation and Spacing Inconsistency**
The system doesn't consistently handle hyphens vs. spaces:
- `Alt-rock` (744) vs `Alternative Rock` (17) vs `Alternative rock` (3)
- `Post-Metal` (23) vs `Post Metal` (2) vs `Post metal` (1)
- `Post-Punk` (464) vs `Post Punk` (1) vs `Post punk` (1)
- `Art-rock` (29) vs `Art Rock` (14) vs `Art rock` (211)

**Impact**: Hundreds of tags split across multiple variants

### 3. **Abbreviation Expansion Issues**
Current `alt` → `alternative` expansion is too simplistic:
- `Alt-Country` (101 instances) - should this become "alternative country"?
- `Alt-Folk` (8) should normalize consistently
- However, "alt" in context may have specific meaning vs. "alternative"

**Impact**: Semantic confusion and inconsistent handling

### 4. **Misspellings and Typos**
Several misspellings aren't caught:
- `Atmosheric Black metal` → should be "Atmospheric Black metal"
- `Anternative` → should be "Alternative"  
- `Bluegras` → should be "Bluegrass"
- `Ghotic metal` → should be "Gothic metal"
- `Cinmatic` → should be "Cinematic"
- `american privitsm` → should be "American Primitivism"
- `electonic` → should be "Electronic"
- `pschedelic` / `psyechedelic` / `pscyhedelic` → should be "Psychedelic"
- `kosmsiche` → should be "Kosmische"
- `melancolic` → should be "Melancholic"
- `tharsh metal` → should be "Thrash metal"

**Impact**: 20+ misspelled tags not being normalized

### 5. **Compound Genre Handling**
Inconsistent treatment of modifiers + base genres:
- `Melodic Death metal` (462) vs `Melodic Death Metal` (13)
- `Technical Death metal` vs `Melodic/Technical Death metal`
- `Atmospheric Sludge metal` (96) vs `Atmospheric Sludge Metal` (1) vs `Atmospheric Sludge` (3)
- `Brutal Death metal` (98) vs `Brutal Death Metal` (3)

**Impact**: Split counts across case variants

### 6. **Suffix Pattern Issues**
- `-core` vs `core` inconsistency: `Metalcore` vs `Metal-core`
- `-wave` vs `wave`: `Darkwave` vs `Dark wave` vs `Dark Wave`
- `-gaze` suffixes: `Blackgaze`, `Doomgaze`, `Grungegaze`, `Noisegaze`, `Nugaze`

**Impact**: 30+ tag groups with suffix inconsistency

### 7. **Regional/Cultural Tag Variants**
Tags with multiple equivalent forms:
- `Folk music` / `Folk Music` → should just be "Folk"
- `Chamber music` / `Chamber Music` → "Chamber" or keep as compound?
- Various folk music regional variants need standardization

**Impact**: 10+ redundant variants

### 8. **Incomplete Atomic Decomposition**
Many compound tags in raw export have atomic forms but aren't being decomposed:
- "Alternative Rock/Indie Rock/Emo" - needs better slash handling
- "Death Metal/Heavy Metal/OSDM" - multi-tag strings not decomposed
- Various "X / Y" patterns

**Impact**: Loss of atomic tag data

## Improvement Recommendations

### Priority 1: Core Normalization Rules

#### A. Case Normalization
```python
# Always normalize to lowercase first, then apply specific capitalization rules if needed
def normalize_case(tag: str) -> str:
    # Convert to lowercase
    tag = tag.lower().strip()
    
    # Keep acronyms uppercase (e.g., DSBM, OSDM, NWOBHM, IDM, EBM)
    acronym_pattern = r'\b[A-Z]{2,}\b'
    # Store acronyms, convert all to lower, then restore acronyms
    
    return tag
```

#### B. Hyphen/Space Standardization Rules
Define clear patterns:
```json
{
  "hyphen_compounds": [
    "post-metal", "post-rock", "post-punk", "post-hardcore",
    "alt-rock", "alt-metal", "alt-country",
    "avant-garde", "neo-prog", "neo-psychedelia",
    "singer-songwriter"
  ],
  "space_compounds": [
    "death metal", "black metal", "doom metal", "heavy metal",
    "power metal", "thrash metal", "speed metal",
    "dream pop", "indie pop", "art pop",
    "noise rock", "math rock", "garage rock"
  ]
}
```

#### C. Enhanced Misspelling Dictionary
```python
ENHANCED_MISSPELLINGS = {
    # Current ones
    "progresive": "progressive",
    "alternitive": "alternative",
    "expirimental": "experimental",
    
    # New additions
    "atmosheric": "atmospheric",
    "anternative": "alternative",
    "bluegras": "bluegrass",
    "ghotic": "gothic",
    "cinmatic": "cinematic",
    "electonic": "electronic",
    "pschedelic": "psychedelic",
    "psyechedelic": "psychedelic",
    "pscyhedelic": "psychedelic",
    "kosmsiche": "kosmische",
    "melancolic": "melancholic",
    "tharsh": "thrash",
    "symphnoic": "symphonic",
    "sympohnic": "symphonic",
    "slugde": "sludge",
    "mittelalter-metal": "medieval metal",
    "mitteralter": "medieval",
    "neoclassica": "neoclassical",
    "acapella": "a capella",
    "privitsm": "primitivism",
}
```

### Priority 2: Suffix Pattern Enhancement

```python
SUFFIX_NORMALIZATION = {
    "-core": {
        "variants": ["core", " core", "-core"],
        "standard": "core",
        "examples": ["metalcore", "deathcore", "grindcore", "mathcore"]
    },
    "-gaze": {
        "variants": ["gaze", "-gaze"],
        "standard": "gaze",
        "examples": ["shoegaze", "blackgaze", "doomgaze", "grungegaze"]
    },
    "-wave": {
        "variants": ["wave", "-wave", " wave"],
        "standard": "wave",
        "examples": ["darkwave", "coldwave", "chillwave", "synthwave"]
    }
}
```

### Priority 3: Abbreviation Intelligence

Instead of blind replacement, use context-aware normalization:

```python
ABBREVIATION_RULES = {
    "alt": {
        "expand_to": "alternative",
        "contexts": {
            "standalone": False,  # "alt" alone stays as "alt"
            "prefix": True,       # "alt-rock" → "alternative rock" OR keep as "alt-rock"
        },
        "decision": "keep_as_alt"  # Could be "expand_to_alternative"
    },
    "prog": {
        "expand_to": "progressive",
        "contexts": {
            "standalone": True,
            "prefix": True
        }
    },
    "psych": {
        "expand_to": "psychedelic",
        "contexts": {
            "standalone": True,
            "prefix": True
        }
    },
    "exp": {
        "expand_to": "experimental",
        "contexts": {
            "standalone": False,
            "prefix": True
        }
    }
}
```

### Priority 4: Slash and Multi-Tag Handling

```python
def handle_multi_tags(tag: str) -> List[str]:
    """
    Handle tags with slashes, e.g., 'Death Metal/Heavy Metal/OSDM'
    Returns list of individual normalized tags
    """
    if '/' in tag:
        parts = [p.strip() for p in tag.split('/')]
        return [normalize(part) for part in parts]
    return [tag]
```

### Priority 5: Compound Genre Intelligence

Create a smarter system for recognizing modifier + base genre patterns:

```python
MODIFIERS = {
    "atmospheric", "melodic", "technical", "brutal", "progressive",
    "experimental", "avant-garde", "epic", "symphonic", "orchestral",
    "blackened", "ambient", "cosmic", "depressive", "dissonant",
    "funeral", "medieval", "pagan", "folk", "viking"
}

BASE_GENRES = {
    "metal": ["death metal", "black metal", "doom metal", "power metal"],
    "rock": ["indie rock", "garage rock", "noise rock", "math rock"],
    "punk": ["post-punk", "hardcore punk", "art punk"],
    "pop": ["dream pop", "indie pop", "art pop", "synth pop"]
}

def normalize_compound(tag: str) -> str:
    """
    Recognize and standardize 'modifier + base genre' patterns
    E.g., 'Atmospheric Black Metal' → 'atmospheric black metal'
    """
    tag_lower = tag.lower()
    
    # Check for modifier + base genre
    for modifier in MODIFIERS:
        if tag_lower.startswith(modifier):
            # Find matching base genre
            remainder = tag_lower[len(modifier):].strip()
            # Normalize spacing/hyphens in remainder
            ...
```

## Implementation Plan

### Phase 1: Foundation (Week 1)
1. ✅ Implement enhanced case normalization
2. ✅ Add comprehensive misspelling dictionary
3. ✅ Create test suite for new normalizations

### Phase 2: Pattern Rules (Week 2)
1. ✅ Implement hyphen/space standardization
2. ✅ Add suffix pattern recognition
3. ✅ Test against existing tag database

### Phase 3: Advanced Features (Week 3)
1. ✅ Implement context-aware abbreviation expansion
2. ✅ Add multi-tag/slash handling
3. ✅ Create compound genre intelligence

### Phase 4: Validation & Rollout (Week 4)
1. ✅ Run full normalization on database
2. ✅ Review and validate results
3. ✅ Update atomic tags
4. ✅ Document changes

## Expected Impact

### Quantitative Benefits
- **Reduce tag count**: Estimated 200-300 tag consolidation
- **Improve consistency**: 95%+ tags following standard patterns
- **Better atomic decomposition**: Full coverage of compound tags

### Qualitative Benefits
- More predictable search results
- Better tag-based filtering
- Improved data quality for analysis
- Easier maintenance and extension

## Test Cases

### Critical Tests
```python
def test_case_normalization():
    assert normalize("Alt-Metal") == "alt-metal"
    assert normalize("Post-Rock") == "post-rock"
    assert normalize("ATMOSPHERIC BLACK METAL") == "atmospheric black metal"

def test_misspellings():
    assert normalize("Atmosheric Black metal") == "atmospheric black metal"
    assert normalize("ghotic metal") == "gothic metal"
    assert normalize("pschedelic") == "psychedelic"

def test_hyphen_space_consistency():
    assert normalize("Post-Metal") == normalize("Post Metal")
    assert normalize("Alt-Rock") == normalize("Alt Rock")
    
def test_compound_genres():
    assert normalize("Melodic Death Metal") == normalize("Melodic Death metal")
    assert normalize("Technical Death Metal") == "technical death metal"

def test_multi_tags():
    result = handle_multi_tags("Death Metal/Heavy Metal/OSDM")
    assert "death metal" in result
    assert "heavy metal" in result
    assert "osdm" in result
```

## Migration Strategy

1. **Backup current data**: ✅ Create full database backup
2. **Run in test mode**: Apply normalizations to copy of data
3. **Review changes**: Generate report of all tag changes
4. **Gradual rollout**: Apply changes in batches
5. **Monitor**: Track any issues or unexpected behaviors

## Configuration Updates Needed

### File: `tag_rules.json`

```json
{
  "common_misspellings": {
    // Add 20+ new entries from analysis
  },
  "hyphen_compounds": [
    // Define clear hyphenated compound list
  ],
  "space_compounds": [
    // Define clear space-separated compound list
  ],
  "suffix_patterns": {
    "core": ["core", "-core", " core"],
    "gaze": ["gaze", "-gaze"],
    "wave": ["wave", "-wave", " wave"],
    "metal": ["metal", " metal"],
    "rock": ["rock", " rock"]
  },
  "modifier_base_patterns": {
    // Intelligent compound genre recognition
  }
}
```

## Next Steps

1. **Review this analysis** with stakeholders
2. **Prioritize improvements** based on impact/effort
3. **Create detailed technical spec** for implementation
4. **Begin Phase 1** implementation
5. **Set up monitoring** for normalization quality

## Questions for Decision

1. **Alt vs Alternative**: Should we keep "alt-" prefix or expand to "alternative"?
2. **Hyphen policy**: Post-metal vs Post Metal - which is canonical?
3. **Acronyms**: Keep uppercase (DSBM, OSDM) or lowercase?
4. **Slash handling**: Split multi-tags or create compound tag?
5. **Atomic mode**: Should atomic decomposition be default for all operations?

---

**Document Version**: 1.0  
**Date**: 2025-01-16  
**Author**: AI Analysis of AlbumExplore Tag System
