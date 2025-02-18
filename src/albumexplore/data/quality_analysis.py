from pathlib import Path
import pandas as pd
from rich.console import Console
from rich.table import Table
from .parsers.csv_parser import CSVParser

def find_missing_entries(df: pd.DataFrame, column: str) -> pd.DataFrame:
	"""Find entries with missing data in specified column."""
	return df[
		df[column].isna() | 
		(df[column].astype(str).str.strip() == '')
	]

def analyze_missing_patterns(missing_df: pd.DataFrame, source_file: str) -> dict:
	"""Analyze patterns in missing data."""
	return {
		'total_missing': len(missing_df),
		'source_file': source_file,
		'year': source_file.split('-')[-1].split('.')[0].strip(),
		'has_artist': missing_df['Artist'].notna().sum(),
		'has_genre': missing_df['Genre / Subgenres'].notna().sum(),
		'has_date': missing_df['Release Date'].notna().sum()
	}

def find_quality_issues(csv_dir: Path) -> dict:
	"""Find and analyze data quality issues."""
	parser = CSVParser(csv_dir)
	df = parser.parse()
	
	results = {
		'missing_albums': [],
		'missing_genres': [],
		'missing_dates': [],
		'missing_vocals': [],
		'location_issues': []
	}
	
	# Find missing album titles
	missing_albums = find_missing_entries(df, 'Album')
	for _, row in missing_albums.iterrows():
		results['missing_albums'].append({
			'artist': row.get('Artist', 'Unknown'),
			'genre': row.get('Genre / Subgenres', 'Unknown'),
			'date': row.get('Release Date', 'Unknown'),
			'file': row.get('_source_file', 'Unknown')
		})
	
	# Find missing genres
	missing_genres = find_missing_entries(df, 'Genre / Subgenres')
	for _, row in missing_genres.iterrows():
		results['missing_genres'].append({
			'artist': row['Artist'],
			'album': row['Album'],
			'date': row.get('Release Date', 'Unknown'),
			'file': row.get('_source_file', 'Unknown')
		})
	
	# Find missing dates
	missing_dates = find_missing_entries(df, 'Release Date')
	for _, row in missing_dates.iterrows():
		results['missing_dates'].append({
			'artist': row['Artist'],
			'album': row['Album'],
			'genre': row.get('Genre / Subgenres', 'Unknown'),
			'file': row.get('_source_file', 'Unknown')
		})
	
	# Find missing vocal styles
	missing_vocals = find_missing_entries(df, 'Vocal Style')
	for _, row in missing_vocals.iterrows():
		results['missing_vocals'].append({
			'artist': row['Artist'],
			'album': row['Album'],
			'genre': row.get('Genre / Subgenres', 'Unknown'),
			'file': row.get('_source_file', 'Unknown')
		})
	
	# Find location format issues
	location_issues = df[~df['Country / State'].str.contains(',', na=False)]
	for _, row in location_issues.iterrows():
		results['location_issues'].append({
			'artist': row['Artist'],
			'album': row['Album'],
			'location': row['Country / State'],
			'file': row.get('_source_file', 'Unknown')
		})
	
	return results

def display_quality_issues(results: dict) -> None:
	"""Display data quality issues in a formatted way."""
	console = Console()
	
	# Display missing album titles
	if results['missing_albums']:
		console.print("\n[bold red]Missing Album Titles:[/bold red]")
		table = Table(show_header=True, header_style="bold")
		table.add_column("Artist")
		table.add_column("Genre")
		table.add_column("Release Date")
		table.add_column("Source File")
		
		for entry in results['missing_albums']:
			table.add_row(
				entry['artist'],
				entry['genre'],
				entry['date'],
				entry['file']
			)
		console.print(table)
	
	# Display missing genres
	if results['missing_genres']:
		console.print("\n[bold yellow]Missing Genres:[/bold yellow]")
		table = Table(show_header=True, header_style="bold")
		table.add_column("Artist")
		table.add_column("Album")
		table.add_column("Release Date")
		table.add_column("Source File")
		
		for entry in results['missing_genres']:
			table.add_row(
				entry['artist'],
				entry['album'],
				entry['date'],
				entry['file']
			)
		console.print(table)
	
	# Display missing dates
	if results['missing_dates']:
		console.print("\n[bold blue]Missing Release Dates:[/bold blue]")
		table = Table(show_header=True, header_style="bold")
		table.add_column("Artist")
		table.add_column("Album")
		table.add_column("Genre")
		table.add_column("Source File")
		
		for entry in results['missing_dates']:
			table.add_row(
				entry['artist'],
				entry['album'],
				entry['genre'],
				entry['file']
			)
		console.print(table)
	
	# Display missing vocal styles
	if results['missing_vocals']:
		console.print("\n[bold magenta]Missing Vocal Styles:[/bold magenta]")
		table = Table(show_header=True, header_style="bold")
		table.add_column("Artist")
		table.add_column("Album")
		table.add_column("Genre")
		table.add_column("Source File")
		
		for entry in results['missing_vocals']:
			table.add_row(
				entry['artist'],
				entry['album'],
				entry['genre'],
				entry['file']
			)
		console.print(table)
	
	# Display location format issues
	if results['location_issues']:
		console.print("\n[bold green]Location Format Issues:[/bold green]")
		table = Table(show_header=True, header_style="bold")
		table.add_column("Artist")
		table.add_column("Album")
		table.add_column("Location")
		table.add_column("Source File")
		
		for entry in results['location_issues']:
			table.add_row(
				entry['artist'],
				entry['album'],
				entry['location'],
				entry['file']
			)
		console.print(table)

def main():
	csv_dir = Path("/home/seth-n/PycharmProjects/AlbumExplore/csv")
	results = find_quality_issues(csv_dir)
	display_quality_issues(results)

if __name__ == "__main__":
	main()