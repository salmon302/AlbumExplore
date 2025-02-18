CREATE TABLE IF NOT EXISTS albums (
	id TEXT PRIMARY KEY,
	artist TEXT NOT NULL,
	title TEXT NOT NULL,
	release_date DATETIME,
	release_year INTEGER,
	length TEXT,
	vocal_style TEXT,
	country TEXT,
	raw_tags TEXT,
	platforms TEXT
);

CREATE TABLE IF NOT EXISTS tags (
	id TEXT PRIMARY KEY,
	name TEXT UNIQUE NOT NULL,
	category TEXT,
	aliases TEXT,
	frequency INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tag_relationships (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	tag1_id TEXT NOT NULL,
	tag2_id TEXT NOT NULL,
	relationship_type TEXT NOT NULL,
	strength REAL,
	FOREIGN KEY (tag1_id) REFERENCES tags(id),
	FOREIGN KEY (tag2_id) REFERENCES tags(id)
);

CREATE TABLE IF NOT EXISTS album_tags (
	album_id TEXT NOT NULL,
	tag_id TEXT NOT NULL,
	FOREIGN KEY (album_id) REFERENCES albums(id),
	FOREIGN KEY (tag_id) REFERENCES tags(id),
	PRIMARY KEY (album_id, tag_id)
);

CREATE TABLE IF NOT EXISTS tag_hierarchy (
    parent_id TEXT NOT NULL,
    child_id TEXT NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES tags(id),
    FOREIGN KEY (child_id) REFERENCES tags(id),
    PRIMARY KEY (parent_id, child_id)
);

CREATE TABLE IF NOT EXISTS update_history (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
	entity_type TEXT NOT NULL,
	entity_id TEXT NOT NULL,
	change_type TEXT NOT NULL,
	changes TEXT
);

CREATE INDEX IF NOT EXISTS artist_idx ON albums (artist);
CREATE INDEX IF NOT EXISTS release_date_idx ON albums (release_date);
CREATE INDEX IF NOT EXISTS tag_name_idx ON tags (name);
CREATE INDEX IF NOT EXISTS tag_category_idx ON tags (category);