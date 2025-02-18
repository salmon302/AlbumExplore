import pandas as pd
from pathlib import Path
from typing import List, Set
from collections import Counter

from albumexplore.src.data.utils import extract_tags_from_csv

def analyze_tags_in_directory(csv_dir: Path) -> Counter:
	"""Analyze tags across multiple CSV files in a directory."""
	all_tags = Counter()
	for csv_file in csv_dir.glob('*.csv'):
		tags = extract_tags_from_csv(csv_file)
		all_tags.update(tags)
	return all_tags

if __name__ == "__main__":
	csv_directory = Path("/home/seth-n/PycharmProjects/AlbumExplore/csv")
	tag_counts = analyze_tags_in_directory(csv_directory)
	
	print("Total Tag Counts:")
	for tag, count in tag_counts.most_common():
		print(f"- {tag}: {count}")
	
	print("\nUnique Tags:")
	unique_tags = set(tag_counts.keys())
	print(f"Total unique tags: {len(unique_tags)}")
