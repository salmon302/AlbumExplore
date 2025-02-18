from typing import List, Dict, Set, Optional
from sqlalchemy.orm import Session
from ...database import models
from ..analysis.tag_analyzer import TagAnalyzer

class TagFilter:
	def __init__(self, db: Session):
		self.db = db

	def filter_by_frequency(self, min_freq: int = 0, max_freq: Optional[int] = None) -> List[models.Tag]:
		"""Filter tags by their frequency of use."""
		query = self.db.query(models.Tag).filter(models.Tag.frequency >= min_freq)
		if max_freq is not None:
			query = query.filter(models.Tag.frequency <= max_freq)
		return query.all()

	def filter_by_category(self, category: str) -> List[models.Tag]:
		"""Filter tags by their category."""
		return self.db.query(models.Tag).filter(models.Tag.category == category).all()

	def filter_by_relationship(self, tag_id: str, min_strength: float = 0.0) -> List[models.TagRelation]:
		"""Filter tag relationships by strength."""
		return self.db.query(models.TagRelation).filter(
			((models.TagRelation.tag1_id == tag_id) | 
			 (models.TagRelation.tag2_id == tag_id)) &
			(models.TagRelation.strength >= min_strength)
		).all()

	def filter_albums_by_tags(self, tag_ids: List[str], match_all: bool = False) -> List[models.Album]:
		"""
		Filter albums by tags.
		If match_all is True, albums must have all specified tags.
		If match_all is False, albums must have any of the specified tags.
		"""
		query = self.db.query(models.Album).join(
			models.album_tags
		).join(
			models.Tag
		).filter(
			models.Tag.id.in_(tag_ids)
		)

		if match_all:
			# Count matching tags per album and filter for those matching all tags
			query = query.group_by(models.Album.id).having(
				models.db.func.count(models.Tag.id) == len(tag_ids)
			)

		return query.all()

	def filter_by_similarity(self, tag_id: str, threshold: float = 0.3) -> List[models.Tag]:
		"""Filter tags by similarity to a given tag."""
		# Get the tag relationships
		relationships = self.filter_by_relationship(tag_id)
		
		# Find tags with relationship strength above threshold
		similar_tag_ids = set()
		for rel in relationships:
			if rel.strength >= threshold:
				if rel.tag1_id == tag_id:
					similar_tag_ids.add(rel.tag2_id)
				else:
					similar_tag_ids.add(rel.tag1_id)
		
		return self.db.query(models.Tag).filter(
			models.Tag.id.in_(similar_tag_ids)
		).all()

	def filter_by_date_range(self, start_year: int, end_year: int) -> List[models.Album]:
		"""Filter albums by release year range."""
		return self.db.query(models.Album).filter(
			models.Album.release_year.between(start_year, end_year)
		).all()

	def filter_by_vocal_style(self, style: str) -> List[models.Album]:
		"""Filter albums by vocal style."""
		return self.db.query(models.Album).filter(
			models.Album.vocal_style == style
		).all()

	def filter_by_country(self, country: str) -> List[models.Album]:
		"""Filter albums by country."""
		return self.db.query(models.Album).filter(
			models.Album.country == country
		).all()

	def filter_by_multiple_criteria(self, criteria: Dict) -> List[models.Album]:
		"""Filter albums by multiple criteria simultaneously."""
		query = self.db.query(models.Album)
		
		if 'tags' in criteria:
			if criteria.get('match_all_tags', False):
				# For match_all, we need to ensure the album has all specified tags
				for tag_id in criteria['tags']:
					# Create a subquery for each tag
					tag_subquery = self.db.query(models.album_tags.c.album_id).filter(
						models.album_tags.c.tag_id == tag_id
					)
					query = query.filter(models.Album.id.in_(tag_subquery))
			else:
				# For match_any, we can use a single join
				query = query.join(models.album_tags).join(models.Tag).filter(
					models.Tag.id.in_(criteria['tags'])
				).distinct()
		
		if 'year_range' in criteria:
			start_year, end_year = criteria['year_range']
			query = query.filter(models.Album.release_year.between(start_year, end_year))
			
		if 'vocal_style' in criteria:
			query = query.filter(models.Album.vocal_style == criteria['vocal_style'])
			
		if 'country' in criteria:
			query = query.filter(models.Album.country == criteria['country'])
			
		return query.all()

	def filter_tags_by_pattern(self, pattern: str) -> List[models.Tag]:
		"""Filter tags by name pattern using SQL LIKE."""
		return self.db.query(models.Tag).filter(
			models.Tag.name.like(f"%{pattern}%")
		).all()

	def filter_by_tag_hierarchy(self, parent_tag_id: str) -> List[models.Tag]:
		"""Filter tags by their relationship hierarchy."""
		relationships = self.db.query(models.TagRelation).filter(
			(models.TagRelation.tag1_id == parent_tag_id) &
			(models.TagRelation.relationship_type == 'parent')
		).all()
		
		child_tag_ids = [rel.tag2_id for rel in relationships]
		return self.db.query(models.Tag).filter(
			models.Tag.id.in_(child_tag_ids)
		).all()

	def filter_by_platform(self, platform: str) -> List[models.Album]:
		"""Filter albums by platform availability."""
		return self.db.query(models.Album).filter(
			models.Album.platforms.like(f"%{platform}%")
		).all()