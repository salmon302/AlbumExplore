import pandas as pd
import json
import re
from collections import defaultdict

class TagNormalizer:
    def __init__(self, alias_file='aliases.json', stop_words_file='stop_words.txt'):
        self.aliases = self._load_json(alias_file)
        self.stop_words = self._load_stop_words(stop_words_file)

    def _load_json(self, file_path):
        with open(file_path, 'r') as f:
            return json.load(f)

    def _load_stop_words(self, file_path):
        with open(file_path, 'r') as f:
            return set([line.strip() for line in f])

    def normalize(self, tag):
        # Initial cleanup
        tag = tag.lower().strip()

        # Alias replacement
        tag = self.aliases.get(tag, tag)

        # Remove stop words
        tag_parts = [part for part in tag.split() if part not in self.stop_words]
        tag = " ".join(tag_parts)

        # Character and punctuation standardization
        tag = re.sub(r'[\-&/]', ' ', tag)  # Replace hyphens, ampersands, slashes with space
        tag = re.sub(r'[^\w\s]', '', tag)  # Remove remaining punctuation
        tag = re.sub(r'\s+', ' ', tag).strip()  # Collapse multiple spaces

        # Component reordering
        parts = sorted(tag.split())
        return " ".join(parts)

def process_tags(input_csv, output_csv):
    normalizer = TagNormalizer()
    df = pd.read_csv(input_csv)

    # We only need the first part of the file, which contains the raw tags.
    # The provided CSV seems to have a mix of raw and processed tags.
    # Let's find the split point. It seems to be where 'Tag' becomes lowercase.
    # A simpler heuristic for this file is that `Processed Count` is 0 for raw tags.
    raw_tags_df = df[df['Processed Count'] == 0].copy()
    
    if raw_tags_df.empty:
        # if the file is already processed, we might need a different heuristic
        # for now let's assume the input has raw tags.
        # Fallback to using all tags if the above logic fails.
        raw_tags_df = df.copy()


    raw_tags_df['Normalized Form'] = raw_tags_df['Tag'].apply(normalizer.normalize)

    # Aggregate counts
    normalized_counts = raw_tags_df.groupby('Normalized Form')['Raw Count'].sum().reset_index()
    normalized_counts.rename(columns={'Raw Count': 'Total Count'}, inplace=True)
    
    # For detailed output, we can merge back
    detailed_output = pd.merge(raw_tags_df, normalized_counts, on='Normalized Form')
    
    # Save the processed data
    detailed_output.to_csv(output_csv, index=False)
    print(f"Processed tags saved to {output_csv}")
    
    # Also save just the summary
    summary_output_csv = output_csv.replace('.csv', '_summary.csv')
    normalized_counts.sort_values(by='Total Count', ascending=False).to_csv(summary_output_csv, index=False)
    print(f"Summary of processed tags saved to {summary_output_csv}")


if __name__ == '__main__':
    # Using the attached file as input
    input_file = 'logs/tags 6 14 25.csv'
    output_file = 'logs/normalized_tags.csv'
    process_tags(input_file, output_file) 