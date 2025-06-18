"""
Modified version of AlbumExplore application that adds more logging to CSV loading.
"""
import os
import sys
from pathlib import Path
import logging
from datetime import datetime

# Configure logging to a file for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csv_load_debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('csv_loader_debug')

def main():
    logger.info("Starting AlbumExplore with enhanced CSV logging")
    
    # Import the application modules
    try:
        from albumexplore.gui import app
        logger.info("Imported albumexplore.gui.app")
        
        # Monkey patch the CSV loader
        from albumexplore.database import csv_loader
        original_load_csv_data = csv_loader.load_csv_data
        
        def enhanced_load_csv_data(csv_dir):
            start_time = datetime.now()
            logger.info(f"Enhanced CSV loader started at {start_time}")
            
            try:
                result = original_load_csv_data(csv_dir)
                end_time = datetime.now()
                processing_time = end_time - start_time
                logger.info(f"Enhanced CSV loader completed in {processing_time.total_seconds():.2f} seconds")
                return result
            except Exception as e:
                logger.error(f"Error in enhanced CSV loader: {str(e)}", exc_info=True)
                raise
        
        # Replace the original function
        csv_loader.load_csv_data = enhanced_load_csv_data
        logger.info("Enhanced CSV loader installed")
        
        # Run the application
        logger.info("Starting the application")
        app.main()
        
    except Exception as e:
        logger.error(f"Error in application: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
