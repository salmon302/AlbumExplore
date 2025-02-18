import pandas as pd
from pathlib import Path
from rich.console import Console
from rich.table import Table
from .validators.data_validator import DataValidator
from .parsers.csv_parser import CSVParser

def test_data_fixes(csv_dir: Path) -> None:
	"""Test the data validation improvements."""
	console = Console()
	
	# Load and validate data
	parser = CSVParser(csv_dir)
	df = parser.parse()
	
	# Create validator
	validator = DataValidator(df)
	is_valid = validator.validate()
	
	# Display validation results
	console.print("\n[bold]Data Validation Results[/bold]")
	
	# Critical Issues Table
	critical_table = Table(title="Critical Issues")
	critical_table.add_column("Field")
	critical_table.add_column("Message")
	critical_table.add_column("Count", justify="right")
	
	for error in validator.errors:
		if isinstance(error, dict) and error.get('severity') == 'critical':
			critical_table.add_row(
				error.get('field', 'Unknown'),
				error.get('message', 'No message'),
				str(error.get('count', 'N/A')),
				style="red"
			)
	
	console.print(critical_table)
	
	# High Priority Issues Table
	high_table = Table(title="High Priority Issues")
	high_table.add_column("Field")
	high_table.add_column("Message")
	high_table.add_column("Count", justify="right")
	
	for error in validator.errors:
		if isinstance(error, dict) and error.get('severity') == 'high':
			high_table.add_row(
				error.get('field', 'Unknown'),
				error.get('message', 'No message'),
				str(error.get('count', 'N/A')),
				style="yellow"
			)
	
	console.print(high_table)
	
	# Inferred Data Table
	inferred_table = Table(title="Inferred Data")
	inferred_table.add_column("Field")
	inferred_table.add_column("Message")
	
	for warning in validator.warnings:
		if isinstance(warning, dict) and 'Inferred' in warning.get('message', ''):
			inferred_table.add_row(
				warning.get('field', 'Unknown'),
				warning.get('message', 'No message'),
				style="blue"
			)
	
	console.print(inferred_table)
	
	# Summary
	console.print(f"\n[bold]{'✓' if is_valid else '✗'} Validation {'Passed' if is_valid else 'Failed'}[/bold]")
	
	# Save fixed data
	if is_valid:
		output_path = csv_dir / 'fixed_data.csv'
		validator.df.to_csv(output_path, index=False)
		console.print(f"\nFixed data saved to: {output_path}")

def main():
	csv_dir = Path("/home/seth-n/PycharmProjects/AlbumExplore/csv")
	test_data_fixes(csv_dir)

if __name__ == "__main__":
	main()