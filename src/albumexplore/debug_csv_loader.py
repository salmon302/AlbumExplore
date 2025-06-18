"""
Debug app for AlbumExplore - uses enhanced CSV loader.
"""
import sys
import os
from pathlib import Path
import logging

# Add the project path to sys.path
project_root = Path(os.path.abspath(__file__)).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(project_root / "debug_csv_loader.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting CSV loader in debug mode")
    
    try:
        from albumexplore.database.csv_loader_debug import load_csv_data_with_debug
        from albumexplore.database import init_database
        
        # Initialize database
        logger.info("Initializing database")
        init_database()
        
        # Load CSV data with enhanced debugging
        csv_dir = project_root / "csv"
        logger.info(f"Loading CSV data from {csv_dir}")
        load_csv_data_with_debug(csv_dir)
        
        logger.info("CSV loading completed successfully")
        
    except Exception as e:
        logger.error(f"Error in CSV loader: {str(e)}", exc_info=True)
        sys.exit(1)
    
    logger.info("CSV loading debug script completed")
    sys.exit(0)
