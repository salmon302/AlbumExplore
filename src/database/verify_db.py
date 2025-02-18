import sqlite3

def verify_tables():
	"""Verify database tables and their structure."""
	conn = sqlite3.connect('albumexplore.db')
	cursor = conn.cursor()
	
	# Get list of tables
	cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
	tables = cursor.fetchall()
	
	print("Database tables:")
	for table in tables:
		print(f"- {table[0]}")
		cursor.execute(f"PRAGMA table_info({table[0]});")
		columns = cursor.fetchall()
		for col in columns:
			print(f"  * {col[1]} ({col[2]})")
	
	conn.close()

if __name__ == "__main__":
	verify_tables()