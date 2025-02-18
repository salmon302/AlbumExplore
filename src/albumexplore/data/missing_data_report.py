import pandas as pd
import logging
from pathlib import Path
from rich.console import Console
from rich.table import Table
from typing import Dict, List, Set, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MissingDataAnalyzer:
	"""Analyzes patterns of missing data in album CSV files."""
	
	def __init__(self, csv_dir: Path):
		self.csv_dir = csv_dir
		self.console = Console()
		
	def read_csv_file(self, file_path: Path) -> pd.DataFrame:
		"""Read CSV file with proper header detection."""
		try:
			# Read all lines to find header
			with open(file_path, 'r', encoding='utf-8') as f:
				lines = f.readlines()
			
			# Find the header row (contains Artist, Album, etc.)
			header_row = -1
			for i, line in enumerate(lines):
				if all(col in line for col in ['Artist', 'Album', 'Release Date', 'Length']):
					header_row = i
					break
			
			if header_row == -1:
				logger.error(f"No header found in {file_path}")
				return pd.DataFrame()
			
			# Create temporary file with only data from header row
			temp_content = lines[header_row:]
			temp_file = file_path.parent / f"temp_{file_path.name}"
			try:
				with open(temp_file, 'w', encoding='utf-8') as f:
					f.writelines(temp_content)
				
				# Read CSV with proper header
				df = pd.read_csv(temp_file)
				df['_source_file'] = file_path.name
				
				# Clean column names
				df.columns = df.columns.str.strip()
				
				return df
			finally:
				if temp_file.exists():
					temp_file.unlink()
			
		except Exception as e:
			logger.error(f"Error reading {file_path}: {str(e)}")
			return pd.DataFrame()

	def analyze_file(self, df: pd.DataFrame) -> Dict:
		"""Analyze missing data patterns in a dataframe."""
		if df.empty:
			return {
				'missing_data': {},
				'patterns': [],
				'file': 'Unknown'
			}
			
		results = {
			'missing_data': {},
			'patterns': [],
			'file': df['_source_file'].iloc[0]
		}
		
		# Check each required column
		required_columns = ['Artist', 'Album', 'Release Date', 'Genre / Subgenres', 'Vocal Style']
		for col in required_columns:
			if col in df.columns:
				missing_mask = df[col].isna() | (df[col].astype(str).str.strip() == '')
				missing_count = missing_mask.sum()
				if missing_count > 0:
					missing_rows = df[missing_mask]
					results['missing_data'][col] = {
						'count': missing_count,
						'percentage': round((missing_count / len(df)) * 100, 2),
						'examples': missing_rows[['Artist', 'Album']].head().to_dict('records') if all(c in df.columns for c in ['Artist', 'Album']) else []
					}
		
		# Analyze patterns
		if not df.empty:
			# Check for rows with multiple missing fields
			missing_mask = pd.DataFrame({
				col: df[col].isna() | (df[col].astype(str).str.strip() == '')
				for col in required_columns if col in df.columns
			})
			multiple_missing = missing_mask.sum(axis=1) > 1
			if multiple_missing.any():
				pattern_rows = df[multiple_missing]
				for _, row in pattern_rows.iterrows():
					missing_cols = [
						col for col in required_columns 
						if col in df.columns and (pd.isna(row[col]) or str(row[col]).strip() == '')
					]
					if missing_cols:
						results['patterns'].append({
							'artist': str(row.get('Artist', 'Unknown')),
							'album': str(row.get('Album', 'Unknown')),
							'missing_fields': missing_cols
						})
		
		return results
	
	def analyze_all_files(self) -> None:
		"""Analyze all CSV files and display results."""
		all_results = []
		total_entries = 0
		
		for file_path in self.csv_dir.glob('*.csv'):
			df = self.read_csv_file(file_path)
			if not df.empty:
				total_entries += len(df)
				results = self.analyze_file(df)
				all_results.append(results)
		
		self.display_results(all_results, total_entries)
	
	def display_results(self, all_results: List[Dict], total_entries: int) -> None:
		"""Display analysis results in formatted tables."""
		# Summary table
		self.console.print("\n[bold]Missing Data Summary[/bold]")
		summary_table = Table(show_header=True)
		summary_table.add_column("Field")
		summary_table.add_column("Total Missing")
		summary_table.add_column("Overall %")
		summary_table.add_column("Most Affected Files")
		
		field_totals = {}
		field_files = {}
		
		for result in all_results:
			for field, data in result['missing_data'].items():
				field_totals[field] = field_totals.get(field, 0) + data['count']
				if field not in field_files:
					field_files[field] = []
				field_files[field].append((result['file'], data['count']))
		
		for field in sorted(field_totals.keys()):
			total = field_totals[field]
			percentage = round((total / total_entries) * 100, 2)
			# Get top 3 affected files
			top_files = sorted(field_files[field], key=lambda x: x[1], reverse=True)[:3]
			files_str = ", ".join(f"{f[0]} ({f[1]})" for f in top_files)
			
			color = "red" if percentage > 5 else "yellow" if percentage > 1 else "green"
			summary_table.add_row(
				field,
				str(total),
				f"{percentage}%",
				files_str,
				style=color
			)
		
		self.console.print(summary_table)
		
		# Pattern Analysis
		self.console.print("\n[bold]Common Missing Data Patterns:[/bold]")
		patterns_table = Table(show_header=True)
		patterns_table.add_column("Pattern")
		patterns_table.add_column("Count")
		patterns_table.add_column("Example")
		
		pattern_counts = {}
		pattern_examples = {}
		
		for result in all_results:
			for pattern in result['patterns']:
				key = tuple(sorted(pattern['missing_fields']))
				pattern_counts[key] = pattern_counts.get(key, 0) + 1
				if key not in pattern_examples:
					pattern_examples[key] = f"{pattern['artist']} - {pattern['album']}"
		
		for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
			patterns_table.add_row(
				", ".join(pattern),
				str(count),
				pattern_examples[pattern]
			)
		
		self.console.print(patterns_table)

def main():
	csv_dir = Path("/home/seth-n/PycharmProjects/AlbumExplore/csv")
	analyzer = MissingDataAnalyzer(csv_dir)
	analyzer.analyze_all_files()

if __name__ == "__main__":
	main()