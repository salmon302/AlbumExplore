import re
import hashlib
import uuid
from pathlib import Path
from typing import Optional, Dict
import pandas as pd
import json

def clean_text(text: str) -> Optional[str]:
    """
    Clean text from HTML tags and normalize whitespace.
    
    Args:
        text: Raw text string that might contain HTML or extra whitespace
        
    Returns:
        Cleaned text or None if empty/NaN
    """
    if pd.isna(text) or text is None:
        return None
    
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', str(text))
    
    # Normalize whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    # Convert special HTML entities
    clean = clean.replace('&amp;', '&')
    clean = clean.replace('&lt;', '<')
    clean = clean.replace('&gt;', '>')
    clean = clean.replace('&quot;', '"')
    clean = clean.replace('&apos;', "'")
    
    return clean if clean else None

def generate_id(prefix: str = "") -> str:
    """
    Generate a unique ID for database entities.
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        Unique string ID
    """
    return f"{prefix}{str(uuid.uuid4())}"

def calculate_file_hash(file_path: Path) -> str:
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except FileNotFoundError:
        return ""

def load_state(state_file: Path) -> Dict[str, str]:
    """Load processing state from JSON file."""
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_state(state_file: Path, state: Dict[str, str]):
    """Save processing state to JSON file."""
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=4)
