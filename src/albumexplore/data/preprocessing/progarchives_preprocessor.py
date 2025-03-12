"""Preprocess ProgArchives HTML files into structured data."""
import argparse
import json
import logging
import sys
from pathlib import Path
import pandas as pd
from albumexplore.data.parsers.progarchives_parser import ProgArchivesParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_arg_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description='Preprocess ProgArchives HTML files into structured data'
    )
    parser.add_argument(
        '--input-dir',
        type=str,
        required=True,
        help='Directory containing ProgArchives HTML files'
    )
    parser.add_argument(
        '--output-file',
        type=str,
        required=True,
        help='Output file path (.json, .csv, or .xlsx)'
    )
    return parser

def save_data(df: pd.DataFrame, output_file: str) -> None:
    """Save DataFrame to file based on extension."""
    try:
        output_path = Path(output_file)
        format = output_path.suffix.lower()
        
        if format == '.json':
            df.to_json(output_path, orient='records', indent=2)
        elif format == '.csv':
            df.to_csv(output_path, index=False)
        elif format == '.xlsx':
            df.to_excel(output_path, index=False)
        else:
            raise ValueError(f"Unsupported output format: {format}")
            
        logger.info(f"Successfully saved data to {output_file}")
        
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        raise

def print_summary(df: pd.DataFrame) -> None:
    """Print summary statistics about the dataset."""
    logger.info("\nDataset Summary:")
    logger.info(f"Total albums: {len(df)}")
    
    logger.info("\nRecords by Subgenre:")
    subgenre_counts = df['subgenre'].value_counts()
    for subgenre, count in subgenre_counts.items():
        logger.info(f"{subgenre}: {count}")
        
    logger.info("\nRecord Types:")
    type_counts = df['record_type'].value_counts()
    for type_, count in type_counts.items():
        logger.info(f"{type_}: {count}")
        
    logger.info("\nTime Range:")
    logger.info(f"Years: {df['year'].min()} - {df['year'].max()}")
    
    if 'rating' in df.columns:
        logger.info("\nRatings:")
        logger.info(f"Average: {df['rating'].mean():.2f}")
        logger.info(f"Min: {df['rating'].min():.2f}")
        logger.info(f"Max: {df['rating'].max():.2f}")

def main():
    """Main entry point."""
    parser = setup_arg_parser()
    args = parser.parse_args()

    logger.info(f"Processing HTML files from {args.input_dir}")
    
    try:
        prog_parser = ProgArchivesParser(args.input_dir)
        df = prog_parser.parse()
        save_data(df, args.output_file)
        print_summary(df)
        
    except Exception as e:
        logger.error(f"Error during preprocessing: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()