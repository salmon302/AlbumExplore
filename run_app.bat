@echo off
cd /d "%~dp0"
rem Set PYTHONPATH to the repo src directory so the albumexplore package is importable.
set "PYTHONPATH=%~dp0src"
echo Setting PYTHONPATH to: %PYTHONPATH%
echo Running AlbumExplore GUI application...
if exist ".venv-1\Scripts\python.exe" (
    ".venv-1\Scripts\python.exe" -m albumexplore.gui.app
) else (
    python -m albumexplore.gui.app
)
pause
