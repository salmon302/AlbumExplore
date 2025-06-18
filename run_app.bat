@echo off  
cd /d "C:\Users\salmo\Documents\GitHub\AlbumExplore"  
set PYTHONPATH=%C:\Users\salmo\Documents\GitHub\AlbumExplore%\Lib\site-packages;%C:\Users\salmo\Documents\GitHub\AlbumExplore%\src  
echo Setting PYTHONPATH to: %%PYTHONPATH%%  
echo Running AlbumExplore GUI application...  
python -m albumexplore.gui.app  
pause 
