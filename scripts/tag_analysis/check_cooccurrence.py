import sqlite3
import json
import logging
from difflib import SequenceMatcher
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'albumexplore.db'
OUTPUT_FILE = 'data/exports/cooccurrence_suggestions.json'

def get_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def analyze_cooccurrence():
    if not Path(DB_PATH).exists():
        logger.error(f"Database not found at {DB_PATH}")
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    logger.info("Fetching singletons from DB...")
    # Find tags with frequency 1
    # NOTE: schema has 'frequency' column in tags table.
    
    # Try using the frequency column first
    use_frequency_column = True
    try:
        cursor.execute("SELECT id, name FROM tags WHERE frequency = 1")
        singletons = cursor.fetchall()
        if len(singletons) == 0:
            logger.info("No singletons found via frequency column. Trying aggregation...")
            use_frequency_column = False
    except sqlite3.OperationalError:
        use_frequency_column = False
        
    if not use_frequency_column:
        logger.info("Calculating singletons and their albums via aggregation...")
        # Modified to fetch album_id as well. Since it's a singleton, MIN/MAX works to get the single value.
        cursor.execute("""
            SELECT t.id, t.name, MAX(at.album_id) as album_id
            FROM tags t 
            JOIN album_tags at ON t.id = at.tag_id 
            GROUP BY t.id 
            HAVING COUNT(at.album_id) = 1
        """)
        singletons = cursor.fetchall()
    else:
        # If we used the frequency column, we still need the album_id
        # This path might be less efficient if we iterate, so let's just do the aggregation one.
        # It's safer and gives us everything we need.
        # Forcing the aggregation path for now as it solves the N+1 problem better
        logger.info("Switching to aggregation to ensure album IDs are fetched efficiently...")
        cursor.execute("""
            SELECT t.id, t.name, MAX(at.album_id) as album_id
            FROM tags t 
            JOIN album_tags at ON t.id = at.tag_id 
            GROUP BY t.id 
            HAVING COUNT(at.album_id) = 1
        """)
        singletons = cursor.fetchall()
        
    logger.info(f"Found {len(singletons)} singletons to analyze. Pre-fetching album contexts...")
    
    # 2. Batch fetch all siblings for these albums
    # Get unique album IDs
    relevant_album_ids = list(set([row['album_id'] for row in singletons if row['album_id'] is not None]))
    
    album_siblings_map = {}
    
    # Chunking to respect SQLite variable limits (usually 999 or 32766, but 900 is safe)
    CHUNK_SIZE = 900
    for i in range(0, len(relevant_album_ids), CHUNK_SIZE):
        chunk = relevant_album_ids[i:i+CHUNK_SIZE]
        if not chunk:
            continue
            
        placeholders = ','.join(['?'] * len(chunk))
        query = f"""
            SELECT at.album_id, t.name 
            FROM album_tags at 
            JOIN tags t ON at.tag_id = t.id 
            WHERE at.album_id IN ({placeholders})
        """
        cursor.execute(query, chunk)
        
        for row in cursor.fetchall():
            aid = row['album_id']
            tname = row['name']
            if aid not in album_siblings_map:
                album_siblings_map[aid] = []
            album_siblings_map[aid].append(tname)
            
    logger.info(f"Loaded context for {len(album_siblings_map)} albums.")
    
    suggestions = {}
    
    for row in singletons:
        tag_id = row['id']
        tag_name = row['name']
        normalized_name = tag_name.lower().strip()
        
        album_id = row['album_id']
        
        if not album_id or album_id not in album_siblings_map:
            continue
            
        # Get siblings from map
        all_tags_on_album = album_siblings_map[album_id]
        # Filter out self
        siblings = [s for s in all_tags_on_album if s != tag_name]
        
        # Compare with siblings
        best_match = None
        best_score = 0.0
        reason = ""
        
        for sibling in siblings:
            sib_norm = sibling.lower().strip()
            
            # 1. Fuzzy Match
            score = get_similarity(normalized_name, sib_norm)
            
            # 2. Substring / Containment (Superset)
            # If singleton is "Post-Rock Music" and sibling is "Post-Rock", 
            # and they are on the same album, "Post-Rock Music" is likely redundant.
            if sib_norm in normalized_name and len(sib_norm) > 3:
                # favor the shorter, simpler tag
                if score < 0.9: # Boost score if contained
                    score = 0.95
                reason = f"contains-sibling:{sib_norm}"
            
            # 3. Substring (Subset)
            # If singleton is "Metal" and sibling is "Heavy Metal", 
            # this is just hierarchy co-occurrence, not necessarily a mapping.
            # We usually DON'T want to map "Metal" -> "Heavy Metal" just because they co-occur.
            # BUT, if singleton is "Post" and sibling is "Post-Rock", maybe "Post" is a typo/fragment?
            # Let's be conservative and only map if it looks like a typo (high fuzzy score).
            
            if score > best_score:
                best_score = score
                best_match = sib_norm
                if not reason:
                    reason = f"fuzzy-cooccurrence:{best_score:.2f}"

        # If we found a very good match on the SAME album
        if best_score > 0.85:
            suggestions[tag_name] = {
                'suggestion': best_match,
                'reason': reason,
                'score': best_score,
                'type': 'cooccurrence'
            }
            
    conn.close()
    
    # Save output
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({'stats': {'suggested': len(suggestions)}, 'suggestions': suggestions}, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Generated {len(suggestions)} co-occurrence suggestions. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    analyze_cooccurrence()
