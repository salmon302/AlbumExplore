import sys
from pathlib import Path
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from albumexplore.data.missing_data_analyzer import analyze_missing_data

def display_results(results: dict) -> None:
	"""Display analysis results with focus on priority fields."""
	console = Console()
	
	# Display critical and high priority issues first
	critical_table = Table(title="Critical and High Priority Issues")
	critical_table.add_column("Field", style="bold")
	critical_table.add_column("Priority")
	critical_table.add_column("Missing %")
	critical_table.add_column("Count")
	critical_table.add_column("Severity", style="bold")
	
	missing_counts = results['missing_counts']
	for field, stats in missing_counts.items():
		if 'priority' in stats and stats['priority'] <= 3:  # Critical and high priority only
			severity_color = "red" if stats['severity'] == 'critical' else "yellow"
			critical_table.add_row(
				field,
				str(stats['priority']),
				f"{stats['missing_percentage']}%",
				str(stats['missing_count']),
				stats['severity'],
				style=severity_color
			)
	
	console.print(critical_table)
	
	# Display medium priority issues
	if any(stats.get('priority', 7) in [4, 5] for stats in missing_counts.values()):
		medium_table = Table(title="Medium Priority Issues")
		medium_table.add_column("Field")
		medium_table.add_column("Priority")
		medium_table.add_column("Missing %")
		
		for field, stats in missing_counts.items():
			if stats.get('priority', 7) in [4, 5]:
				medium_table.add_row(
					field,
					str(stats['priority']),
					f"{stats['missing_percentage']}%"
				)
		
		console.print("\n", medium_table)
	
	# Display recommendations
	console.print("\n[bold]Prioritized Recommendations:[/bold]")
	for rec in results['recommendations']:
		if rec['severity'] != 'low':  # Skip low priority recommendations
			color = "red" if rec['severity'] == 'critical' else \
					"yellow" if rec['severity'] == 'high' else "blue"
			console.print(f"Priority {rec['priority']}: {rec['message']}", style=color)
	
	# Display partial data patterns that affect priority fields
	patterns = results['missing_patterns']['partial_data']
	priority_patterns = [p for p in patterns if any(
		field in p['type'] for field in ['date', 'genre', 'location']
	)]
	if priority_patterns:
		console.print("\n[bold]Data Quality Patterns:[/bold]")
		for pattern in priority_patterns:
			console.print(f"- {pattern['type']}: {pattern['count']} instances")

def main():
	if len(sys.argv) != 2:
		print("Usage: python analyze_missing_data.py <csv_directory>")
		sys.exit(1)
	
	csv_dir = Path(sys.argv[1])
	if not csv_dir.exists():
		print(f"Directory not found: {csv_dir}")
		sys.exit(1)
	
	results = analyze_missing_data(csv_dir)
	if results:
		display_results(results)
	else:
		print("No results found or error occurred during analysis.")

if __name__ == "__main__":
	main()