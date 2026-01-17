from albumexplore.database import session_scope, models

def inspect_data():
    with session_scope() as session:
        albums = session.query(models.Album).limit(10).all()
        print(f"Found {session.query(models.Album).count()} albums.")
        
        if albums:
            print("\nSample Albums:")
            for a in albums:
                print(f" - Title: {a.title}")
                print(f"   PA Artist: {a.pa_artist_name_on_album}")
                if a.artist_obj:
                    print(f"   Linked Artist: {a.artist_obj.name}")
                else:
                    print(f"   Linked Artist: None")

if __name__ == "__main__":
    inspect_data()
