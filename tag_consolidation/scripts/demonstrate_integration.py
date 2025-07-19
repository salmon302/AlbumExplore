#!/usr/bin/env python3
"""
Example Integration: Using Atomic Tags in Real Workflow

This script demonstrates how to integrate the atomic tag system 
into existing AlbumExplore workflows.
"""

import sys
import os
import json
from pathlib import Path

# Add paths for imports
sys.path.append('c:/Users/salmo/Documents/GitHub/AlbumExplore/src')

def load_atomic_config():
    """Load the atomic tag configuration"""
    config_path = 'c:/Users/salmo/Documents/GitHub/AlbumExplore/src/albumexplore/config/tag_rules.json'
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

def atomic_normalize_tag(tag, config):
    """Normalize a single tag using atomic decomposition"""
    if not tag or not config:
        return [tag] if tag else []
    
    # Clean the tag
    cleaned_tag = tag.lower().strip()
    
    # Check for decomposition rules
    decomp_rules = config.get('atomic_decomposition', {})
    
    if cleaned_tag in decomp_rules:
        return decomp_rules[cleaned_tag]
    
    # Check for case variants
    for rule_tag, components in decomp_rules.items():
        if rule_tag.replace('-', ' ') == cleaned_tag.replace('-', ' '):
            return components
    
    # If no decomposition rule, return as single atomic tag
    return [cleaned_tag]

def process_album_tags(album_data, config):
    """Process album tags using atomic normalization"""
    
    if 'tags' not in album_data:
        return album_data
    
    original_tags = album_data['tags']
    atomic_tags = []
    
    for tag in original_tags:
        atomic_components = atomic_normalize_tag(tag, config)
        atomic_tags.extend(atomic_components)
    
    # Remove duplicates while preserving order
    unique_atomic_tags = []
    seen = set()
    for tag in atomic_tags:
        if tag not in seen:
            seen.add(tag)
            unique_atomic_tags.append(tag)
    
    # Update album data
    album_data_updated = album_data.copy()
    album_data_updated['original_tags'] = original_tags
    album_data_updated['atomic_tags'] = unique_atomic_tags
    album_data_updated['tag_reduction'] = len(original_tags) - len(unique_atomic_tags)
    
    return album_data_updated

def demonstrate_integration():
    """Demonstrate the atomic tag integration"""
    
    print("🎵 ATOMIC TAG INTEGRATION DEMONSTRATION")
    print("=" * 60)
    
    # Load configuration
    print("1️⃣  Loading atomic tag configuration...")
    config = load_atomic_config()
    
    if not config:
        print("❌ Failed to load configuration")
        return
    
    print(f"✅ Loaded {len(config.get('atomic_tags', {}).get('all_valid_tags', []))} atomic tags")
    print(f"✅ Loaded {len(config.get('atomic_decomposition', {}))} decomposition rules")
    
    # Example album data
    sample_albums = [
        {
            'title': 'Tool - Lateralus',
            'tags': ['Progressive Metal', 'Alternative Metal', 'art-rock']
        },
        {
            'title': 'Opeth - Blackwater Park', 
            'tags': ['death metal', 'progressive-metal', 'atmospheric']
        },
        {
            'title': 'Godspeed You! Black Emperor - Lift Your Skinny Fists',
            'tags': ['post-rock', 'experimental', 'ambient', 'cinematic']
        },
        {
            'title': 'Mastodon - Leviathan',
            'tags': ['sludge metal', 'progressive metal', 'heavy metal']
        },
        {
            'title': 'King Crimson - In the Court of the Crimson King',
            'tags': ['progressive rock', 'art-rock', 'experimental rock']
        }
    ]
    
    print("\n2️⃣  Processing sample albums...")
    
    for i, album in enumerate(sample_albums, 1):
        print(f"\n📀 Album {i}: {album['title']}")
        processed = process_album_tags(album, config)
        
        print(f"   Original tags ({len(processed['original_tags'])}): {processed['original_tags']}")
        print(f"   Atomic tags ({len(processed['atomic_tags'])}): {processed['atomic_tags']}")
        
        if processed['tag_reduction'] > 0:
            print(f"   ✅ Reduced by {processed['tag_reduction']} tags")
        elif processed['tag_reduction'] < 0:
            print(f"   📈 Expanded by {abs(processed['tag_reduction'])} atomic components")
        else:
            print(f"   ➡️  No change in tag count")
    
    # Demonstrate search capabilities
    print("\n3️⃣  Demonstrating atomic search capabilities...")
    
    # Collect all atomic tags from processed albums
    all_atomic_tags = set()
    for album in sample_albums:
        processed = process_album_tags(album, config)
        all_atomic_tags.update(processed['atomic_tags'])
    
    print(f"\n📊 Total unique atomic tags across all albums: {len(all_atomic_tags)}")
    print(f"🏷️  Atomic tags: {sorted(all_atomic_tags)}")
    
    # Search examples
    search_examples = ['metal', 'progressive', 'experimental', 'rock']
    
    print("\n🔍 Search Examples:")
    for search_term in search_examples:
        matching_albums = []
        for album in sample_albums:
            processed = process_album_tags(album, config)
            if search_term in processed['atomic_tags']:
                matching_albums.append(album['title'])
        
        print(f"   '{search_term}' found in: {matching_albums}")
    
    # Performance comparison
    print("\n4️⃣  Performance comparison...")
    
    total_original_tags = sum(len(album['tags']) for album in sample_albums)
    total_atomic_tags = sum(len(process_album_tags(album, config)['atomic_tags']) for album in sample_albums)
    
    print(f"   Total original tags: {total_original_tags}")
    print(f"   Total atomic tags: {total_atomic_tags}")
    
    if total_atomic_tags < total_original_tags:
        reduction = ((total_original_tags - total_atomic_tags) / total_original_tags) * 100
        print(f"   ✅ Overall reduction: {reduction:.1f}%")
    else:
        expansion = ((total_atomic_tags - total_original_tags) / total_original_tags) * 100
        print(f"   📈 Overall expansion: {expansion:.1f}% (more semantic precision)")
    
    print("\n✅ INTEGRATION DEMONSTRATION COMPLETE!")

def create_production_adapter():
    """Create a production adapter for easy integration"""
    
    adapter_code = '''#!/usr/bin/env python3
"""
Production Adapter for Atomic Tag System

This adapter provides a simple interface for integrating atomic tags
into existing AlbumExplore production code.
"""

import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class AtomicTagAdapter:
    """Production adapter for atomic tag normalization"""
    
    def __init__(self, config_path: str = None):
        """Initialize the adapter"""
        if config_path is None:
            config_path = 'c:/Users/salmo/Documents/GitHub/AlbumExplore/src/albumexplore/config/tag_rules.json'
        
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load atomic tag configuration"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load atomic tag config: {e}")
            return {}
    
    def normalize_tags(self, tags: List[str]) -> List[str]:
        """Normalize a list of tags to atomic components"""
        if not tags:
            return []
        
        atomic_tags = []
        decomp_rules = self.config.get('atomic_decomposition', {})
        
        for tag in tags:
            if not tag:
                continue
                
            cleaned_tag = tag.lower().strip()
            
            # Check for decomposition rule
            if cleaned_tag in decomp_rules:
                atomic_tags.extend(decomp_rules[cleaned_tag])
            else:
                # Check for case variants
                found = False
                for rule_tag, components in decomp_rules.items():
                    if rule_tag.replace('-', ' ') == cleaned_tag.replace('-', ' '):
                        atomic_tags.extend(components)
                        found = True
                        break
                
                if not found:
                    atomic_tags.append(cleaned_tag)
        
        # Remove duplicates while preserving order
        unique_tags = []
        seen = set()
        for tag in atomic_tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        return unique_tags
    
    def is_atomic_tag(self, tag: str) -> bool:
        """Check if a tag is a valid atomic component"""
        valid_tags = self.config.get('atomic_tags', {}).get('all_valid_tags', [])
        return tag.lower() in valid_tags
    
    def get_core_genres(self) -> List[str]:
        """Get list of core genre atomic tags"""
        return self.config.get('atomic_tags', {}).get('core_genres', [])
    
    def get_style_modifiers(self) -> List[str]:
        """Get list of style modifier atomic tags"""
        return self.config.get('atomic_tags', {}).get('style_modifiers', [])

# Convenience function for easy integration
def normalize_album_tags(album_tags: List[str]) -> List[str]:
    """Simple function to normalize album tags to atomic components"""
    adapter = AtomicTagAdapter()
    return adapter.normalize_tags(album_tags)
'''
    
    adapter_file = 'c:/Users/salmo/Documents/GitHub/AlbumExplore/tag_consolidation/scripts/atomic_tag_adapter.py'
    with open(adapter_file, 'w', encoding='utf-8') as f:
        f.write(adapter_code)
    
    print(f"✅ Created production adapter: {adapter_file}")
    return adapter_file

def main():
    """Run the integration demonstration"""
    
    demonstrate_integration()
    
    print("\n📦 Creating production adapter...")
    adapter_path = create_production_adapter()
    
    print(f"\n🎯 QUICK INTEGRATION:")
    print("Add this to your existing code:")
    print(f"```python")
    print(f"from tag_consolidation.scripts.atomic_tag_adapter import normalize_album_tags")
    print(f"")
    print(f"# Convert any tag list to atomic components")
    print(f"atomic_tags = normalize_album_tags(['Progressive Metal', 'death-metal'])")
    print(f"# Returns: ['progressive', 'metal', 'death']")
    print(f"```")
    
    print(f"\n📚 Documentation: tag_consolidation/documentation/ATOMIC_TAG_INTEGRATION_GUIDE.md")

if __name__ == "__main__":
    main()
