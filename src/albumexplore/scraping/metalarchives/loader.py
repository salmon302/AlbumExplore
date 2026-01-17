import pandas as pd
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
import re

logger = logging.getLogger(__name__)

class MetalArchivesLoader:
    """
    Loader for MetalArchives database dump (Nov 2024).
    Expects CSVs:
    - all_bands_discography.csv: Album Name,Type,Year,Reviews,Band ID
    """
    
    def __init__(self, data_dir: str = "data/MetalArchives"):
        self.data_dir = Path(data_dir)
        self.discography_path = self.data_dir / "all_bands_discography.csv"
        self.bands_path = self.data_dir / "metal_bands.csv"
        
    def parse_reviews(self, review_str: str) -> Dict[str, Optional[float]]:
        """
        Parses review string like "1 (77%)" or "No Reviews".
        Returns: {'count': int, 'rating': float (0-100)}
        """
        if pd.isna(review_str) or review_str == "No Reviews":
            return {'count': 0, 'rating': None}
        
        # Regex for "5 (85%)"
        match = re.search(r"(\d+)\s*\((\d+)%\)", str(review_str))
        if match:
            return {
                'count': int(match.group(1)),
                'rating': float(match.group(2))
            }
        
        return {'count': 0, 'rating': None}

    def load_bands(self) -> Dict[str, Dict[str, Any]]:
        """
        Loads bands into a dictionary keyed by Band ID.
        """
        if not self.bands_path.exists():
            logger.error(f"Bands file not found at {self.bands_path}")
            return {}
            
        logger.info(f"Loading bands from {self.bands_path}")
        df = pd.read_csv(self.bands_path, dtype={'Band ID': str})
        
        bands = {}
        for _, row in df.iterrows():
            bands[row['Band ID']] = {
                'name': row['Name'],
                'country': row['Country'],
                'genre': row['Genre'],
                'status': row['Status'],
                'url': row['URL']
            }
        return bands

    def load_discography(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Loads and parses the discography CSV.
        
        Proposed Schema Mapping:
        ------------------------
        Source CSV          ->  Album Model
        'Album Name'        ->  title
        'Type'              ->  type
        'Year'              ->  release_year
        'Reviews' (parsed)  ->  ma_review_count (new), ma_rating_percent (new)
        'Band ID'           ->  Linked to Artist via mappings
        """
        if not self.discography_path.exists():
            logger.error(f"Discography file not found at {self.discography_path}")
            return []

        # Load bands first for resolution
        bands_map = self.load_bands()
        
        logger.info(f"Loading discography from {self.discography_path}")
        
        # Read CSV
        # Note: Band ID seem to be numeric but large, keep as strings to be safe
        df = pd.read_csv(self.discography_path, nrows=limit, dtype={'Band ID': str})
        
        results = []
        
        for _, row in df.iterrows():
            review_data = self.parse_reviews(row['Reviews'])
            band_id = row['Band ID']
            band_info = bands_map.get(band_id, {})
            
            entry = {
                'title': row['Album Name'],
                'type': row['Type'],
                'year': row['Year'],
                'band_id': band_id,
                'artist_name': band_info.get('name', 'Unknown Artist'),
                'artist_country': band_info.get('country'),
                'artist_genre': band_info.get('genre'),
                'review_count': review_data['count'],
                'rating_percent': review_data['rating'],
                'source': 'MetalArchives'
            }
            results.append(entry)
            
        logger.info(f"Parsed {len(results)} albums from MetalArchives export.")
        return results

    def analyze_data_quality(self):
        """
        Quick analysis of the dataset.
        """
        if not self.discography_path.exists():
            print(f"File not found: {self.discography_path}")
            return
            
        df_disco = pd.read_csv(self.discography_path, dtype={'Band ID': str})
        print(f"Total Albums: {len(df_disco)}")
        
        print("\nRelease Types Distribution:")
        print(df_disco['Type'].value_counts())
        
        if self.bands_path.exists():
            df_bands = pd.read_csv(self.bands_path, dtype={'Band ID': str})
            print(f"\nTotal Bands: {len(df_bands)}")
            
            # Coverage check
            disco_ids = set(df_disco['Band ID'])
            band_ids = set(df_bands['Band ID'])
            common = disco_ids.intersection(band_ids)
            missing = disco_ids - band_ids
            
            print(f"Bands in Discography: {len(disco_ids)}")
            print(f"Bands with Metadata: {len(common)}")
            print(f"Bands Missing Metadata: {len(missing)}")
            
            if len(missing) > 0:
                print(f"Sample missing IDs: {list(missing)[:5]}")
        else:
            print("\nBands file missing, cannot analyze coverage.")

if __name__ == "__main__":
    # Simple CLI test
    import sys
    logging.basicConfig(level=logging.INFO)
    
    loader = MetalArchivesLoader()
    if len(sys.argv) > 1 and sys.argv[1] == "analyze":
        loader.analyze_data_quality()
    else:
        # Load sample
        items = loader.load_discography(limit=5)
        for item in items:
            print(f"{item['artist_name']} - {item['title']} ({item['year']})")
