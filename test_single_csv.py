"""Simple test to process just one CSV file."""
import sys
sys.path.insert(0, 'src')

from pathlib import Path

def test_single_csv():
    print("=== Single CSV File Test ===")
    
    try:
        from albumexplore.database import init_db, get_session
        from albumexplore.database.models import Album
        from albumexplore.database.csv_loader import _process_csv_file, extract_year
        
        # Initialize database
        init_db()
        
        # Get a CSV file to test
        csv_dir = Path('csv')
        csv_files = list(csv_dir.glob('*.csv'))
        
        if not csv_files:
            print("No CSV files found")
            return
        
        # Use the 2024 prog-metal file as it should be smaller
        test_file = None
        for f in csv_files:
            if '2024' in f.name and 'Prog-metal' in f.name:
                test_file = f
                break
        
        if not test_file:
            test_file = csv_files[0]
        
        print(f"Testing with: {test_file.name}")
        
        # Check existing albums
        session = get_session()
        before_count = session.query(Album).count()
        print(f"Albums before: {before_count}")
        
        # Extract year and process file
        year = extract_year(test_file.name)
        print(f"Extracted year: {year}")
        
        if year:
            print("Processing CSV file...")
            result = _process_csv_file(test_file, year, session)
            print(f"Processing completed: {result}")
            
            session.commit()
            
            after_count = session.query(Album).count()
            print(f"Albums after: {after_count}")
            print(f"New albums added: {after_count - before_count}")
              if after_count > before_count:
                print("\nSample new albums:")
                new_albums = session.query(Album).order_by(Album.id.desc()).limit(5).all()
                for album in new_albums:
                    is_caps = album.title.isupper() and album.pa_artist_name_on_album.isupper()
                    caps_indicator = " [ALL CAPS]" if is_caps else " [mixed case]"
                    print(f"  {album.pa_artist_name_on_album} - {album.title}{caps_indicator}")
        
        session.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_csv() 
