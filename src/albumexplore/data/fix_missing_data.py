import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Optional
from .validators.data_validator import DataValidator

logger = logging.getLogger(__name__)

class DataFixer:
	"""Fixes missing data in album CSV files."""
	
	GENRE_MAPPINGS = {
		'Deftones': 'Alt-metal, Prog-metal',
		'Korn': 'Alt-metal, Nu metal',
		'dredg': 'Prog-rock, Alt-rock',
		'The Tea Party': 'Prog-rock, World music',
		'Tori Amos': 'Art rock, Alternative',
		'IQ': 'Prog-rock, Symphonic',
		'BAND-MAID': 'Prog-rock, Hard rock',
		'Insomnium': 'Melodic Death metal, Prog-metal',
		'Be\'lakor': 'Melodic Death metal, Prog-metal',
		'Textures': 'Prog-metal, Djent',
		'Trivium': 'Metalcore, Prog-metal',
		'X JAPAN': 'Prog-metal, Power metal',
	}
	
	def __init__(self, csv_dir: Path):
		self.csv_dir = csv_dir
		self.current_year = datetime.now().year
	
	def fix_data(self) -> None:
		"""Fix missing data in all CSV files."""
		for file_path in self.csv_dir.glob('*.csv'):
			self._fix_file(file_path)
	
	def _fix_file(self, file_path: Path) -> None:
		"""Fix missing data in a single file."""
		try:
			# Read file and find header row
			with open(file_path, 'r', encoding='utf-8') as f:
				lines = f.readlines()
			
			header_row = -1
			for i, line in enumerate(lines):
				if all(col in line for col in ['Artist', 'Album', 'Release Date', 'Length']):
					header_row = i
					break
			
			if header_row == -1:
				logger.error(f"No header found in {file_path}")
				return
			
			# Create temporary file with only data from header row
			temp_file = file_path.parent / f"temp_{file_path.name}"
			try:
				with open(temp_file, 'w', encoding='utf-8') as f:
					f.writelines(lines[header_row:])
				
				# Read and process data
				df = pd.read_csv(temp_file)
				df = self._process_dataframe(df, file_path)
				
				# Write back to original file
				with open(file_path, 'w', encoding='utf-8') as f:
					# Write header comments
					f.writelines(lines[:header_row])
					# Write fixed data
					df.to_csv(f, index=False)
				
				logger.info(f"Fixed data in {file_path}")
				
			finally:
				if temp_file.exists():
					temp_file.unlink()
					
		except Exception as e:
			logger.error(f"Error fixing {file_path}: {str(e)}")
	
	def _process_dataframe(self, df: pd.DataFrame, file_path: Path) -> pd.DataFrame:
		"""Process and fix missing data in a dataframe."""
		# Get year from filename
		year_str = [part for part in file_path.stem.split('-') if part.strip().isdigit()]
		file_year = int(year_str[0]) if year_str else self.current_year
		
		# Fix missing data
		for idx, row in df.iterrows():
			# Fix missing album titles for future releases
			if pd.isna(row['Album']) or str(row['Album']).strip() == '':
				if file_year > self.current_year:
					df.at[idx, 'Album'] = 'TBA'
			
			# Fix missing release dates
			if pd.isna(row['Release Date']) or str(row['Release Date']).strip() == '':
				if file_year > self.current_year:
					df.at[idx, 'Release Date'] = f"{file_year}-TBA"
				else:
					df.at[idx, 'Release Date'] = f"{file_year}-01-01"
			
			# Fix missing genres for known artists
			if pd.isna(row['Genre / Subgenres']) or str(row['Genre / Subgenres']).strip() == '':
				if row['Artist'] in self.GENRE_MAPPINGS:
					df.at[idx, 'Genre / Subgenres'] = self.GENRE_MAPPINGS[row['Artist']]
			
			# Fix missing vocal styles based on genre
			if pd.isna(row['Vocal Style']) or str(row['Vocal Style']).strip() == '':
				genre = str(row['Genre / Subgenres']).lower()
				if any(x in genre for x in ['death metal', 'black metal', 'deathcore']):
					df.at[idx, 'Vocal Style'] = 'Harsh'
				elif any(x in genre for x in ['prog-rock', 'symphonic', 'power metal']):
					df.at[idx, 'Vocal Style'] = 'Clean'
				elif any(x in genre for x in ['prog-metal', 'metalcore']):
					df.at[idx, 'Vocal Style'] = 'Mixed'
				elif 'instrumental' in genre:
					df.at[idx, 'Vocal Style'] = 'Instrumental'
		
		return df

def main():
	csv_dir = Path("/home/seth-n/PycharmProjects/AlbumExplore/csv")
	fixer = DataFixer(csv_dir)
	fixer.fix_data()

if __name__ == "__main__":
	main()