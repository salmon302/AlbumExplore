"""
Last.fm batch fetcher for enriching album data.

Fetches album/artist data from Last.fm and stores raw JSON responses.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Iterator, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from .client import LastFmClient, LastFmAPIError
from .media_manager import MediaManager

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Result of a fetch operation."""
    artist: str
    album: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    mbid: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LastFmFetcher:
    """
    High-level fetcher for batch Last.fm data retrieval.
    
    Features:
    - Batch processing with progress tracking
    - Raw JSON storage in raw_data/lastfm/
    - Resume capability via manifest tracking
    - Error aggregation and reporting
    
    Usage:
        fetcher = LastFmFetcher(api_key="...")
        
        # Fetch for a list of albums
        albums = [("Pink Floyd", "The Wall"), ("Tool", "Lateralus")]
        results = fetcher.fetch_albums(albums)
        
        # Check results
        for result in results:
            if result.success:
                print(f"Got {result.data['playcount']} plays")
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        shared_secret: Optional[str] = None,
        raw_data_dir: str = "./raw_data/lastfm",
        requests_per_second: float = 5.0,
        download_images: bool = True,
    ):
        """
        Initialize the fetcher.
        
        Args:
            api_key: Last.fm API key
            shared_secret: Last.fm shared secret
            raw_data_dir: Directory for raw JSON storage
            requests_per_second: Rate limit
            download_images: Whether to download and cache album art
        """
        self.client = LastFmClient(
            api_key=api_key,
            shared_secret=shared_secret,
            requests_per_second=requests_per_second,
        )
        self.media_manager = MediaManager() if download_images else None
        self.raw_data_dir = Path(raw_data_dir)
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create dated subdirectory for this fetch session
        self.session_date = datetime.now().strftime("%Y%m%d")
        self.session_dir = self.raw_data_dir / self.session_date
        self.session_dir.mkdir(exist_ok=True)
        
        # Manifest for tracking fetched items
        self.manifest_path = self.raw_data_dir / "MANIFEST.json"
        self.manifest = self._load_manifest()
    
    def _load_manifest(self) -> Dict[str, Any]:
        """Load or create the manifest file."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Could not decode manifest, starting fresh")
        
        return {
            "created": datetime.now().isoformat(),
            "last_updated": None,
            "albums_fetched": {},
            "artists_fetched": {},
            "fetch_sessions": [],
        }
    
    def _save_manifest(self):
        """Save the manifest file."""
        self.manifest["last_updated"] = datetime.now().isoformat()
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2)
    
    def _get_album_key(self, artist: str, album: str) -> str:
        """Generate a unique key for an album."""
        return f"{artist.lower().strip()}|||{album.lower().strip()}"
    
    def _get_artist_key(self, artist: str) -> str:
        """Generate a unique key for an artist."""
        return artist.lower().strip()

    def _get_best_image_url(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract best quality image URL from response data."""
        images = data.get('image', [])
        if not images:
            return None
        
        # Prefer largest size
        for size in ['mega', 'extralarge', 'large', 'medium', 'small']:
            for img in images:
                if img.get('size') == size and img.get('#text'):
                    return img['#text']
        return None
    
    def _prune_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prune unnecessary data from the API response to save space.
        """
        # Remove redundant images if we have a local copy
        if '_local_image_path' in data and 'image' in data:
            # Keep only the largest image URL as backup (usually the last one)
            images = data['image']
            if isinstance(images, list) and images:
                 # Filter to keep just the last one (usually 'mega' or 'extralarge')
                data['image'] = [images[-1]]
        
        # Prune wiki content if it's too long? (Optional)
        # For now we keep it as it's useful context.
        
        return data

    def _save_raw_json(self, data: Dict[str, Any], filename: str) -> Path:
        """Save raw JSON response to session directory."""
        data = self._prune_data(data)
        filepath = self.session_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath
    
    def is_album_fetched(self, artist: str, album: str) -> bool:
        """Check if an album has already been fetched."""
        key = self._get_album_key(artist, album)
        return key in self.manifest.get("albums_fetched", {})
    
    def is_artist_fetched(self, artist: str) -> bool:
        """Check if an artist has already been fetched."""
        key = self._get_artist_key(artist)
        return key in self.manifest.get("artists_fetched", {})
    
    def fetch_album(
        self,
        artist: str,
        album: str,
        skip_if_exists: bool = True,
        include_tags: bool = True,
    ) -> FetchResult:
        """
        Fetch data for a single album.
        
        Args:
            artist: Artist name
            album: Album title
            skip_if_exists: Skip if already in manifest
            include_tags: Also fetch top tags
            
        Returns:
            FetchResult with album data
        """
        key = self._get_album_key(artist, album)
        
        if skip_if_exists and key in self.manifest.get("albums_fetched", {}):
            logger.debug(f"Skipping already fetched: {artist} - {album}")
            cached = self.manifest["albums_fetched"][key]
            return FetchResult(
                artist=artist,
                album=album,
                success=True,
                data={"cached": True, "raw_file": cached.get("raw_file")},
                mbid=cached.get("mbid"),
            )
        
        try:
            # Fetch album info
            album_info = self.client.get_album_info(artist, album)
            
            # Optionally fetch tags separately (more detailed)
            if include_tags:
                try:
                    tags = self.client.get_album_tags(artist, album)
                    album_info['_fetched_tags'] = tags
                except LastFmAPIError as e:
                    logger.debug(f"Could not fetch tags for {artist} - {album}: {e}")
            
            # Extract MBID if present
            mbid = album_info.get('mbid') or None

            # Download and cache album art
            if self.media_manager:
                image_url = self._get_best_image_url(album_info)
                if image_url:
                    local_path = self.media_manager.download_and_process_image(image_url)
                    if local_path:
                        album_info['_local_image_path'] = local_path
                        logger.debug(f"Cached album art to {local_path}")
            
            # Save raw JSON
            safe_artist = "".join(c if c.isalnum() else "_" for c in artist)[:50]
            safe_album = "".join(c if c.isalnum() else "_" for c in album)[:50]
            filename = f"album_{safe_artist}_{safe_album}.json"
            raw_file = self._save_raw_json(album_info, filename)
            
            # Update manifest
            if "albums_fetched" not in self.manifest:
                self.manifest["albums_fetched"] = {}
            
            self.manifest["albums_fetched"][key] = {
                "artist": artist,
                "album": album,
                "mbid": mbid,
                "raw_file": str(raw_file),
                "fetched_at": datetime.now().isoformat(),
            }
            self._save_manifest()
            
            return FetchResult(
                artist=artist,
                album=album,
                success=True,
                data=album_info,
                mbid=mbid,
            )
            
        except LastFmAPIError as e:
            logger.warning(f"API error fetching {artist} - {album}: {e}")
            return FetchResult(
                artist=artist,
                album=album,
                success=False,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching {artist} - {album}: {e}")
            return FetchResult(
                artist=artist,
                album=album,
                success=False,
                error=str(e),
            )
    
    def fetch_artist(
        self,
        artist: str,
        skip_if_exists: bool = True,
        include_top_albums: bool = True,
        include_similar: bool = True,
        top_albums_limit: int = 50,
    ) -> FetchResult:
        """
        Fetch data for an artist.
        
        Args:
            artist: Artist name
            skip_if_exists: Skip if already in manifest
            include_top_albums: Also fetch top albums
            include_similar: Also fetch similar artists
            top_albums_limit: Max albums to fetch
            
        Returns:
            FetchResult with artist data
        """
        key = self._get_artist_key(artist)
        
        if skip_if_exists and key in self.manifest.get("artists_fetched", {}):
            logger.debug(f"Skipping already fetched artist: {artist}")
            cached = self.manifest["artists_fetched"][key]
            return FetchResult(
                artist=artist,
                album="",
                success=True,
                data={"cached": True, "raw_file": cached.get("raw_file")},
                mbid=cached.get("mbid"),
            )
        
        try:
            # Fetch artist info
            artist_info = self.client.get_artist_info(artist)
            
            # Optionally fetch top albums
            if include_top_albums:
                try:
                    top_albums = self.client.get_artist_top_albums(
                        artist, limit=top_albums_limit
                    )
                    artist_info['_top_albums'] = top_albums
                except LastFmAPIError as e:
                    logger.debug(f"Could not fetch top albums for {artist}: {e}")
            
            # Optionally fetch similar artists
            if include_similar:
                try:
                    similar = self.client.get_similar_artists(artist)
                    artist_info['_similar_artists'] = similar
                    logger.debug(f"Fetched {len(similar)} similar artists for {artist}")
                except LastFmAPIError as e:
                    logger.debug(f"Could not fetch similar artists for {artist}: {e}")
            
            # Extract MBID
            mbid = artist_info.get('mbid') or None
            
            # Download and cache artist image
            if self.media_manager:
                image_url = self._get_best_image_url(artist_info)
                if image_url:
                    local_path = self.media_manager.download_and_process_image(image_url)
                    if local_path:
                        artist_info['_local_image_path'] = local_path
                        logger.debug(f"Cached artist image to {local_path}")

            # Save raw JSON
            safe_artist = "".join(c if c.isalnum() else "_" for c in artist)[:50]
            filename = f"artist_{safe_artist}.json"
            raw_file = self._save_raw_json(artist_info, filename)
            
            # Update manifest
            if "artists_fetched" not in self.manifest:
                self.manifest["artists_fetched"] = {}
            
            self.manifest["artists_fetched"][key] = {
                "artist": artist,
                "mbid": mbid,
                "raw_file": str(raw_file),
                "fetched_at": datetime.now().isoformat(),
            }
            self._save_manifest()
            
            return FetchResult(
                artist=artist,
                album="",
                success=True,
                data=artist_info,
                mbid=mbid,
            )
            
        except LastFmAPIError as e:
            logger.warning(f"API error fetching artist {artist}: {e}")
            return FetchResult(
                artist=artist,
                album="",
                success=False,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching artist {artist}: {e}")
            return FetchResult(
                artist=artist,
                album="",
                success=False,
                error=str(e),
            )
    
    def fetch_albums_batch(
        self,
        albums: List[Tuple[str, str]],
        skip_if_exists: bool = True,
        include_tags: bool = True,
        progress_callback: Optional[callable] = None,
        max_workers: int = 5,
    ) -> Iterator[FetchResult]:
        """
        Fetch data for multiple albums.
        
        Args:
            albums: List of (artist, album) tuples
            skip_if_exists: Skip already fetched albums
            include_tags: Fetch tags for each album
            progress_callback: Called with (current, total, result) after each fetch
            max_workers: Number of concurrent fetch threads
            
        Yields:
            FetchResult for each album
        """
        total = len(albums)
        logger.info(f"Starting batch fetch of {total} albums with {max_workers} workers")
        
        # Track session
        session_info = {
            "started": datetime.now().isoformat(),
            "total_requested": total,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
        }
        
        # Prepare work items
        work_items = []
        for i, (artist, album) in enumerate(albums):
            work_items.append((i, artist, album))
            
        # Use ThreadPoolExecutor for concurrent fetching
        completed_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a future for each album
            future_to_index = {
                executor.submit(
                    self.fetch_album, 
                    artist, 
                    album, 
                    skip_if_exists=skip_if_exists, 
                    include_tags=include_tags
                ): i 
                for i, artist, album in work_items
            }
            
            # Process results as they complete
            # Note: We yield results out of order as they complete, but we
            # can use the index to report progress or re-order if strictly needed.
            # Usually strict order doesn't matter for batch processing.
            for future in as_completed(future_to_index):
                completed_count += 1
                result = future.result()
                
                if result.success:
                    if result.data and result.data.get("cached"):
                        session_info["skipped"] += 1
                    else:
                        session_info["successful"] += 1
                else:
                    session_info["failed"] += 1
                
                if progress_callback:
                    progress_callback(completed_count, total, result)
                
                yield result
        
        # Record session
        session_info["completed"] = datetime.now().isoformat()
        if "fetch_sessions" not in self.manifest:
            self.manifest["fetch_sessions"] = []
        self.manifest["fetch_sessions"].append(session_info)
        self._save_manifest()
        
        logger.info(
            f"Batch complete: {session_info['successful']} success, "
            f"{session_info['failed']} failed, {session_info['skipped']} skipped"
        )
    
    def fetch_albums_for_artists(
        self,
        artists: List[str],
        albums_per_artist: int = 20,
        skip_if_exists: bool = True,
    ) -> Iterator[FetchResult]:
        """
        Fetch top albums for a list of artists.
        
        This is useful for discovering new albums from known artists.
        
        Args:
            artists: List of artist names
            albums_per_artist: How many top albums to fetch per artist
            skip_if_exists: Skip already fetched
            
        Yields:
            FetchResult for each album found
        """
        for artist in artists:
            try:
                top_albums = self.client.get_artist_top_albums(
                    artist, limit=albums_per_artist
                )
                
                for album_data in top_albums:
                    album_name = album_data.get('name', '')
                    if not album_name:
                        continue
                    
                    result = self.fetch_album(
                        artist, album_name,
                        skip_if_exists=skip_if_exists,
                    )
                    yield result
                    
            except LastFmAPIError as e:
                logger.warning(f"Could not get top albums for {artist}: {e}")
                yield FetchResult(
                    artist=artist,
                    album="",
                    success=False,
                    error=f"Could not fetch top albums: {e}",
                )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about fetched data."""
        return {
            "total_albums": len(self.manifest.get("albums_fetched", {})),
            "total_artists": len(self.manifest.get("artists_fetched", {})),
            "sessions": len(self.manifest.get("fetch_sessions", [])),
            "last_updated": self.manifest.get("last_updated"),
        }
