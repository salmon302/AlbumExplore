import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from ..data.parsers.csv_parser import CSVParser
from . import models

logger = logging.getLogger(__name__)

def parse_date(date_str):
	"""Convert date string to datetime object."""
	try:
		if pd.isna(date_str):
			return None
		return datetime.strptime(date_str, '%Y-%m-%d')
	except ValueError:
		return None

def load_csv_data(db: Session, csv_dir: Path):
	"""Load CSV data into the database."""
	try:
		logger.info("Loading CSV data...")
		parser = CSVParser(csv_dir)
		df = parser.parse()
		
		# Keep track of existing tags
		tag_map = {}
		tag_counter = 0
		
		for _, row in df.iterrows():
			# Create album
			album = models.Album(
				id=f"a{_}",
				artist=row['Artist'],
				title=row['Album'],
				release_date=parse_date(row['Release Date']),
				length=row['Length'],
				vocal_style=row['Vocal Style'],
				country=row['Country / State'],
				genre=row['Genre / Subgenres']
			)
			
			# Create tags from genre/subgenres
			if pd.notna(row['Genre / Subgenres']):
				genres = [g.strip() for g in row['Genre / Subgenres'].split(',')]
				for genre in genres:
					if genre not in tag_map:
						tag = db.query(models.Tag).filter_by(name=genre).first()
						if not tag:
							tag_counter += 1
							tag = models.Tag(
								id=f"t{tag_counter}",
								name=genre,
								category='genre'
							)
							db.add(tag)
						tag_map[genre] = tag
					album.tags.append(tag_map[genre])
			
			db.add(album)
		
		db.commit()
		logger.info(f"Successfully loaded {len(df)} albums")
		
	except Exception as e:
		logger.error(f"Error loading CSV data: {str(e)}")
		db.rollback()
		raise