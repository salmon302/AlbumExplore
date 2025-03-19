"""ProgArchives.com scraper with ethical rate limiting."""
import logging
import re
import time
from typing import Dict, List, Iterator, Optional, Any
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup, Tag

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class ProgArchivesScraper(BaseScraper):
    """Scraper for ProgArchives.com that follows ethical guidelines."""
    
    BASE_URL = "https://www.progarchives.com"
    ALPHA_URL = f"{BASE_URL}/bands-alpha.asp"
    ARTIST_URL = f"{BASE_URL}/artist.asp"
    ALBUM_URL = f"{BASE_URL}/album.asp"
    ALBUM_REVIEWS_URL = f"{BASE_URL}/album-reviews.asp"
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_bands: Optional[int] = None,
        random_sample: bool = False
    ):
        """Initialize scraper with optional limits and sampling strategy."""
        super().__init__(
            cache_dir=cache_dir / "progarchives" if cache_dir else Path("cache/progarchives"),
            min_request_interval=5.0  # Ethical rate limiting
        )
        self.max_bands = max_bands
        self.random_sample = random_sample
        self._retry_count = 3  # Number of retries for failed requests

    def get_bands_all(self, use_cache: bool = True) -> Iterator[Dict[str, Any]]:
        """
        Get all bands from ProgArchives alphabetically.
        
        Args:
            use_cache: Whether to use cache or force a fresh request
            
        Returns:
            Iterator of band dictionaries with name, URL, and metadata
        """
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        band_count = 0
        
        for letter in letters:
            try:
                for band in self._get_bands_for_letter(letter, use_cache=use_cache):
                    yield band
                    band_count += 1
                    
                    if self.max_bands and band_count >= self.max_bands:
                        logger.info(f"Reached maximum band count limit ({self.max_bands})")
                        return
                        
            except Exception as e:
                logger.error(f"Error getting bands for letter {letter}: {e}")
    
    def _get_bands_for_letter(self, letter: str, use_cache: bool = True) -> Iterator[Dict[str, Any]]:
        """
        Get all bands starting with a specific letter.
        
        Args:
            letter: The letter to get bands for
            use_cache: Whether to use cache or force a fresh request
            
        Returns:
            Iterator of band dictionaries with name, URL, and metadata
        """
        url = f"{self.ALPHA_URL}?letter={letter}"
        
        try:
            # Fetch the page
            response = self.fetch_url(url, use_cache=use_cache)
            if not response or not response.get('content'):
                logger.warning(f"No content received from {url}")
                return
                
            # Parse the HTML
            soup = BeautifulSoup(response['content'], 'html.parser')
            
            # Find the grid container that contains the band listings
            grid_container = soup.select_one('div.grid-container')
            if not grid_container:
                logger.warning(f"Could not find grid container on {url}")
                return
                
            # Extract artist links
            artist_links = grid_container.select('a[href*="artist.asp"]')
            
            if not artist_links:
                logger.warning(f"No artist links found on {url}")
                return
                
            logger.info(f"Found {len(artist_links)} bands starting with letter '{letter}'")
            
            # Process each band entry
            for i, link in enumerate(artist_links):
                try:
                    band_url = link['href']
                    if not band_url.startswith('http'):
                        band_url = f"{self.BASE_URL}/{band_url.lstrip('/')}"
                        
                    # Get band ID from URL
                    band_id_match = re.search(r'id=(\d+)', band_url)
                    band_id = band_id_match.group(1) if band_id_match else None
                    
                    # Find genre and country information
                    # In the grid-container, each row has 3 cells:
                    # Artist | Genre | Country
                    parent = link.parent  # This is the artist cell
                    row_items = list(parent.parent.children)
                    
                    genre = None
                    country = None
                    
                    # Look for genre and country in sibling cells
                    if len(row_items) >= 3:
                        genre_cell = row_items[1]
                        country_cell = row_items[2]
                        
                        genre = self._extract_text(genre_cell)
                        country = self._extract_text(country_cell)
                    
                    band = {
                        'name': self._extract_text(link),
                        'url': band_url,
                        'id': band_id,
                    }
                    
                    if genre:
                        band['genre'] = genre
                    
                    if country:
                        band['country'] = country
                        
                    yield band
                    
                except Exception as e:
                    logger.warning(f"Error processing band {i} on letter {letter} page: {e}")
            
        except Exception as e:
            logger.error(f"Error getting bands for letter {letter}: {e}")
    
    def get_band_details(self, url_or_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get detailed information about a band/artist.
        
        Args:
            url_or_id: Either a full URL or just the artist ID from ProgArchives
            use_cache: Whether to use cache or force a fresh request
            
        Returns:
            Dictionary with band details including name, genre, country, discography, etc.
        """
        try:
            # Convert URL to ID if needed
            artist_id = self._extract_id(url_or_id)
            if not artist_id:
                raise ValueError(f"Invalid artist URL or ID: {url_or_id}")
                
            # Construct the URL if not already provided
            if url_or_id.isdigit():
                url = f"{self.ARTIST_URL}?id={artist_id}"
            else:
                url = url_or_id
                
            # Fetch the page content
            response = self.fetch_url(url, use_cache=use_cache)
            if not response or not response.get('content'):
                raise ValueError(f"No content received from {url}")
                
            # Parse the HTML
            soup = BeautifulSoup(response['content'], 'html.parser')
            
            # Extract artist information
            artist_info = self._parse_artist_info(soup, url)
            if not artist_info:
                raise ValueError(f"Could not find band info section for {url}")
                
            # Add metadata
            artist_info['url'] = url
            artist_info['id'] = artist_id
            artist_info['scraped_at'] = datetime.now().isoformat()
            
            # Get albums
            artist_info['albums'] = list(self._find_band_albums(soup))
            
            return artist_info
            
        except Exception as e:
            logger.error(f"Error getting band details from {url_or_id}: {e}")
            return {'error': str(e)}
    
    def get_album_data(self, url_or_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get detailed information about an album.
        
        Args:
            url_or_id: Either a full URL or just the album ID from ProgArchives
            use_cache: Whether to use cache or force a fresh request
            
        Returns:
            Dictionary with album details including title, artist, tracks, etc.
        """
        try:
            # Convert URL to ID if needed
            album_id = self._extract_id(url_or_id)
            if not album_id:
                raise ValueError(f"Invalid album URL or ID: {url_or_id}")
                
            # Construct the URL
            url = f"{self.ALBUM_URL}?id={album_id}"
            
            # Fetch the page content
            response = self.fetch_url(url, use_cache=use_cache)
            if not response or not response.get('content'):
                raise ValueError(f"No content received from {url}")
                
            # Parse the HTML
            soup = BeautifulSoup(response['content'], 'html.parser')
            
            # Extract album details
            album_info = self._parse_album_info(soup)
            if not album_info:
                raise ValueError(f"Could not parse album data from {url}")
                
            # Add metadata
            album_info['url'] = url
            album_info['id'] = album_id
            album_info['scraped_at'] = datetime.now().isoformat()
            
            # Get review summary/stats
            album_info['reviews'] = self._get_review_stats(soup)
            
            # Get tracklist
            album_info['tracks'] = self._extract_tracklist(soup)
            
            return album_info
            
        except Exception as e:
            logger.error(f"Error getting album data from {url_or_id}: {e}")
            return {'error': str(e)}
            
    def get_album_reviews(self, url_or_id: str, use_cache: bool = True, max_reviews: Optional[int] = None) -> Dict[str, Any]:
        """
        Get reviews for a specific album.
        
        Args:
            url_or_id: Either a full URL or just the album ID from ProgArchives
            use_cache: Whether to use cache or force a fresh request
            max_reviews: Maximum number of reviews to fetch (None for all)
            
        Returns:
            Dictionary with album reviews and review metadata
        """
        try:
            # Convert URL to ID if needed
            album_id = self._extract_id(url_or_id)
            if not album_id:
                raise ValueError(f"Invalid album URL or ID: {url_or_id}")
                
            # Construct the URL
            url = f"{self.ALBUM_REVIEWS_URL}?id={album_id}"
            
            # Fetch the page content
            response = self.fetch_url(url, use_cache=use_cache)
            if not response or not response.get('content'):
                raise ValueError(f"No content received from {url}")
                
            # Parse the HTML
            soup = BeautifulSoup(response['content'], 'html.parser')
            
            # Extract basic album info
            album_info = {
                'id': album_id,
                'url': url,
                'title': self._extract_album_title_from_reviews(soup),
                'artist': self._extract_artist_from_reviews(soup),
                'reviews': list(self._extract_reviews(soup, max_reviews)),
                'scraped_at': datetime.now().isoformat()
            }
            
            return album_info
            
        except Exception as e:
            logger.error(f"Error getting album reviews from {url_or_id}: {e}")
            return {'error': str(e)}
    
    def _extract_id(self, url_or_id: str) -> Optional[str]:
        """Extract ID from URL or return ID if already an ID string."""
        if url_or_id.isdigit():
            return url_or_id
            
        # Try to extract ID from URL
        match = re.search(r'[?&]id=(\d+)', url_or_id)
        if match:
            return match.group(1)
            
        return None
        
    def _parse_artist_info(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract artist information from artist page HTML."""
        artist_info = {}
        
        try:
            # Extract artist name from h1 element
            h1_element = soup.find('h1')
            if h1_element:
                artist_info['name'] = self._extract_text(h1_element)
            
            # Extract genre and country information
            genre_elem = soup.select_one('.genresubtitle')
            if genre_elem:
                artist_info['genre'] = self._extract_text(genre_elem)
                
            country_elem = soup.select_one('.countrysubtitle')
            if country_elem:
                artist_info['country'] = self._extract_text(country_elem)
            
            # Extract biography/description
            bio_element = soup.select_one('.artistdescription')
            if bio_element:
                artist_info['bio'] = self._extract_text(bio_element)
                
            # Check for required fields
            if 'name' not in artist_info:
                logger.warning(f"Could not find artist name for {url}")
                return {}
                
            return artist_info
            
        except Exception as e:
            logger.error(f"Error parsing artist info for {url}: {e}")
            return {}
    
    def _find_band_albums(self, soup: BeautifulSoup) -> Iterator[Dict[str, Any]]:
        """
        Extract albums from an artist page.
        
        Args:
            soup: BeautifulSoup object of the artist page
            
        Returns:
            Iterator of album dictionaries
        """
        try:
            # Find all album entries in the discography section
            album_entries = soup.select('.artist-discography-td')
            
            if not album_entries:
                logger.warning("No album entries found in artist discography")
                return
                
            for entry in album_entries:
                try:
                    album_info = {}
                    
                    # Extract album link and title
                    link = entry.select_one('a[href*="album.asp"]')
                    if link:
                        album_url = link['href']
                        if not album_url.startswith('http'):
                            album_url = f"{self.BASE_URL}/{album_url.lstrip('/')}"
                            
                        album_info['title'] = self._extract_text(link)
                        album_info['url'] = album_url
                        
                        # Extract album ID from URL
                        album_id_match = re.search(r'id=(\d+)', album_url)
                        if album_id_match:
                            album_info['id'] = album_id_match.group(1)
                    
                    # Look for additional information like year and type
                    album_details = self._extract_text(entry)
                    if album_details:
                        # Try to extract year from text
                        year_match = re.search(r'\b(19|20)\d{2}\b', album_details)
                        if year_match:
                            album_info['year'] = year_match.group(0)
                            
                        # Try to extract album type/format
                        type_match = re.search(r'\b(LP|EP|Single|Demo|Live|Compilation)\b', album_details, re.IGNORECASE)
                        if type_match:
                            album_info['type'] = type_match.group(0)
                    
                    # Only yield albums with at least a title and URL
                    if 'title' in album_info and 'url' in album_info:
                        yield album_info
                        
                except Exception as e:
                    logger.warning(f"Error processing album entry: {e}")
                    
        except Exception as e:
            logger.error(f"Error finding band albums: {e}")
        
    def _parse_album_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract album information from album page HTML."""
        album_info = {}
        
        try:
            # Extract album title from h1 element - direct approach first
            h1_elements = soup.find_all('h1')
            if h1_elements and len(h1_elements) > 0:
                album_info['title'] = self._extract_text(h1_elements[0])
                
            # Extract artist from h2 element that links to the artist page
            artist_link = soup.select_one('h2 a[href*="artist.asp"]')
            if artist_link:
                album_info['artist'] = self._extract_text(artist_link)
                artist_url = artist_link['href']
                if not artist_url.startswith('http'):
                    artist_url = f"{self.BASE_URL}/{artist_url.lstrip('/')}"
                album_info['artist_url'] = artist_url
                
                # Extract artist ID
                artist_id_match = re.search(r'id=(\d+)', artist_url)
                if artist_id_match:
                    album_info['artist_id'] = artist_id_match.group(1)
            
            # Extract genre from h2 element that shows genre
            genre_h2 = soup.select('h2')
            for h2 in genre_h2:
                if not h2.select_one('a'):  # Only take the h2 without a link (the genre one)
                    genre_text = self._extract_text(h2)
                    if genre_text:
                        album_info['genre'] = genre_text
                        break
            
            # Extract album cover image
            cover_img = soup.select_one('#imgCover')
            if cover_img and cover_img.get('src'):
                img_url = cover_img['src']
                if not img_url.startswith('http'):
                    img_url = f"{self.BASE_URL}/{img_url.lstrip('/')}"
                album_info['cover_image'] = img_url
            
            # Extract release information - look for "Releases information" label
            release_info = None
            for strong_tag in soup.find_all('strong'):
                if 'Releases information' in self._extract_text(strong_tag):
                    release_info = strong_tag.find_next('p')
                    break
                    
            if release_info:
                album_info['release_info'] = self._extract_text(release_info)
                
                # Try to extract year from release info
                year_match = re.search(r'\b(19|20)\d{2}\b', self._extract_text(release_info))
                if year_match:
                    album_info['year'] = year_match.group(0)
            
            # Extract track listing - look for "Songs / Tracks Listing" label
            tracks = []
            tracklist_p = None
            for strong_tag in soup.find_all('strong'):
                if 'Songs / Tracks Listing' in self._extract_text(strong_tag):
                    tracklist_p = strong_tag.find_next('p')
                    break
                    
            if tracklist_p:
                album_info['tracklist_raw'] = self._extract_text(tracklist_p)
                
            # Extract lineup/musicians - look for "Line-up / Musicians" label
            musicians = []
            lineup_p = None
            for strong_tag in soup.find_all('strong'):
                if 'Line-up / Musicians' in self._extract_text(strong_tag):
                    lineup_p = strong_tag.find_next('p')
                    break
                    
            if lineup_p:
                album_info['musicians_raw'] = self._extract_text(lineup_p)
                
            # Extract album type from "Studio Album", "Live Album", etc.
            album_type = None
            for strong_tag in soup.find_all('strong'):
                text = self._extract_text(strong_tag)
                if 'Album, released in' in text or 'Album released in' in text:
                    album_type_match = re.match(r'([^,]+),?\s+released in', text)
                    if album_type_match:
                        album_info['type'] = album_type_match.group(1).strip()
                    # Try to extract year from this text as well
                    year_match = re.search(r'released in (\d{4})', text)
                    if year_match:
                        album_info['year'] = year_match.group(1)
                    break
            
            # Make sure we have the minimum required fields
            required_fields = ['title', 'artist']
            missing_fields = [f for f in required_fields if f not in album_info]
            if missing_fields:
                logger.warning(f"Missing required album fields: {', '.join(missing_fields)}")
                
                # Try alternative methods for getting title if h1 approach failed
                if 'title' not in album_info:
                    # Try to extract from meta tags
                    title_meta = soup.select_one('meta[property="og:title"]')
                    if title_meta and title_meta.get('content'):
                        title_content = title_meta.get('content')
                        title_match = re.match(r'(.+?)\s*-\s*(.+?)\s*\(', title_content)
                        if title_match:
                            album_info['artist'] = title_match.group(1).strip()
                            album_info['title'] = title_match.group(2).strip()
                
                # If still missing required fields, return empty dict
                missing_fields = [f for f in required_fields if f not in album_info]
                if missing_fields:
                    return {}
                
            return album_info
            
        except Exception as e:
            logger.error(f"Error parsing album info: {e}")
            return {}
    
    def _get_review_stats(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract review statistics from album page."""
        stats = {
            'avg_rating': None,
            'num_ratings': 0,
            'num_reviews': 0
        }
        
        try:
            # Look for average rating span
            avg_rating_span = soup.select_one('span[id^="avgRatings_"]')
            if avg_rating_span and avg_rating_span.get_text():
                try:
                    stats['avg_rating'] = float(avg_rating_span.get_text())
                except (ValueError, TypeError):
                    pass
                    
            # Look for number of ratings span
            num_ratings_span = soup.select_one('span[id^="nbRatings_"]')
            if num_ratings_span and num_ratings_span.get_text():
                try:
                    stats['num_ratings'] = int(num_ratings_span.get_text())
                except (ValueError, TypeError):
                    pass
                    
            # Look for number of reviews info
            review_stats = soup.select_one('.ratings_count') or soup.select_one('a[href="#reviews"]')
            if review_stats:
                text = self._extract_text(review_stats)
                if text:
                    reviews_match = re.search(r'(\d+)\s+reviews', text)
                    if reviews_match:
                        try:
                            stats['num_reviews'] = int(reviews_match.group(1))
                        except (ValueError, TypeError):
                            pass
            
            return stats
            
        except Exception as e:
            logger.error(f"Error extracting review stats: {e}")
            return stats
    
    def _extract_tracklist(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract album tracklist."""
        tracks = []
        
        try:
            # Look for the tracklist paragraph after "Songs / Tracks Listing" heading
            tracklist_p = None
            for strong_tag in soup.find_all('strong'):
                if 'Songs / Tracks Listing' in self._extract_text(strong_tag):
                    tracklist_p = strong_tag.find_next('p')
                    break
                    
            if not tracklist_p:
                return tracks
                
            # Get text content
            tracklist_text = self._extract_text(tracklist_p)
            if not tracklist_text:
                return tracks
                
            # Split into lines by <br> tags or by numbered tracks
            # For the HTML version, we need to split by <br> tags
            track_lines = []
            for line in tracklist_p.get_text(separator='||').split('||'):
                line = line.strip()
                if line:
                    track_lines.append(line)
            
            # If no <br> tags found, try to split the text by numbers with a period
            if len(track_lines) <= 1:
                for line in re.split(r'\s*\d+\.\s+', tracklist_text):
                    line = line.strip()
                    if line and not line.startswith('Total Time'):
                        track_lines.append(line)
            
            # Process each track
            for i, line in enumerate(track_lines):
                # Skip total time line
                if 'Total Time' in line:
                    continue
                    
                # Try to extract track number, title, and duration
                track_info = {}
                
                # If line starts with a number, it's probably a track number
                num_match = re.match(r'(\d+)\.\s*(.*)', line)
                if num_match:
                    track_info['number'] = int(num_match.group(1))
                    line = num_match.group(2).strip()
                else:
                    # Default to track position in list + 1
                    track_info['number'] = i + 1
                
                # Try to extract duration in parentheses from the end
                duration_match = re.search(r'\((\d+:\d+)\)$', line)
                if duration_match:
                    track_info['duration'] = duration_match.group(1)
                    line = re.sub(r'\(\d+:\d+\)$', '', line).strip()
                
                # What remains should be the track title
                track_info['title'] = line
                
                # Only add tracks with at least a title
                if track_info['title']:
                    tracks.append(track_info)
            
            return tracks
            
        except Exception as e:
            logger.error(f"Error extracting tracklist: {e}")
            return tracks
    
    def _extract_album_title_from_reviews(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract album title from reviews page."""
        # First approach: h1 element
        h1_elements = soup.find_all('h1')
        if h1_elements and len(h1_elements) > 0:
            return self._extract_text(h1_elements[0])
            
        # Second approach: meta title
        title_meta = soup.select_one('meta[property="og:title"]')
        if title_meta and title_meta.get('content'):
            title_content = title_meta.get('content')
            title_match = re.match(r'(.+?)\s*-\s*(.+?)\s*\(', title_content)
            if title_match:
                return title_match.group(2).strip()
        
        return None
    
    def _extract_artist_from_reviews(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract artist name from reviews page."""
        # First approach: h2 with link to artist page
        artist_link = soup.select_one('h2 a[href*="artist.asp"]')
        if artist_link:
            return self._extract_text(artist_link)
            
        # Second approach: meta title
        title_meta = soup.select_one('meta[property="og:title"]')
        if title_meta and title_meta.get('content'):
            title_content = title_meta.get('content')
            title_match = re.match(r'(.+?)\s*-\s*(.+?)\s*\(', title_content)
            if title_match:
                return title_match.group(1).strip()
                
        return None
    
    def _extract_reviews(self, soup: BeautifulSoup, max_reviews: Optional[int] = None) -> Iterator[Dict[str, Any]]:
        """Extract individual reviews from reviews page."""
        review_count = 0
        # First try with common review class
        review_items = soup.select('.reviewtext, .review-box')
        
        if not review_items:
            # Try alternative approach looking for reviews section
            reviews_section = None
            for h2_tag in soup.find_all('h2'):
                if 'reviews' in self._extract_text(h2_tag).lower():
                    reviews_section = h2_tag.find_next('div')
                    if reviews_section:
                        review_items = reviews_section.select('div[class*="review"]')
                        
        for review in review_items:
            try:
                if max_reviews and review_count >= max_reviews:
                    break
                    
                review_info = {}
                
                # Extract reviewer name
                username_elem = review.select_one('.username, .user, .author')
                if username_elem:
                    review_info['author'] = self._extract_text(username_elem)
                
                # Extract review date
                date_elem = review.select_one('.reviewdate, .date')
                if date_elem:
                    review_info['date'] = self._extract_text(date_elem)
                
                # Extract rating
                rating_elem = review.select_one('.reviewrating, .rating')
                if rating_elem:
                    rating_text = self._extract_text(rating_elem)
                    if rating_text:
                        # Try to extract numeric rating
                        match = re.search(r'([\d.]+)', rating_text)
                        if match:
                            try:
                                review_info['rating'] = float(match.group(1))
                            except ValueError:
                                pass
                
                # Extract review text
                text_elem = review.select_one('.reviewcomment, .content, .text')
                if text_elem:
                    review_info['text'] = self._extract_text(text_elem)
                
                # Only yield reviews with text or at least a rating
                if 'text' in review_info or 'rating' in review_info:
                    yield review_info
                    review_count += 1
                    
            except Exception as e:
                logger.warning(f"Error parsing review: {e}")
    
    def _extract_text(self, element: Optional[Tag]) -> Optional[str]:
        """Helper method to safely extract and clean text from a BS4 element."""
        if not element:
            return None
            
        text = element.get_text(strip=True)
        if not text:
            return None
            
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _extract_year(self, element: Tag) -> Optional[str]:
        """Extract year from an element containing year information."""
        if not element:
            return None
            
        text = self._extract_text(element)
        if not text:
            return None
            
        # Try to find a year in the text
        year_match = re.search(r'\b(19|20)\d{2}\b', text)
        if year_match:
            return year_match.group(0)
            
        return None