import sys, os, uuid 
from datetime import datetime  
sys.path.insert(0, 'src')  
from albumexplore.database import get_session  
from albumexplore.database.models import Album 
