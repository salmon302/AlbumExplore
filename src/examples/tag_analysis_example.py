from pathlib import Path
import pandas as pd
from src.data.parsers import CSVParser
from src.tags.analysis import TagAnalyzer, TagSimilarity

def main():
	"""Demonstrate tag analysis functionality."""
	# Load and parse data
	csv_path = Path(__file__).parent.parent.parent / '_r_ProgMetal _ Yearly Albums - 2025 Prog-metal.tsv'
	parser = CSVParser(csv_path)
	df = parser.parse()
	
	# Initialize analyzer and calculate relationships
	analyzer = TagAnalyzer(df)
	analyzer.calculate_relationships()
	
	# Get tag statistics
	stats = analyzer.analyze_tags()
	print("\nTag Statistics:")
	print(f"Total tags: {stats['total_tags']}")
	print(f"Unique tags: {stats['unique_tags']}")
	print(f"Average tags per album: {stats['avg_tags_per_album']:.2f}")
	
	print("\nMost Common Tags:")
	for tag, count in stats['most_common'][:10]:
		print(f"- {tag}: {count}")
	
	# Initialize similarity analyzer
	similarity = TagSimilarity(analyzer)
	similarity.calculate_similarities()
	
	# Show similar tags for some example genres
	example_tags = ['progressive metal', 'death metal', 'black metal']
	print("\nTag Similarities:")
	for tag in example_tags:
		print(f"\nSimilar to '{tag}':")
		similar_tags = similarity.find_similar_tags(tag, threshold=0.4)
		for similar_tag, sim_score in similar_tags[:5]:
			print(f"- {similar_tag}: {sim_score:.2f}")
	
	# Show some tag clusters
	print("\nTag Clusters:")
	clusters = analyzer.get_tag_clusters(min_size=3)
	for name, tags in list(clusters.items())[:5]:
		print(f"\n{name}:")
		print("- " + "\n- ".join(sorted(tags)))

if __name__ == "__main__":
	main()