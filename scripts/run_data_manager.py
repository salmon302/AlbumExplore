import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication

# Setup path
root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir / 'src'))

# Configure basic logging for the run
logging.basicConfig(level=logging.INFO)

from albumexplore.gui.data_loader_dialog import DataLoaderDialog

def main():
    app = QApplication(sys.argv)
    
    dialog = DataLoaderDialog()
    dialog.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
