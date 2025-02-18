from pathlib import Path
import pandas as pd
import logging
from rich.console import Console
from rich.table import Table
from .parsers.csv_parser import CSVParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MissingEntriesAnalyzer:
	"""Analyzes missing entries in album data with source file tracking."""
	
	def __init__(self, csv_dir: Path):
		self.csv_dir = csv_dir
		self.console = Console()
		
	def analyze_file(self, file_path: Path) -> dict:
		"""Analyze missing data in a single file."""
		try:
			# Use CSVParser to read the file
			parser = CSVParser(file_path)
			df = parser.parse_single_csv(file_path)
			df['_source_file'] = file_path.name
			
			missing_data = {
				'album_titles': [],
				'genres': [],
				'release_dates': [],
				'vocal_styles': [],
				'locations': []
			}
			
			# Find missing album titles
			missing_albums = df[df['Album'].isna() | (df['Album'].astype(str).str.strip() == '')]
			for _, row in missing_albums.iterrows():
					'artist': row.get('Artist', 'Unknown'),
					'file': row['_source_file'],
					'row_number': row.name + 2  # +2 for header and 1-based indexing
				})
			
			# Find missing genres
			missing_genres = df[df['Genre / Subgenres'].isna() | (df['Genre / Subgenres'].str.strip() == '')]
			for _, row in missing_genres.iterrows():
				missing_data['genres'].append({
					'artist': row['Artist'],
					'album': row.get('Album', 'Unknown'),
					'file': row['_source_file'],
					'row_number': row.name + 2
				})
			
			# Find missing release dates
			missing_dates = df[df['Release Date'].isna() | (df['Release Date'].str.strip() == '')]
			for _, row in missing_dates.iterrows():
				missing_data['release_dates'].append({
					'artist': row['Artist'],
					'album': row.get('Album', 'Unknown'),
					'file': row['_source_file'],
					'row_number': row.name + 2
				})
			
			# Find missing vocal styles
			missing_vocals = df[df['Vocal Style'].isna() | (df['Vocal Style'].str.strip() == '')]
			for _, row in missing_vocals.iterrows():
				missing_data['vocal_styles'].append({
					'artist': row['Artist'],
					'album': row.get('Album', 'Unknown'),
					'file': row['_source_file'],
					'row_number': row.name + 2
				})
			
			# Find location format issues
			location_issues = df[~df['Country / State'].str.contains(',', na=False)]
			for _, row in location_issues.iterrows():
				missing_data['locations'].append({
					'artist': row['Artist'],
					'album': row.get('Album', 'Unknown'),
					'location': row['Country / State'],
					'file': row['_source_file'],
					'row_number': row.name + 2
				})
			
			return missing_data
			
		except Exception as e:
			logger.error(f"Error analyzing file {file_path}: {str(e)}")
			return {}
	
	def display_missing_entries(self, missing_data: dict) -> None:
		"""Display missing entries in a formatted table."""
		# Display missing album titles
		if missing_data['album_titles']:
			self.console.print("\n[bold red]Missing Album Titles:[/bold red]")
			table = Table(show_header=True)
			table.add_column("Artist")
			table.add_column("File")
			table.add_column("Row")
			
			for entry in missing_data['album_titles']:
				table.add_row(
					entry['artist'],
					entry['file'],
					str(entry['row_number'])
				)
			self.console.print(table)
		
		# Display missing genres
		if missing_data['genres']:
			self.console.print("\n[bold yellow]Missing Genres:[/bold yellow]")
			table = Table(show_header=True)
			table.add_column("Artist")
			table.add_column("Album")
			table.add_column("File")
			table.add_column("Row")
			
			for entry in missing_data['genres']:
				table.add_row(
					entry['artist'],
					entry['album'],
					entry['file'],
					str(entry['row_number'])
				)
			self.console.print(table)
		
		# Display missing release dates
		if missing_data['release_dates']:
			self.console.print("\n[bold blue]Missing Release Dates:[/bold blue]")
			table = Table(show_header=True)
			table.add_column("Artist")
			table.add_column("Album")
			table.add_column("File")
			table.add_column("Row")
			
			for entry in missing_data['release_dates']:
				table.add_row(
					entry['artist'],
					entry['album'],
					entry['file'],
					str(entry['row_number'])
				)
			self.console.print(table)
		
		# Display missing vocal styles
		if missing_data['vocal_styles']:
			self.console.print("\n[bold magenta]Missing Vocal Styles:[/bold magenta]")
			table = Table(show_header=True)
			table.add_column("Artist")
			table.add_column("Album")
			table.add_column("File")
			table.add_column("Row")
			
			for entry in missing_data['vocal_styles']:
				table.add_row(
					entry['artist'],
					entry['album'],
					entry['file'],
					str(entry['row_number'])
				)
			self.console.print(table)
		
		# Display location format issues
		if missing_data['locations']:
			self.console.print("\n[bold green]Location Format Issues:[/bold green]")
			table = Table(show_header=True)
			table.add_column("Artist")
			table.add_column("Album")
			table.add_column("Location")
			table.add_column("File")
			table.add_column("Row")
			
			for entry in missing_data['locations']:
				table.add_row(
					entry['artist'],
					entry['album'],
					entry['location'],
					entry['file'],
					str(entry['row_number'])
				)
			self.console.print(table)
	
	def analyze_all_files(self) -> None:
		"""Analyze all CSV files in the directory."""
		all_missing_data = {
			'album_titles': [],
			'genres': [],
			'release_dates': [],
			'vocal_styles': [],
			'locations': []
		}
		
		for file_path in self.csv_dir.glob('*.csv'):
			file_data = self.analyze_file(file_path)
			for category in all_missing_data:
				all_missing_data[category].extend(file_data.get(category, []))
		
		self.display_missing_entries(all_missing_data)

def main():
	csv_dir = Path("/home/seth-n/PycharmProjects/AlbumExplore/csv")
	analyzer = MissingEntriesAnalyzer(csv_dir)
	analyzer.analyze_all_files()

if __name__ == "__main__":
	main()