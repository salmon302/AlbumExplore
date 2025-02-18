import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from . import models

logger = logging.getLogger(__name__)

def load_test_data(db: Session):
	"""Load test data into the database."""
	try:
		# Check if we already have data
		existing_albums = db.query(models.Album).count()
		if existing_albums > 0:
			logger.info("Test data already exists")
			return
			
		logger.info("Loading test data...")
		
		# Create tags with more variety
		tags = {
			'rock': models.Tag(id='t1', name='rock', category='genre'),
			'metal': models.Tag(id='t2', name='metal', category='genre'),
			'jazz': models.Tag(id='t3', name='jazz', category='genre'),
			'prog': models.Tag(id='t4', name='progressive', category='style'),
			'instrumental': models.Tag(id='t5', name='instrumental', category='style'),
			'fusion': models.Tag(id='t6', name='fusion', category='style'),
			'electronic': models.Tag(id='t7', name='electronic', category='genre'),
			'experimental': models.Tag(id='t8', name='experimental', category='style')
		}
		
		# Add tags
		for tag in tags.values():
			try:
				db.add(tag)
			except IntegrityError:
				db.rollback()
				continue
		db.flush()
		
		# Create albums with more complex relationships
		albums = [
			models.Album(
				id='a1',
				artist='Pink Floyd',
				title='Dark Side of the Moon',
				release_year=1973,
				length='LP',
				genre='Progressive Rock',
				tags=[tags['rock'], tags['prog'], tags['experimental']]
			),
			models.Album(
				id='a2',
				artist='Miles Davis',
				title='Kind of Blue',
				release_year=1959,
				length='LP',
				genre='Jazz',
				tags=[tags['jazz'], tags['instrumental']]
			),
			models.Album(
				id='a3',
				artist='Metallica',
				title='Master of Puppets',
				release_year=1986,
				length='LP',
				genre='Thrash Metal',
				tags=[tags['metal'], tags['rock']]
			),
			models.Album(
				id='a4',
				artist='King Crimson',
				title='Red',
				release_year=1974,
				length='LP',
				genre='Progressive Rock',
				tags=[tags['rock'], tags['prog'], tags['experimental']]
			),
			models.Album(
				id='a5',
				artist='Weather Report',
				title='Heavy Weather',
				release_year=1977,
				length='LP',
				genre='Jazz Fusion',
				tags=[tags['jazz'], tags['fusion'], tags['instrumental']]
			),
			models.Album(
				id='a6',
				artist='Tangerine Dream',
				title='Phaedra',
				release_year=1974,
				length='LP',
				genre='Electronic',
				tags=[tags['electronic'], tags['experimental'], tags['instrumental']]
			)
		]
		
		# Add albums
		for album in albums:
			try:
				db.add(album)
			except IntegrityError:
				db.rollback()
				continue
		db.flush()
		
		# Create more meaningful relationships
		relationships = [
			models.TagRelation(tag1_id='t1', tag2_id='t2', relationship_type='related', strength=0.7),
			models.TagRelation(tag1_id='t3', tag2_id='t6', relationship_type='related', strength=0.9),
			models.TagRelation(tag1_id='t4', tag2_id='t8', relationship_type='related', strength=0.6),
			models.TagRelation(tag1_id='t7', tag2_id='t8', relationship_type='related', strength=0.5),
			models.TagRelation(tag1_id='t1', tag2_id='t4', relationship_type='related', strength=0.8)
		]
		
		# Add relationships
		for rel in relationships:
			try:
				db.add(rel)
			except IntegrityError:
				db.rollback()
				continue
		
		# Commit all changes
		db.commit()
		logger.info("Test data loaded successfully")
		
	except Exception as e:
		logger.error(f"Error loading test data: {str(e)}")
		db.rollback()
		raise