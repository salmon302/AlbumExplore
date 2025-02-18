#!/bin/bash

# Activate virtual environment
source /home/seth-n/PycharmProjects/AlbumExplore/.venv/bin/activate || { echo "Error: Failed to activate virtual environment"; exit 1; }

# Install PyQt6 if not already installed
/home/seth-n/PycharmProjects/AlbumExplore/.venv/bin/pip install PyQt6 || { echo "Error: Failed to install PyQt6"; exit 1; }

# Set PYTHONPATH
export PYTHONPATH="/home/seth-n/PycharmProjects/AlbumExplore/src:/home/seth-n/PycharmProjects/AlbumExplore/src/gui"

# Run the GUI application
python /home/seth-n/PycharmProjects/AlbumExplore/src/gui/app.py || { echo "Error: GUI application failed to launch"; exit 1; }

echo "GUI application launched successfully"