from abc import ABC, abstractmethod
import pandas as pd

class BaseParser(ABC):
    """Base class for data parsers."""
    
    def __init__(self):
        """Initialize the parser."""
        self._data = None
    
    @property
    def data(self) -> pd.DataFrame:
        """Return the parsed data, parsing if not already done."""
        if self._data is None:
            self._data = self.parse()
        return self._data
    
    @abstractmethod
    def parse(self) -> pd.DataFrame:
        """Parse the data source and return a DataFrame.
        
        Must be implemented by child classes.
        """
        pass