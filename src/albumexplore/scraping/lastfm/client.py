"""
Last.fm API Client with rate limiting and error handling.

Provides low-level API access with automatic retry and backoff.
"""
import os
import time
import hashlib
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

import requests
import backoff

logger = logging.getLogger(__name__)


class LastFmAPIError(Exception):
    """Base exception for Last.fm API errors."""
    def __init__(self, message: str, error_code: Optional[int] = None):
        super().__init__(message)
        self.error_code = error_code


class LastFmRateLimitError(LastFmAPIError):
    """Raised when rate limit is exceeded."""
    pass


class LastFmClient:
    """
    Low-level Last.fm API client.
    
    Features:
    - Automatic rate limiting (default: 5 req/sec)
    - Exponential backoff on errors
    - Request signing for authenticated methods
    
    Usage:
        client = LastFmClient(api_key="your_key")
        album_info = client.get_album_info("Pink Floyd", "The Wall")
    """
    
    BASE_URL = "https://ws.audioscrobbler.com/2.0/"
    
    # Last.fm error codes
    ERROR_INVALID_SERVICE = 2
    ERROR_INVALID_METHOD = 3
    ERROR_AUTH_FAILED = 4
    ERROR_INVALID_FORMAT = 5
    ERROR_INVALID_PARAMS = 6
    ERROR_INVALID_RESOURCE = 7
    ERROR_OPERATION_FAILED = 8
    ERROR_INVALID_SESSION = 9
    ERROR_INVALID_API_KEY = 10
    ERROR_SERVICE_OFFLINE = 11
    ERROR_RATE_LIMIT = 29
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        shared_secret: Optional[str] = None,
        requests_per_second: float = 5.0,
    ):
        """
        Initialize the Last.fm client.
        
        Args:
            api_key: Last.fm API key. Falls back to LASTFM_API_KEY env var.
            shared_secret: Last.fm shared secret. Falls back to LASTFM_SHARED_SECRET env var.
            requests_per_second: Maximum requests per second (default 5).
        """
        self.api_key = api_key or os.environ.get("LASTFM_API_KEY")
        self.shared_secret = shared_secret or os.environ.get("LASTFM_SHARED_SECRET")
        
        if not self.api_key:
            raise ValueError(
                "Last.fm API key required. Pass api_key or set LASTFM_API_KEY env var."
            )
        
        self._min_request_interval = 1.0 / requests_per_second
        self._last_request_time = 0.0
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'AlbumExplore/1.0 (https://github.com/albumexplore)'
        })
    
    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            sleep_time = self._min_request_interval - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.time()
    
    def _sign_request(self, params: Dict[str, str]) -> str:
        """
        Generate API signature for authenticated requests.
        
        Args:
            params: Request parameters (excluding format and callback)
            
        Returns:
            MD5 signature string
        """
        if not self.shared_secret:
            raise ValueError("Shared secret required for authenticated requests")
        
        # Sort parameters alphabetically and concatenate
        sorted_params = sorted(params.items())
        sig_string = "".join(f"{k}{v}" for k, v in sorted_params)
        sig_string += self.shared_secret
        
        return hashlib.md5(sig_string.encode('utf-8')).hexdigest()
    
    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, LastFmRateLimitError),
        max_tries=5,
        max_time=60,
    )
    def _make_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False
    ) -> Dict[str, Any]:
        """
        Make an API request with retry logic.
        
        Args:
            method: Last.fm API method name (e.g., 'album.getInfo')
            params: Additional parameters
            signed: Whether to sign the request
            
        Returns:
            Parsed JSON response
            
        Raises:
            LastFmAPIError: On API errors
            LastFmRateLimitError: On rate limit (will trigger backoff)
        """
        self._rate_limit()
        
        request_params = {
            'method': method,
            'api_key': self.api_key,
            'format': 'json',
        }
        
        if params:
            request_params.update(params)
        
        if signed:
            # Remove format before signing
            sign_params = {k: v for k, v in request_params.items() if k != 'format'}
            request_params['api_sig'] = self._sign_request(sign_params)
        
        try:
            response = self._session.get(self.BASE_URL, params=request_params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Check for API-level errors
            if 'error' in data:
                error_code = data.get('error')
                error_msg = data.get('message', 'Unknown error')
                
                if error_code == self.ERROR_RATE_LIMIT:
                    raise LastFmRateLimitError(error_msg, error_code)
                
                raise LastFmAPIError(f"Last.fm API error {error_code}: {error_msg}", error_code)
            
            return data
            
        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout for method {method}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for method {method}: {e}")
            raise
    
    # =========================================================================
    # Album Methods
    # =========================================================================
    
    def get_album_info(
        self,
        artist: str,
        album: str,
        mbid: Optional[str] = None,
        autocorrect: bool = True,
        username: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get album metadata from Last.fm.
        
        Args:
            artist: Artist name
            album: Album title
            mbid: MusicBrainz album ID (optional, used instead of artist+album)
            autocorrect: Transform misspelled names to correct artist/album
            username: Username for user-specific playcount
            
        Returns:
            Album info dict with keys: name, artist, mbid, url, image,
            listeners, playcount, tracks, tags, wiki
        """
        params = {
            'autocorrect': '1' if autocorrect else '0',
        }
        
        if mbid:
            params['mbid'] = mbid
        else:
            params['artist'] = artist
            params['album'] = album
        
        if username:
            params['username'] = username
        
        response = self._make_request('album.getInfo', params)
        return response.get('album', {})
    
    def get_album_tags(
        self,
        artist: str,
        album: str,
        mbid: Optional[str] = None,
        autocorrect: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get top tags for an album.
        
        Returns:
            List of tag dicts with keys: name, url, count
        """
        params = {
            'autocorrect': '1' if autocorrect else '0',
        }
        
        if mbid:
            params['mbid'] = mbid
        else:
            params['artist'] = artist
            params['album'] = album
        
        response = self._make_request('album.getTopTags', params)
        tags = response.get('toptags', {}).get('tag', [])
        
        # Ensure it's always a list (single tag returns dict)
        if isinstance(tags, dict):
            tags = [tags]
        
        return tags
    
    def search_album(
        self,
        album: str,
        limit: int = 30,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Search for albums by name.
        
        Returns:
            Search results with albummatches list
        """
        params = {
            'album': album,
            'limit': str(limit),
            'page': str(page),
        }
        
        response = self._make_request('album.search', params)
        return response.get('results', {})
    
    # =========================================================================
    # Artist Methods
    # =========================================================================
    
    def get_artist_info(
        self,
        artist: str,
        mbid: Optional[str] = None,
        autocorrect: bool = True,
        username: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get artist metadata from Last.fm.
        
        Returns:
            Artist info dict with keys: name, mbid, url, image,
            stats (listeners, playcount), similar, tags, bio
        """
        params = {
            'autocorrect': '1' if autocorrect else '0',
        }
        
        if mbid:
            params['mbid'] = mbid
        else:
            params['artist'] = artist
        
        if username:
            params['username'] = username
        
        response = self._make_request('artist.getInfo', params)
        return response.get('artist', {})
    
    def get_artist_top_albums(
        self,
        artist: str,
        mbid: Optional[str] = None,
        autocorrect: bool = True,
        limit: int = 50,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Get an artist's top albums by playcount.
        
        Returns:
            List of album dicts sorted by playcount
        """
        params = {
            'autocorrect': '1' if autocorrect else '0',
            'limit': str(limit),
            'page': str(page),
        }
        
        if mbid:
            params['mbid'] = mbid
        else:
            params['artist'] = artist
        
        response = self._make_request('artist.getTopAlbums', params)
        albums = response.get('topalbums', {}).get('album', [])
        
        if isinstance(albums, dict):
            albums = [albums]
        
        return albums
    
    def get_artist_tags(
        self,
        artist: str,
        mbid: Optional[str] = None,
        autocorrect: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get top tags for an artist.
        
        Returns:
            List of tag dicts with keys: name, url, count
        """
        params = {
            'autocorrect': '1' if autocorrect else '0',
        }
        
        if mbid:
            params['mbid'] = mbid
        else:
            params['artist'] = artist
        
        response = self._make_request('artist.getTopTags', params)
        tags = response.get('toptags', {}).get('tag', [])
        
        if isinstance(tags, dict):
            tags = [tags]
        
        return tags
    
    def get_similar_artists(
        self,
        artist: str,
        mbid: Optional[str] = None,
        autocorrect: bool = True,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get similar artists.
        
        Returns:
            List of similar artist dicts with match score
        """
        params = {
            'autocorrect': '1' if autocorrect else '0',
            'limit': str(limit),
        }
        
        if mbid:
            params['mbid'] = mbid
        else:
            params['artist'] = artist
        
        response = self._make_request('artist.getSimilar', params)
        artists = response.get('similarartists', {}).get('artist', [])
        
        if isinstance(artists, dict):
            artists = [artists]
        
        return artists
    
    def search_artist(
        self,
        artist: str,
        limit: int = 30,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Search for artists by name.
        
        Returns:
            Search results with artistmatches list
        """
        params = {
            'artist': artist,
            'limit': str(limit),
            'page': str(page),
        }
        
        response = self._make_request('artist.search', params)
        return response.get('results', {})
    
    # =========================================================================
    # Tag Methods
    # =========================================================================
    
    def get_tag_info(self, tag: str) -> Dict[str, Any]:
        """
        Get metadata for a tag.
        
        Returns:
            Tag info with reach and wiki
        """
        params = {'tag': tag}
        response = self._make_request('tag.getInfo', params)
        return response.get('tag', {})
    
    def get_tag_top_albums(
        self,
        tag: str,
        limit: int = 50,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Get top albums for a tag.
        
        Returns:
            List of album dicts
        """
        params = {
            'tag': tag,
            'limit': str(limit),
            'page': str(page),
        }
        
        response = self._make_request('tag.getTopAlbums', params)
        albums = response.get('albums', {}).get('album', [])
        
        if isinstance(albums, dict):
            albums = [albums]
        
        return albums
    
    def get_tag_top_artists(
        self,
        tag: str,
        limit: int = 50,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Get top artists for a tag.
        
        Returns:
            List of artist dicts
        """
        params = {
            'tag': tag,
            'limit': str(limit),
            'page': str(page),
        }
        
        response = self._make_request('tag.getTopArtists', params)
        artists = response.get('topartists', {}).get('artist', [])
        
        if isinstance(artists, dict):
            artists = [artists]
        
        return artists
