import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from . import models
from . import Base
from pathlib import Path

logger = logging.getLogger(__name__)

def init_db(database_url: str = "sqlite:///./albumexplore.db"):
	"""Initialize the database, creating tables from schema.sql."""
	try:
		engine = create_engine(database_url, connect_args={"check_same_thread": False})
		
		# Create tables from schema.sql
		schema_path = Path(__file__).parent / 'schema.sql'
		with open(schema_path, 'r') as f:
			schema = f.read()
			
		# Split and execute statements separately
		statements = [stmt.strip() for stmt in schema.split(';') if stmt.strip()]
		with engine.connect() as conn:
			for statement in statements:
				if statement:
					conn.execute(text(statement))
			conn.commit()
		
		Base.metadata.create_all(bind=engine)  # Ensure all tables are created
		logger.info("Database initialized successfully.")
		
		return engine
	except Exception as e:
		logger.error(f"Error initializing database: {str(e)}")
		raise

def verify_db_structure(engine):
	"""Verify that all required tables and indexes exist"""
	try:
		with engine.connect() as conn:
			# Check tables
			tables = conn.execute(text(
				"SELECT name FROM sqlite_master WHERE type='table'"
			)).fetchall()
			table_names = {table[0] for table in tables}
			
			required_tables = {
				'albums', 'tags', 'tag_relationships', 
				'album_tags', 'tag_hierarchy', 'update_history'
			}
			
			if not required_tables.issubset(table_names):
				missing = required_tables - table_names
				logger.error(f"Missing tables: {missing}")
				return False

			# Check indexes
			indexes = conn.execute(text(
				"SELECT name FROM sqlite_master WHERE type='index'"
			)).fetchall()
			index_names = {idx[0] for idx in indexes}
			
			required_indexes = {
				'artist_idx', 'release_date_idx',
				'tag_name_idx', 'tag_category_idx'
			}
			
			if not required_indexes.issubset(index_names):
				missing = required_indexes - index_names
				logger.error(f"Missing indexes: {missing}")
				return False
				
			return True
	except Exception as e:
		logger.error(f"Error verifying database structure: {str(e)}")
		return False

if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO)
	engine = init_db()
	if verify_db_structure(engine):
		logger.info("Database structure verified successfully")
	else:
		logger.error("Database structure verification failed")
