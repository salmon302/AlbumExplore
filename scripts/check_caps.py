from albumexplore.database import session_scope, models
from sqlalchemy import func

def check_caps():
    with session_scope() as session:
        # Find albums where artist name is all upper case and length > 3 (to avoid acronyms like YES or RUSH potentially being valid)
        # SQLite GLOB '[A-Z]*' might not be enough, let's just fetch and check in python for simplicity
        
        # Checking distinct artist names
        names = session.query(models.Album.pa_artist_name_on_album).distinct().all()
        names = [n[0] for n in names if n[0]]
        
        all_caps = [n for n in names if n.isupper() and len(n) > 2]
        
        print(f"Total distinct artists: {len(names)}")
        print(f"Potential ALL CAPS artists: {len(all_caps)}")
        if all_caps:
            print("Samples:", all_caps[:20])

if __name__ == "__main__":
    check_caps()
