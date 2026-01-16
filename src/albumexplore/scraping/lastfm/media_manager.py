"""
Media Manager for handling album art and other media assets.

Handles downloading, optimizing (WebP), and storing images efficiently.
"""
import hashlib
import logging
import shutil
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)


class MediaManager:
    """
    Manages media assets with efficient storage and optimization.
    
    Features:
    - Downloads images from URLs
    - Converts to efficient WebP format
    - Deduplicates using content hashing
    - Organizes storage with sharding
    """
    
    def __init__(self, base_dir: str = "./data/media"):
        self.base_dir = Path(base_dir)
        self.covers_dir = self.base_dir / "covers"
        self.covers_dir.mkdir(parents=True, exist_ok=True)
        
        # User-Agent for downloads
        self.headers = {
            'User-Agent': 'AlbumExplore/1.0 (MediaManager)'
        }
    
    def _get_start_sharding(self, hash_str: str) -> Path:
        """Get the shard directory (first 2 chars of hash) to avoid thousands of files in one dir."""
        shard = hash_str[:2]
        return self.covers_dir / shard

    def _calculate_content_hash(self, data: bytes) -> str:
        """Calculate MD5 hash of binary data."""
        return hashlib.md5(data).hexdigest()

    def download_and_process_image(
        self,
        url: str,
        max_size: Tuple[int, int] = (500, 500),
        quality: int = 80
    ) -> Optional[str]:
        """
        Download an image, convert to WebP, and store it.
        
        Args:
            url: Image URL
            max_size: Max dimensions (width, height) to resize to
            quality: WebP quality (0-100)
            
        Returns:
            Relative path to the stored image (as string), or None if failed.
        """
        if not url:
            return None
            
        try:
            # Check if it's already a local path
            if url.startswith("file://") or Path(url).exists():
                logger.debug(f"URL appears to be local: {url}")
                return str(url)

            # Download
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            content = response.content
            
            # Identify content hash for deduplication
            content_hash = self._calculate_content_hash(content)
            
            # Check if we already have this exact image processed
            shard_dir = self._get_start_sharding(content_hash)
            shard_dir.mkdir(exist_ok=True)
            
            filename = f"{content_hash}.webp"
            file_path = shard_dir / filename
            
            # Return path relative to project root (or base_dir) if it exists
            # We return relative to base_dir parents to make it portable? 
            # Actually, standardizing on relative path to project root is safest if running from root.
            # But let's return path relative to the media base dir for database cleanliness?
            # No, full relative path from execution context (project root) is best for specific usage.
            relative_path = Path("data/media/covers") / content_hash[:2] / filename
            
            if file_path.exists():
                logger.debug(f"Image already exists: {relative_path}")
                return str(relative_path).replace("\\", "/") # Normalize separators

            # Process image
            with Image.open(BytesIO(content)) as img:
                # Convert to RGB (in case of RGBA/P)
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Resize if needed (maintain aspect ratio)
                if img.width > max_size[0] or img.height > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save as WebP
                img.save(file_path, 'WEBP', quality=quality)
                logger.debug(f"Saved optimized image to {file_path}")
                
            return str(relative_path).replace("\\", "/")
            
        except Exception as e:
            logger.warning(f"Failed to process image from {url}: {e}")
            return None

    def get_local_path(self, relative_path: str) -> Optional[Path]:
        """Convert stored relative path to absolute Path object."""
        if not relative_path:
            return None
        return Path(relative_path).resolve()
