"""Debug script to test CSV loading specifically."""
import sys
sys.path.insert(0, 'src')

from pathlib import Path

def main():
    print("=== CSV Loading Debug Test ===")
    
    try:
        from albumexplore.database import get_session
        from albumexplore.database.models import Album
        
        # Check current album count and sample data
        session = get_session()
        before_count = session.query(Album).count()
        print(f'Albums before CSV loading: {before_count}')        # Show sample albums to see the capitalization pattern
        sample_albums = session.query(Album).limit(5).all()
        print('\nSample existing albums (checking for ALL CAPS pattern):')
        for album in sample_albums:
            print(f'  {album.pa_artist_name_on_album} - {album.title} ({album.release_year})')

        # Test CSV loading
        csv_dir = Path('csv')
        print(f'\nCSV directory exists: {csv_dir.exists()}')
        print(f'CSV directory path: {csv_dir.resolve()}')
        
        if csv_dir.exists():
            csv_files = list(csv_dir.glob('*.csv'))
            print(f'Found {len(csv_files)} CSV files')
            print('First 3 CSV files:', [f.name for f in csv_files[:3]])
            
            if csv_files:
                print('\n=== Testing single CSV file processing ===')
                
                from albumexplore.database.csv_loader import extract_year
                
                # Test with one file
                test_file = csv_files[0]
                print(f'Testing with: {test_file.name}')
                
                year = extract_year(test_file.name)
                print(f'Extracted year: {year}')
                
                if year:
                    # Read first few lines to see structure
                    print('\nFirst 15 lines of CSV file:')
                    with open(test_file, 'r', encoding='utf-8') as f:
                        for i, line in enumerate(f):
                            if i >= 15:
                                break
                            print(f'  {i+1:2d}: {line.strip()[:100]}')
                else:
                    print('Could not extract year from filename')
            else:
                print('No CSV files found')
        else:
            print('CSV directory does not exist')
            
        session.close()
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

    print("\n=== Test completed ===")

if __name__ == "__main__":
    main() 
