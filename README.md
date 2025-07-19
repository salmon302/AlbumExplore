# AlbumExplore

A tool for exploring and analyzing music album collections with advanced tag management capabilities.

## Features

- Advanced tag analysis and normalization
- Smart tag variant detection and consolidation
- Hierarchical tag relationships
- Pattern-based tag similarity detection
- Single-instance tag handling
- Tag co-occurrence analysis
- GUI interface for collection management

## Installation

```bash
# Install for development
pip install -e .[dev,test]

# Install for regular use
pip install .
```

## Usage

```python
from albumexplore import run

# Launch the GUI application
run()

#tmp command for dev use
#  set PYTHONPATH=C:\Users\salmo\Documents\GitHub\AlbumExplore\src && C:\Users\salmo\Documents\GitHub\AlbumExplore\.venv-1\Scripts\python.exe -m albumexplore.gui.app
```

## Development

```bash
# Run tests
pytest tests/

# Format code
black src/ tests/
```

## Requirements

- Python 3.8+
- Required packages listed in setup.py
- Development dependencies available through [dev] and [test] extras