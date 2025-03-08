#!/usr/bin/env python3
"""
Tag Export Utility

This script exports all unique tags and their counts from the album database
to a CSV file for further analysis and tag consolidation improvements.
"""

import os
import csv
import sqlite3
import argparse
from pathlib import Path
from collections import Counter
from typing import List, Tuple, Dict, Set, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add project root to path if running script directly
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from albumexplore.database import models
from albumexplore.tags.normalizer import TagNormalizer


def get_db_session(db_path: Optional[str] = None) -> Session:
    """Create a database session."""
    if db_path is None:
        # Default to albumexplore.db in project root
        db_path = str(Path(__file__).parent.parent.parent.parent / "albumexplore.db")
    
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    return Session()


def get_tag_counts(db_session: Session) -> Counter:
    """Extract tag counts from the database."""
    print("Extracting tags from database...")
    tag_counts = Counter()
    
    # Get all albums with their tags
    albums = db_session.query(models.Album).all()
    total_albums = len(albums)
    
    print(f"Processing {total_albums} albums...")
    for i, album in enumerate(albums):
        if i % 100 == 0:
            print(f"Processed {i}/{total_albums} albums")
        
        # Extract tags from album
        for tag in album.tags:
            tag_counts[tag.name] += 1
    
    print(f"Found {len(tag_counts)} unique tags across {total_albums} albums")
    return tag_counts


def analyze_tag_relationships(tag_counts: Counter, db_session: Session) -> Dict:
    """Analyze tag relationships and hierarchies."""
    print("Analyzing tag relationships...")
    
    # Get tag relationships from database
    tag_relationships = db_session.query(models.TagRelation).all()
    
    # Create relationship mapping
    relationship_data = {
        "hierarchies": [],
        "similar_tags": [],
        "co_occurrences": []
    }
    
    # Extract relationship data
    for relation in tag_relationships:
        if relation.relationship_type == "parent":
            relationship_data["hierarchies"].append({
                "parent": relation.tag1_id,
                "child": relation.tag2_id,
                "strength": relation.strength
            })
        elif relation.relationship_type == "similar":
            relationship_data["similar_tags"].append({
                "tag1": relation.tag1_id,
                "tag2": relation.tag2_id,
                "strength": relation.strength
            })
    
    return relationship_data


def analyze_normalized_tags(tag_counts: Counter) -> Dict:
    """Analyze tags using the tag normalizer."""
    print("Analyzing tags using normalizer...")
    normalizer = TagNormalizer()
    
    normalization_stats = {
        "total": len(tag_counts),
        "normalized_forms": Counter(),
        "potential_duplicates": []
    }
    
    # Group by normalized form
    normalized_groups = {}
    for tag in tag_counts:
        normalized = normalizer.normalize(tag)
        if normalized not in normalized_groups:
            normalized_groups[normalized] = []
        normalized_groups[normalized].append((tag, tag_counts[tag]))
        normalization_stats["normalized_forms"][normalized] += tag_counts[tag]
    
    # Find potential duplicates (same normalized form but different original tags)
    for normalized, variants in normalized_groups.items():
        if len(variants) > 1:
            normalization_stats["potential_duplicates"].append({
                "normalized": normalized,
                "variants": variants
            })
    
    print(f"Found {len(normalization_stats['normalized_forms'])} unique normalized forms")
    print(f"Found {len(normalization_stats['potential_duplicates'])} potential duplicate groups")
    
    return normalization_stats


def export_tag_data(tag_counts: Counter, 
                   relationship_data: Dict,
                   normalization_stats: Dict,
                   output_dir: str) -> None:
    """Export tag data to CSV files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Export basic tag counts
    print(f"Exporting tag counts to {output_path/'tag_counts.csv'}...")
    with open(output_path / "tag_counts.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Tag", "Count"])
        for tag, count in tag_counts.most_common():
            writer.writerow([tag, count])
    
    # Export normalized tag data
    print(f"Exporting normalized tag data to {output_path/'normalized_tags.csv'}...")
    with open(output_path / "normalized_tags.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Normalized Form", "Count", "Variants"])
        for norm_form, count in normalization_stats["normalized_forms"].most_common():
            variants = [v[0] for v in next((g["variants"] for g in normalization_stats["potential_duplicates"] 
                                          if g["normalized"] == norm_form), [])]
            variants_str = "|".join(variants) if variants else ""
            writer.writerow([norm_form, count, variants_str])
    
    # Export potential duplicates
    print(f"Exporting duplicate candidates to {output_path/'duplicate_candidates.csv'}...")
    with open(output_path / "duplicate_candidates.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Normalized Form", "Variant", "Count"])
        for duplicate in normalization_stats["potential_duplicates"]:
            for variant, count in duplicate["variants"]:
                writer.writerow([duplicate["normalized"], variant, count])
    
    # Export relationship data
    print(f"Exporting tag relationships to {output_path/'tag_relationships.csv'}...")
    if relationship_data["hierarchies"]:
        with open(output_path / "tag_hierarchies.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Parent", "Child", "Strength"])
            for hierarchy in relationship_data["hierarchies"]:
                writer.writerow([hierarchy["parent"], hierarchy["child"], hierarchy["strength"]])
    
    if relationship_data["similar_tags"]:
        with open(output_path / "tag_similarities.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Tag1", "Tag2", "Strength"])
            for similar in relationship_data["similar_tags"]:
                writer.writerow([similar["tag1"], similar["tag2"], similar["strength"]])
    
    print("Export complete!")


def main():
    parser = argparse.ArgumentParser(description="Export tag data for analysis and consolidation")
    parser.add_argument("--db-path", type=str, help="Path to the SQLite database")
    parser.add_argument("--output-dir", type=str, default="tag_analysis", help="Output directory for exported files")
    
    args = parser.parse_args()
    
    # Create database session
    db_session = get_db_session(args.db_path)
    
    try:
        # Extract tag counts
        tag_counts = get_tag_counts(db_session)
        
        # Analyze tag relationships
        relationship_data = analyze_tag_relationships(tag_counts, db_session)
        
        # Analyze normalized forms
        normalization_stats = analyze_normalized_tags(tag_counts)
        
        # Export the data
        export_tag_data(tag_counts, relationship_data, normalization_stats, args.output_dir)
        
    finally:
        db_session.close()
    
    print("Done!")


if __name__ == "__main__":
    main()