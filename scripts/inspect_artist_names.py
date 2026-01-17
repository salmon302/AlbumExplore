from albumexplore.database import session_scope, models

def inspect_artists():
    with session_scope() as session:
        artists = session.query(models.Artist).limit(20).all()
        print(f"Found {len(artists)} artists. First 20 names:")
        for a in artists:
            print(f" - {a.name}")

if __name__ == "__main__":
    inspect_artists()
