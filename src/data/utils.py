import pandas as pd
from pathlib import Path
from typing import List

def extract_tags_from_csv(csv_file_path: Path) -> List[str]:
	"""Extract tags from a CSV file.
	
	Args:
		csv_file_path: Path to the CSV file containing album data
		
	Returns:
		List of extracted genre tags
		
	Raises:
		FileNotFoundError: If CSV file is not found
		pd.errors.EmptyDataError: If CSV file is empty
		pd.errors.ParserError: If CSV file cannot be parsed
	"""
	try:
		df = pd.read_csv(csv_file_path)
		if 'Genre / Subgenres' in df.columns:
			tags = []
			for index, row in df.iterrows():
				genre_tags = row['Genre / Subgenres']
				if isinstance(genre_tags, str):
					tags.extend([tag.strip().lower() for tag in genre_tags.split(',')])
			return tags
		else:
			return []
	except FileNotFoundError:
		print(f"Error: CSV file not found at {csv_file_path}")
		return []
	except pd.errors.EmptyDataError:
		print(f"Error: CSV file is empty at {csv_file_path}")
		return []
	except pd.errors.ParserError:
		print(f"Error: Could not parse CSV file at {csv_file_path}")
		return []