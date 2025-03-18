"""Script to analyze ProgArchives HTML structure."""
import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def analyze_page():
    """Analyze the HTML structure of a ProgArchives page."""
    url = "https://www.progarchives.com/bands-alpha.asp?letter=A&page=1"
    
    # Use headers that look like a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
    }
    
    # Fetch the page
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Log the overall structure
    logger.debug("=== Page Structure Analysis ===")
    
    # Look for main content area
    logger.debug("\n=== Main Content Areas ===")
    for div in soup.find_all('div', class_=['contentarea', 'content', 'main_content', 'content_main']):
        logger.debug(f"Found content div with class: {div.get('class')}")
    
    # Look for tables
    logger.debug("\n=== Tables ===")
    for idx, table in enumerate(soup.find_all('table')):
        logger.debug(f"\nTable {idx + 1}:")
        # Check headers
        headers = table.find_all(['th', 'td'], class_='header')
        if headers:
            logger.debug("Headers found:")
            for header in headers:
                logger.debug(f"- {header.get_text(strip=True)}")
        
        # Check first row
        first_row = table.find('tr')
        if first_row:
            cells = first_row.find_all('td')
            logger.debug(f"First row has {len(cells)} cells")
            if cells:
                logger.debug("First row cell contents:")
                for cell in cells:
                    logger.debug(f"- {cell.get_text(strip=True)}")
                    links = cell.find_all('a')
                    if links:
                        for link in links:
                            logger.debug(f"  Link: {link.get('href')} -> {link.get_text(strip=True)}")
    
    # Find all artist links
    logger.debug("\n=== Artist Links ===")
    artist_links = soup.find_all('a', href=lambda h: h and 'artist.asp?id=' in h)
    for link in artist_links[:5]:  # Show first 5 as sample
        logger.debug(f"Artist link: {link['href']} -> {link.get_text(strip=True)}")
        # Find parent row
        row = link.find_parent('tr')
        if row:
            cells = row.find_all('td')
            if len(cells) >= 3:
                logger.debug(f"- Genre: {cells[1].get_text(strip=True)}")
                logger.debug(f"- Country: {cells[2].get_text(strip=True)}")

if __name__ == "__main__":
    analyze_page()