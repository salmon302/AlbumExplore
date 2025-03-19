# Tag System Technical Specification

## 1. Tag Analysis

The tag analysis is performed by the `TagAnalyzer` class located in `src/tags/analysis/tag_analyzer.py`.

**Key Functionalities:**

*   **Initialization:**
    *   Takes a Pandas DataFrame containing album data (with a 'tags' column) as input.
    *   Initializes data structures for tag frequencies, relationships, clusters, and a graph representation.
    *   Uses a `TagNormalizer` instance (likely from `src/tags/normalizer.py`) to normalize tags.
    *   Calculates initial tag frequencies and builds a graph with frequency-weighted nodes.

*   **`analyze_tags()`:**
    *   Calculates overall tag statistics: total tags, unique tags, most common tags, average tags per album.
    *   Calculates centrality metrics (degree centrality and betweenness centrality) using the `networkx` library.
    *   Detects hierarchical relationships between tags using the `_detect_hierarchies()` method.
    *   Returns a dictionary containing these statistics.

*   **`calculate_relationships()`:**
    *   Calculates weighted relationships between tags based on co-occurrence in the input DataFrame.
    *   Updates the graph with weighted edges representing these relationships.

*   **`_detect_hierarchies()`:**
    *   Identifies hierarchical relationships between tags by analyzing tag tokens (e.g., "melodic death metal" is a child of "death metal").

*   **`get_tag_clusters()`:**
    *   Performs community detection using the Louvain algorithm (from the `networkx` library) to find clusters of related tags.
    *   Allows specifying a minimum cluster size and a resolution parameter for the algorithm.

*   **`find_similar_tags()`:**
    *   Finds tags similar to a given tag based on shared connections in the graph.
    *   Uses a similarity threshold to filter results.

**Data Structures:**

*   **`tag_frequencies`:** (Dict[str, int]) Stores the frequency of each normalized tag.
*   **`tag_relationships`:** (Dict[Tuple[str, str], float]) Stores the weighted relationship strength between tag pairs.
*   **`tag_clusters`:** (Dict[str, List[str]]) Stores clusters of related tags.
*   **`graph`:** (nx.Graph) A NetworkX graph representing tags as nodes and relationships as edges.

**Dependencies:**

*   `pandas`: For DataFrame manipulation.
*   `collections.Counter`: For counting tag frequencies.
*   `networkx`: For graph representation and analysis (centrality, community detection).
*   `TagNormalizer`: For tag normalization.

### 1.1 Primary Tag Categories (Conceptual)
Based on data analysis:
- Genre Tags (e.g., "Black metal", "Death metal", "Prog-metal")
- Style Modifiers (e.g., "Atmospheric", "Technical", "Melodic")
- Fusion Indicators (e.g., "Post-", "Progressive", "Avant-Garde")
- Regional/Cultural Tags (e.g., "Celtic", "Viking", "Medieval")

### 1.2 Tag Relationships (Conceptual and Implemented)
- Hierarchical (e.g., "Death metal" -> "Melodic Death metal") - Detected by `_detect_hierarchies` and represented in the graph.
- Compositional (e.g., "Atmospheric" + "Black metal") - Implicitly captured through co-occurrence and graph relationships.
- Fusion (e.g., "Post-metal" + "Blackgaze") - Implicitly captured through co-occurrence and graph relationships.
- Exclusive (e.g., "Clean" vs "Harsh" vocals) -  Not explicitly handled in `TagAnalyzer`, but could be addressed through tag consolidation rules or future enhancements.

## 2. Normalization System

The tag normalization is handled by the `TagNormalizer` class located in `src/tags/normalizer/tag_normalizer.py`.

**Key Features and Functionalities:**

*   **`COMMON_MISSPELLINGS`:** A dictionary mapping common misspellings and variations of tags to their standardized forms (e.g., 'prog' to 'progressive', 'black-metal' to 'black metal').
*   **`known_tags`:** A set of known valid tags.
*   **`tag_aliases`:** A dictionary for storing tag aliases.
*    **`_initialize_known_tags`:**  Populates a set of known tags.
*   **`normalize(self, tag: str)`:** Normalizes a single tag:
    *   Converts to lowercase and removes leading/trailing whitespace.
    *   Handles compound terms (e.g., "post metal" becomes "post-metal").
    *   Handles regional spelling variations (e.g., "metal-core" becomes "metalcore").
    *   Standardizes spaces around hyphens.
    *   Removes special characters (except hyphens and apostrophes).
    *   Normalizes multiple spaces.
    *   Checks against `COMMON_MISSPELLINGS` and replaces if a match is found.
    *   Checks against `tag_aliases`.
    *   Checks if the tag is in `known_tags`.
    *   If no match is found, calls `_find_closest_match`.
*   **`_find_closest_match(self, tag: str, threshold: float = 0.85)`:** Finds the closest matching known tag using `SequenceMatcher` from the `difflib` library.
* **`add_alias(self, alias: str, primary: str)`:** Adds a new tag alias.
* **`normalize_list(self, tags: List[str])`:** Normalizes a list of tags.

### 2.1 Tag Standardization Rules (Implemented in `normalize` method)
- Case normalization (lowercase base terms)
- Hyphenation standards (e.g., "post-metal" vs "post metal")
- Compound term handling (e.g., "deathcore" vs "death-core")
- Regional spelling variations (e.g., "metal-core" vs "metalcore")
- Common misspelling handling
- Removal of special characters (except hyphens and apostrophes)

### 2.2 Tag Grouping
- Primary genres
- Subgenres
- Style modifiers
- Technical characteristics
- Vocal styles
- Instrumental indicators

### 2.3 Tag Similarity Detection
- Edit distance calculation (used in `_find_closest_match`)
- Common misspellings database (handled via `COMMON_MISSPELLINGS`)
- Phonetic similarity matching (Not directly implemented, but could be added as a custom rule or extension)
- Context-based grouping (Not explicitly implemented in `TagNormalizer`)

## 3. Search and Filter System

### 3.1 Search Features
- Fuzzy matching
- Partial term matching
- Synonym matching
- Auto-completion
- Suggestion system

### 3.2 Filter States
- Inclusive (must have tag)
	- Weight: 1.0
	- Behavior: Required match
- Exclusive (must not have tag)
	- Weight: -1.0
	- Behavior: Automatic exclusion
- Neutral (ignored)
	- Weight: 0.0
	- Behavior: No impact

### 3.3 Filter Combinations
- AND operations between inclusive tags
- OR operations within tag groups
- NOT operations for exclusive tags
- Weight-based relevance scoring

## 4. Implementation Considerations

### 4.1 Data Structures
- Tag Trie for fast prefix matching
- Similarity Matrix for related tags
- Weighted Graph for tag relationships
- Bloom filters for quick exclusion checks

### 4.2 Performance Optimization
- Cached similarity calculations
- Precomputed relationship weights
- Indexed tag lookups
- Batch update processing

### 4.3 Update Management
- Version control for tag definitions
- Change tracking system
- Conflict resolution rules
- Migration path for evolving tags

## 5. Tag Statistics

### 5.1 Usage Metrics
- Frequency tracking
- Co-occurrence patterns
- Temporal trends
- Regional variations

### 5.2 Quality Metrics
- Consistency score
- Ambiguity index
- Relationship strength
- User feedback integration

## 6. Problematic Tag Handling

### 6.1 Tag Consolidation

The `src/tags/analysis/tag_consolidator.py` file defines the `TagConsolidator` class, which is responsible for identifying and managing tag consolidation.

**Key Features and Functionalities:**

*   **Dependencies:** Depends on `TagAnalyzer` and `TagSimilarity` for tag analysis and similarity calculations.
*   **`ConsolidationRule`:** Represents a consolidation rule with a `pattern` (regular expression), `replacement` string, and `min_similarity` threshold.
*   **`MergeConflict`:** Represents a conflict during tag merging, including the `type` of conflict (frequency mismatch, relationship conflict, or existing merge), `primary_tag`, `conflicting_tags`, and a `description`.
*   **`MergePreview`:** Represents a preview of a merge operation, including the `primary_tag`, `tags_to_merge`, `affected_albums`, `frequency_change`, and a list of `conflicts`.
*   **`_initialize_default_rules`:** Initializes a set of default consolidation rules for common patterns (e.g., "prog metal" to "progressive metal", hyphenation, etc.).
*   **`add_consolidation_rule`:** Allows adding custom consolidation rules.
*   **`identify_merge_candidates`:** Identifies potential tag merges based on both consolidation rules and tag similarity. It first applies the rules and then uses similarity-based identification.
*   **`suggest_merges`:** Generates merge suggestions based on identified candidates and their frequencies.
*   **`detect_conflicts`:** Detects potential conflicts in a proposed merge, such as:
    *   **Frequency Mismatch:** When a tag to be merged has a significantly higher frequency than the primary tag.
    *   **Relationship Conflict:** When a tag to be merged has strong, unique relationships that the primary tag doesn't have.
    *   **Existing Merge:** When a tag is already part of another pending merge.
*   **`preview_merge`:** Provides a preview of the effects of a proposed merge, including the number of affected albums, the frequency change, and any detected conflicts.
*   **`queue_merge`:** Queues tags for merging, optionally forcing the merge despite conflicts (except for existing merge conflicts, which always block the merge).
*   **`apply_pending_merges`:** Applies all pending merges, updating the dataset and rebuilding tag frequencies and the graph (by calling `self.analyzer._initialize()`).
*   **`get_merge_history`:** Returns the history of applied merges.

### 6.2 Outlier Detection

The `TagAnalyzer` class provides some functionalities that can be used for outlier detection, although it doesn't have dedicated methods explicitly labeled as such.

**Potential Approaches using `TagAnalyzer`:**

*   **Centrality and Betweenness:** The `analyze_tags` method calculates centrality and betweenness metrics for tags in the tag graph. Tags with low centrality and betweenness could be considered outliers.
*   **Hierarchical Relationships:** The `_detect_hierarchies` method identifies hierarchical relationships. Tags that don't fit well within the hierarchy might be outliers.
*   **Tag Clustering:** The `get_tag_clusters` method groups related tags. Outliers might be tags that don't belong to any large cluster.
*   **Tag Similarity:** The `find_similar_tags` method could be used to identify tags with no similar tags above a certain threshold, potentially indicating outliers.
* **Frequency Analysis:** The `tag_frequencies` attribute, populated during initialization, can be used to identify low-frequency tags.

### 6.3 Misspelling Management

The `TagAnalyzer` class relies on the `TagNormalizer` class (presumably defined in `src/tags/normalizer.py`) for tag normalization, which likely handles some aspects of misspelling correction. However, `TagAnalyzer` itself doesn't have dedicated methods for misspelling detection or correction beyond the normalization provided by `TagNormalizer`.

### 6.4 Alternate Naming

The `TagAnalyzer` class does not directly handle alternate naming or synonyms.

### 6.5 Quality Assurance
- Validation Rules:
	- Format checking
	- Consistency validation
	- Relationship verification
	- Usage monitoring
- Review System:
	- Manual review queue
	- Automated flags
	- Change approval
	- Rollback capability