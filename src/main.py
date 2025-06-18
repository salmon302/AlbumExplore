from pathlib import Path
from albumexplore.data.parsers.csv_parser import CSVParser
from albumexplore.data.validators.data_validator import DataValidator
from albumexplore.tags.normalizer import TagNormalizer
from albumexplore.tags.relationships import TagRelationships
import argparse
import pandas as pd
import logging

def paginate_output(items, page_size=20):
	"""Display items with pagination."""
	total_pages = (len(items) + page_size - 1) // page_size
	current_page = 1
	
	while True:
		start_idx = (current_page - 1) * page_size
		end_idx = start_idx + page_size
		page_items = items[start_idx:end_idx]
		
		print(f"\nPage {current_page} of {total_pages}:")
		for item in page_items:
			print(item)
		
		if total_pages > 1:
			choice = input("\nEnter 'n' for next page, 'p' for previous page, or 'q' to quit: ").lower()
			if choice == 'n' and current_page < total_pages:
				current_page += 1
			elif choice == 'p' and current_page > 1:
				current_page -= 1
			elif choice == 'q':
				break
		else:
			input("\nPress Enter to continue...")
			break

def display_menu():
	print("\nAlbum Explorer Menu:")
	print("1. Show all tags")
	print("2. Search by genre")
	print("3. Show tag relationships")
	print("4. Show album details")
	print("5. Exit")
	return input("\nSelect an option (1-5): ")

def search_albums(df: pd.DataFrame, search_tag: str) -> pd.DataFrame:
	"""Search for albums by tag."""
	return df[df['tags'].apply(lambda x: any(search_tag in tag.lower() for tag in x))]

def get_tag_relationships(tag: str, normalizer: TagNormalizer, 
						 relationships: TagRelationships, all_tags: set) -> dict:
	"""Get tag relationships."""
	if tag not in all_tags:
		return None
		
	normalized = normalizer.normalize(tag)
	related = relationships.get_related_tags(normalized)
	
	if not related:
		return None
		
	return {
		'tag': tag,
		'relationships': related[:5]
	}


def run_cli(csv_directory="csv"):
	"""Run the command-line interface version."""
	try:
		logging.basicConfig(level=logging.INFO)
		logging.info("Starting Album Explorer")
		
		# Initialize components
		csv_dir = Path(csv_directory)
		if not csv_dir.exists():
			csv_dir.mkdir(parents=True)
			logging.info(f"Created CSV directory at {csv_dir}")
		
		# Check if directory contains CSV files
		csv_files = list(csv_dir.glob('*.csv'))
		if not csv_files:
			logging.error("No CSV files found in directory")
			print("\nNo CSV files found. Please add CSV files to the 'csv' directory.")
			return
			
		logging.info(f"Found {len(csv_files)} CSV files")
		
		# Initialize parser
		parser = CSVParser(csv_dir)
		
		# Process data
		df = parser.parse()
		if df.empty:
			logging.error("No data was parsed from CSV files")
			print("\nNo data could be parsed from CSV files. Please check file format.")
			return
			
		# Validate data
		validator = DataValidator(df)
		validator.validate()
		if validator.validation_errors:
			logging.warning("Data validation found errors:")
			for error in validator.validation_errors:
				logging.warning(f"- {error}")
			
			# Check if we have minimum required data to continue
			if 'Genre / Subgenres' not in df.columns:
				logging.error("Cannot continue without Genre/Subgenres data")
				print("\nMissing required Genre/Subgenres data. Please check your CSV files.")
				return
		
		if validator.validation_warnings:
			logging.info("Data validation found warnings:")
			for warning in validator.validation_warnings:
				logging.info(f"- {warning}")
		
		# Extract tags after validation
		if 'tags' not in df.columns:
			logging.error("Tags column not found after data cleaning")
			print("\nError processing genre tags. Please check CSV format.")
			return
		
		all_tags = set()
		for tags in df['tags']:
			if isinstance(tags, list):
				all_tags.update(tags)
		
		if not all_tags:
			logging.error("No valid tags found in the data")
			print("\nNo genre tags found. Please check your CSV files.")
			return
		
		logging.info(f"Loaded {len(df)} albums with {len(all_tags)} unique tags")
		
		# Initialize other components
		normalizer = TagNormalizer()
		relationships = TagRelationships()
		
		# Add year information to display
		def extract_year(date_str):
			if not pd.notna(date_str):
				return 'Unknown'
			try:
				parts = str(date_str).split()
				if len(parts) > 0 and parts[-1].isdigit():
					return parts[-1]
				# Try to get year from filename if date parsing failed
				file_year = [y for y in str(csv_dir).split('_') if y.isdigit()]
				return file_year[0] if file_year else 'Unknown'
			except:
				return 'Unknown'

		df['Year'] = df['Release Date'].apply(extract_year)


		while True:
			try:
				choice = display_menu()
				
				if choice == '1':
					logging.info("Displaying all tags")
					tag_list = [f"- {tag}" for tag in sorted(all_tags)]
					paginate_output(tag_list)
				
				elif choice == '2':
					search_tag = input("\nEnter genre to search: ").lower().strip()
					logging.info(f"Searching for genre: {search_tag}")
					matches = search_albums(df, search_tag)
					if len(matches) > 0:
						print(f"\nFound {len(matches)} albums:")
						album_list = [
							f"- {str(row['Artist'])} - {str(row['Album'])} ({str(row['Release Date']) if pd.notna(row['Release Date']) else 'Unknown'}) [{str(row['Year'])}]" 
							for _, row in matches.iterrows()
						]
						paginate_output(album_list)
					else:
						print("\nNo albums found with that genre.")
				
				elif choice == '3':
					tag = input("\nEnter tag to show relationships: ").lower().strip()
					logging.info(f"Getting relationships for tag: {tag}")
					result = get_tag_relationships(tag, normalizer, relationships, all_tags)
					if result:
						print(f"\nRelationships for {result['tag']}:")
						for related_tag, weight in result['relationships']:
							print(f"- {related_tag} (strength: {weight:.2f})")
					else:
						print("\nNo relationships found for this tag.")
						similar_tags = [t for t in all_tags if tag in t.lower()]
						if similar_tags:
							print("Similar tags found:")
							for t in sorted(similar_tags)[:5]:
								print(f"- {t}")
				
				elif choice == '4':
					artist = input("\nEnter artist name: ").strip()
					logging.info(f"Searching for artist: {artist}")
					matches = df[df['Artist'].str.lower().str.contains(artist.lower())]
					if len(matches) > 0:
						for _, row in matches.iterrows():
							print("\n" + "="*50)
							print(f"Artist: {row['Artist']}")
							print(f"Album: {row['Album']}")
							print(f"Release Date: {row['Release Date']} [{row['Year']}]")
							print(f"Genre/Subgenres: {row['Genre / Subgenres']}")
							print(f"Vocal Style: {row['Vocal Style']}")
							print(f"Country/State: {row['Country / State']}")
							if pd.notna(row['Bandcamp']) and row['Bandcamp'] == 'BC':
								print("Available on: Bandcamp")
							if pd.notna(row['Spotify']) and row['Spotify'] == 'S':
								print("Available on: Spotify")
							print("="*50)
					else:
						print("\nNo matching artists found.")
				
				elif choice == '5':
					print("\nExiting Album Explorer...")
					logging.info("Application terminated by user")
					break
				
				else:
					print("\nInvalid choice. Please select 1-5.")
			
			except Exception as e:
				logging.error(f"Error during operation: {str(e)}")
				print(f"\nAn error occurred: {str(e)}")
	
	except Exception as e:
		logging.error(f"Fatal error: {str(e)}")
		print(f"\nFatal error occurred: {str(e)}")

def main():
	"""Main application entry point."""
	# Parse command line arguments
	parser = argparse.ArgumentParser(description="Album Explorer")
	parser.add_argument("--gui", action="store_true", help="Launch GUI version")
	parser.add_argument("--csv-dir", type=str, help="CSV directory for CLI mode", default="csv")
	args = parser.parse_args()
	
	if args.gui:
		# Import and run GUI
		try:
			from gui.app import run_gui
			run_gui()
		except ImportError as e:
			logging.error(f"Failed to import GUI components: {str(e)}")
			print("Error: GUI components not available. Please ensure PyQt6 is installed.")
		except Exception as e:
			logging.error(f"Error launching GUI: {str(e)}")
			print(f"Error launching GUI: {str(e)}")
	else:
		# Run CLI version with specified CSV directory
		run_cli(args.csv_dir)

if __name__ == "__main__":
	main()
