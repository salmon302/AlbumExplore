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

def run_cli():
	"""Run the command-line interface version."""
	try:
		logging.basicConfig(level=logging.INFO)
		logging.info("Starting Album Explorer")
		
		# Initialize components
		csv_dir = Path(__file__).parent.parent / 'csv'
		if not csv_dir.exists():
			csv_dir.mkdir(parents=True)
			logging.info(f"Created CSV directory at {csv_dir}")
			
		parser = CSVParser(csv_dir)
		df = parser.parse()
		
		normalizer = TagNormalizer()
		relationships = TagRelationships(df)
		all_tags = set()
		
		for tags in df['tags']:
			all_tags.update(tags)
		
		while True:
			choice = display_menu()
			
			if choice == '1':
				print("\nAll Available Tags:")
				paginate_output(sorted(list(all_tags)))
				
			elif choice == '2':
				genre = input("Enter genre to search: ").lower()
				results = search_albums(df, genre)
				
				if len(results) == 0:
					print("No albums found with that genre.")
				else:
					print(f"\nFound {len(results)} albums:")
					paginate_output([f"{row['Artist']} - {row['Album']}" 
								   for _, row in results.iterrows()])
					
			elif choice == '3':
				tag = input("Enter tag to analyze: ").lower()
				rel_data = get_tag_relationships(tag, normalizer, relationships, all_tags)
				
				if rel_data is None:
					print("Tag not found or no relationships available.")
				else:
					print(f"\nRelationships for '{tag}':")
					for related_tag in rel_data['relationships']:
						print(f"- {related_tag}")
						
			elif choice == '4':
				artist = input("Enter artist name (or part of it): ")
				matches = df[df['Artist'].str.contains(artist, case=False, na=False)]
				
				if len(matches) == 0:
					print("No matching artists found.")
				else:
					print("\nMatching Albums:")
					album_details = []
					for _, row in matches.iterrows():
						details = f"Artist: {row['Artist']}\n"
						details += f"Album: {row['Album']}\n"
						details += f"Release Date: {row['Release Date']}\n"
						details += f"Genre: {row['Genre / Subgenres']}\n"
						details += f"Tags: {', '.join(row['tags'])}\n"
						album_details.append(details)
					paginate_output(album_details)
					
			elif choice == '5':
				print("\nExiting Album Explorer...")
				break
				
			else:
				print("Invalid choice. Please try again.")
				
	except Exception as e:
		logging.error(f"Error in CLI: {str(e)}")
		print(f"An error occurred: {str(e)}")

def main():
	"""Main application entry point."""
	# Parse command line arguments
	parser = argparse.ArgumentParser(description="Album Explorer")
	parser.add_argument("--gui", action="store_true", help="Launch GUI version")
	args = parser.parse_args()
	
	if args.gui:
		# Import and run GUI
		try:
			from albumexplore.gui.app import run_gui
			run_gui()
		except ImportError as e:
			logging.error(f"Failed to import GUI components: {str(e)}")
			print("Error: GUI components not available. Please ensure PyQt6 is installed.")
		except Exception as e:
			logging.error(f"Error launching GUI: {str(e)}")
			print(f"Error launching GUI: {str(e)}")
	else:
		# Run CLI version
		run_cli()

if __name__ == "__main__":
	main()