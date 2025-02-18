from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel

class AlbumBase(BaseModel):
	artist: str
	title: str
	release_date: Optional[datetime] = None
	release_year: Optional[int] = None
	length: Optional[str] = None
	vocal_style: Optional[str] = None
	country: Optional[str] = None
	raw_tags: List[str] = []
	platforms: Dict[str, str] = {}

class AlbumCreate(AlbumBase):
	id: str

class Album(AlbumBase):
	id: str
	tags: List['Tag'] = []

	class Config:
		orm_mode = True

class TagBase(BaseModel):
	name: str
	category: Optional[str] = None
	aliases: List[str] = []

class TagCreate(TagBase):
	id: str

class Tag(TagBase):
	id: str
	frequency: int = 0
	albums: List[Album] = []

	class Config:
		orm_mode = True

class TagRelationBase(BaseModel):
	tag1_id: str
	tag2_id: str
	relationship_type: str
	strength: float = 0.0

class TagRelationCreate(TagRelationBase):
	pass

class TagRelation(TagRelationBase):
	id: int

	class Config:
		orm_mode = True

class UpdateHistoryBase(BaseModel):
	entity_type: str
	entity_id: str
	change_type: str
	changes: Dict

class UpdateHistory(UpdateHistoryBase):
	id: int
	timestamp: datetime

	class Config:
		orm_mode = True

# Resolve forward references
Album.update_forward_refs()
Tag.update_forward_refs()