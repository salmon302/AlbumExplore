"""ProgArchives.com scraper for local HTML files."""
import logging
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
from bs4 import BeautifulSoup, NavigableString, Tag

logger = logging.getLogger(__name__)

class ProgArchivesScraper:
    """Parser for local ProgArchives.com HTML files."""
    
    # Constants for file paths
    LOCAL_DATA_ROOT = Path("data/progarchives")
    
    def __init__(
        self,
        local_data_root: Optional[Path] = None, # Made local_data_root optional again
        cache_dir: Optional[Path] = None # Made cache_dir optional again
    ):
        """Initialize scraper with path to local ProgArchives.com HTML files."""
        self.local_data_root = local_data_root if local_data_root else self.LOCAL_DATA_ROOT
        self.local_data_root.mkdir(parents=True, exist_ok=True)
        
        # Keep a simplified cache for parsed results
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cache/progarchives")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Regex for matching album links (e.g., albumXXXX.html or albumXXXX.html?id=YYYY)
        # Allows for alphanumeric characters, dots, and hyphens in the album identifier part.
        self.album_link_pattern = re.compile(r"album[a-zA-Z0-9.-]+\.html(?:\?id=\d+)?$")
        self.year_pattern = re.compile(r"(?:\b|\()((?:19|20)\d{2})(?:\b|\))") # (YYYY) or YYYY
        self.rating_pattern = re.compile(r"\b(\d\.\d{2})\b") # X.YY
        
        # To store the path of the current artist file being processed, useful for _resolve_relative_path
        self.current_artist_file_path: Optional[Path] = None

    def _normalize_album_type(self, header_text: str, artist_name: Optional[str]) -> str:
        """Normalize album type from discography section header."""
        logger.debug(f"_normalize_album_type: Original header_text='{header_text}', artist_name='{artist_name}'")
        lower_header = header_text.lower()

        if artist_name and artist_name.lower() in lower_header:
            escaped_artist_name = re.escape(artist_name.lower())
            lower_header = re.sub(escaped_artist_name, '', lower_header, flags=re.IGNORECASE).strip()
            logger.debug(f"_normalize_album_type: After artist removal, lower_header='{lower_header}'")

        # Simplified regex to remove any parenthetical suffix at the end.
        # Using proper raw string syntax
        lower_header = re.sub(r'\s*\([^)]+\)\s*$', '', lower_header).strip()
        logger.debug(f"_normalize_album_type: After general suffix removal, lower_header='{lower_header}'")
        
        # Remove counts like (16) if not caught by the general suffix removal
        # Using proper raw string syntax
        lower_header = re.sub(r'\s*\(\d+\)\s*$', '', lower_header).strip()
        logger.debug(f"_normalize_album_type: After count removal, lower_header='{lower_header}'")

        # Specific keyword checks (order can be important)
        if "studio album" in lower_header or "top albums" in lower_header:
            return "Studio Album"
        if "live album" in lower_header:
            return "Live Album"
        if "official singles, eps" in lower_header or \
           "singles / eps" in lower_header or \
           "ep/single" in lower_header or \
           "eps & singles" in lower_header or \
           "singles, eps, fan club & promo" in lower_header:
            return "EP/Single"
        if "ep" in lower_header:
            return "EP"
        if "single" in lower_header:
            return "Single"
        # Check for "compilation" before "video/dvd" if "dvd-a" might be present and unstripped in a compilation header
        if "compilation" in lower_header:
            return "Compilation"
        if "boxset" in lower_header or "box set" in lower_header: # Check for boxset after compilation general check
             # If "boxset & compilations" it will be "Compilation" by above, which is acceptable.
             # If just "boxset", it will be "Boxset".
            return "Boxset"
        if "videos" in lower_header or "video/dvd" in lower_header or "dvd" in lower_header or "blu-ray" in lower_header or "vhs" in lower_header:
            return "Video/DVD" # This should be checked after compilation if there's risk of 'dvd-a' in general suffix.

        logger.debug(f"Could not precisely normalize album type for header: '{header_text}'. Processed header: '{lower_header}'. Defaulting to 'Album'.")
        return "Album"

    def _get_cached_result(self, file_path: str) -> Optional[Dict]:
        """Get cached result for file path."""
        cache_file = self.cache_dir / f"{hash(file_path)}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache for {file_path}: {e}")
        return None

    def _save_to_cache(self, file_path: str, data: Dict):
        """Save result to cache."""
        cache_file = self.cache_dir / f"{hash(file_path)}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to cache result for {file_path}: {e}")

    def _read_local_html_content(self, file_path: Path) -> Optional[str]:
        """Read HTML content from local file, trying multiple encodings."""
        encodings_to_try = ['utf-8', 'iso-8859-1', 'latin1']
        last_exception = None
        for enc in encodings_to_try:
            try:
                logger.debug(f"Trying to read {file_path} with {enc} encoding...")
                # Added detailed path checks right before opening
                logger.debug(f"In _read_local_html_content: About to open path: {file_path}")
                logger.debug(f"In _read_local_html_content: Path exists? {Path(file_path).exists()}")
                logger.debug(f"In _read_local_html_content: Is file? {Path(file_path).is_file()}")
                with open(file_path, 'r', encoding=enc, errors='replace') as f:
                    content = f.read()
                logger.info(f"Successfully read {file_path} with {enc} encoding.")
                return content
            except UnicodeDecodeError as e:
                logger.warning(f"Failed to decode {file_path} with {enc}: {e}")
                last_exception = e
            except Exception as e: # Catch other potential file errors
                error_msg = f"Error reading file {file_path} with {enc}: {str(e)}"
                logger.error(error_msg)
                last_exception = e # Store it to be raised if all fail
                # Depending on the error, you might not want to try other encodings
                # For now, we'll let it try others unless it's a non-decode error like FileNotFoundError
                if not isinstance(e, UnicodeDecodeError):
                    break 
        
        # If all encodings failed
        error_msg = f"Failed to read file {file_path} after trying {', '.join(encodings_to_try)}."
        if last_exception:
            error_msg += f" Last error: {str(last_exception)}"
        logger.error(error_msg)
        raise ValueError(error_msg) # Or raise the last_exception itself

    def _resolve_relative_path(self, base_path: Path, relative_reference: str) -> Path:
        """
        Resolve a relative reference (like a link to an artist or album) to a local file path
        within the self.local_data_root directory.
        """
        logger.debug(f"_resolve_relative_path: self.local_data_root is currently '{self.local_data_root}'") # Log the current local_data_root
        # Normalize backslashes to forward slashes for regex and path consistency
        relative_reference = relative_reference.replace("\\\\", "/")

        # Extract the core filename (e.g., "albumXXXX.html") from the reference
        # It might have query parameters like ?id=...
        filename_match = re.match(r"([^?#]+)(\?[^#]*)?(#.*)?", relative_reference)
        
        if not filename_match:
            logger.warning(f"Could not extract filename from relative reference: '{relative_reference}' on page '{base_path.name}'. Returning base path.")
            return base_path # Fallback for unparsable references

        core_filename = filename_match.group(1)

        # Check if it's an album, artist, or reviews file pattern we expect locally.
        # These files are expected to be directly under self.local_data_root.
        if (re.fullmatch(r"album[a-zA-Z0-9.-]+\.html", core_filename) or 
            re.fullmatch(r"artist[a-zA-Z0-9.-]+\.html", core_filename) or 
            re.fullmatch(r"album-reviews[a-zA-Z0-9.-]+\.html", core_filename)):
            
            # Construct the path directly under self.local_data_root
            resolved_path = self.local_data_root / core_filename
            logger.info(f"Resolved relative reference '{relative_reference}' to '{resolved_path}' from base '{base_path.name}'")
            return resolved_path
        
        logger.warning(
            f"Relative reference '{relative_reference}' (core: '{core_filename}') on page '{base_path.name}' "
            f"does not match known local file patterns (e.g. albumXXXX.html). Returning original base path."
        )
        # If it doesn't match our specific file patterns, it might be a link to another part of the site
        # we don't have locally, or an external link. Returning base_path effectively means we don't follow it
        # as a local file for further parsing in the current context of resolving album/artist links.
        return base_path 

    def get_band_details(self, artist_id_or_path: Union[str, Path], use_cache: bool = True) -> Dict:
        """Get detailed information about a band from local HTML file."""
        try:
            # Determine the file path
            if isinstance(artist_id_or_path, Path):
                file_path = artist_id_or_path
            elif isinstance(artist_id_or_path, str):
                file_path = Path(artist_id_or_path)
            else:
                raise ValueError(f"Invalid artist_id_or_path type: {artist_id_or_path}")

            self.current_artist_file_path = self._resolve_path_for_reading(file_path)
            logger.debug(f"Resolved artist_file_path in get_band_details: {self.current_artist_file_path}")

            # Check cache
            if use_cache:
                cached = self._get_cached_result(str(self.current_artist_file_path))
                if cached:
                    return cached
            
            # Read and parse HTML
            content = self._read_local_html_content(self.current_artist_file_path)
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract band name
            name_tag = soup.find('h1') # Prefer h1 for artist name
            if not name_tag: # Fallback if h1 is not found, though typically it should be
                 # Check for the structure seen in album pages as a fallback, though less likely for artist main page
                name_tag = soup.find('h2', style="margin-top:1px;display:inline;")
                if name_tag and name_tag.find('a'): # If it's <h2...><a...>Artist</a></h2>
                    name_tag = name_tag.find('a')
            
            name = name_tag.text.strip() if name_tag else None
            
            # Extract genre and country
            h2_info = soup.find('h2', style="margin:1px 0px;padding:0;color:#777;font-weight:normal;")
            genre = country = None
            if h2_info:
                info_parts = h2_info.text.split('•')
                if len(info_parts) >= 2:
                    genre = info_parts[0].strip()
                    country = info_parts[1].strip()
            
            # Find biography
            bio_div = soup.find('div', id='artist-biography')
            biography_text = ""
            if bio_div:
                # Attempt to get the full biography text directly first
                # ProgArchives often has a "read more" that replaces the shortBio with the full text in moreBio
                # or moreBio simply contains the full text including what was in shortBio.
                more_bio_span = bio_div.find('span', id='moreBio')
                short_bio_span = bio_div.find('span', id='shortBio')

                if more_bio_span and more_bio_span.get_text(strip=True): # Prioritize moreBio if it has content
                    # We use decode_contents to better handle <br> tags for paragraph structure if needed,
                    # then clean it. If it just has text, get_text is fine.
                    # Using .stripped_strings and joining with newline is often best for preserving paragraphs.
                    biography_text = '\n\n'.join(more_bio_span.stripped_strings)
                    logger.debug("Biography extracted from moreBio span.")
                elif short_bio_span and short_bio_span.get_text(strip=True):
                    biography_text = '\n\n'.join(short_bio_span.stripped_strings)
                    logger.debug("Biography extracted from shortBio span (moreBio was empty or not found).")
                else: # Fallback if specific spans are not found or empty, try to get all text from bio_div
                    # This might grab more than just the bio if the structure is unexpected.
                    biography_text = '\n\n'.join(bio_div.stripped_strings)
                    logger.debug("Biography extracted from full artist-biography div (spans not found/empty).")
            
            # Remove any "read more" links or similar artifacts that might be at the very end.
            # The javascript:showFullBio(); link is often an <a> tag without text, so cleaning text content is key.
            # The previous re.sub for "read more$" is good.
            biography_text = re.sub(r'read more$', '', biography_text, flags=re.I).strip()
            # Further cleanup: excessive newlines or leading/trailing newlines introduced by join
            biography_text = re.sub(r'^\s+|\s+$', '', biography_text) # trim leading/trailing whitespace including newlines
            biography_text = re.sub(r'(\n\s*){2,}', '\n\n', biography_text).strip()

            # Find albums
            discography = []
            # Find all relevant section headers for discography types
            # Common headers are <h3> or <h4>, sometimes with <strong> inside.
            # e.g. <h3><strong>STUDIO ALBUMS</strong> (16)</h3>
            #      <h4>Official compilations (21)</h4>
            # We look for h3/h4 tags that are likely section titles for discographies.
            # A simple way is to find all h3 and h4, then for each, see if a 'discog' table follows.
            
            all_potential_headers = soup.find_all(['h3', 'h4'])
            logger.debug(f"Found {len(all_potential_headers)} potential discography section headers (h3, h4).")

            for header_tag in all_potential_headers:
                header_text = header_tag.get_text(strip=True)
                
                # Skip known non-discography headers explicitly
                if "reviews" in header_text.lower() or "forum topics" in header_text.lower() or \
                   "members zone" in header_text.lower() or "where to buy" in header_text.lower() or \
                   header_text.lower().startswith("related links") or \
                   "Add to album ratings" in header_text: # Example for Yes - Fragile page
                    logger.debug(f"Skipping non-discography header: '{header_text}'")
                    continue

                current_sibling = header_tag.find_next_sibling()
                current_table = None
                
                # Find the next table that is a valid discography table
                while current_sibling:
                    if current_sibling.name == 'table':
                        # MODIFIED VALIDITY CHECK: A table is potentially a discography table if it contains an album link.
                        if current_sibling.find('a', href=re.compile(self.album_link_pattern)):
                            current_table = current_sibling
                            logger.debug(f"Found valid discography table (tag: {current_table.name}, class: {current_table.get('class')}, id: {current_table.get('id')}) for header '{header_text}'")
                            break
                        else:
                            logger.debug(f"Sibling table found for header '{header_text}' but it's not a valid discography table (lacks definitive album links). Classes: {current_sibling.get('class', [])}. Will check next sibling.")
                    elif current_sibling.name in ['h3', 'h4', 'h2']: # Stop if we hit the next significant header
                        logger.debug(f"Encountered next header ('{current_sibling.name}') before finding suitable table for '{header_text}'.")
                        break
                    current_sibling = current_sibling.find_next_sibling()

                if current_table:
                    logger.info(f"Processing discography section: '{header_text}'. Table found.")
                    normalized_album_type = self._normalize_album_type(header_text, name if name else "Unknown Artist")
                    logger.info(f"Processing discography section: '{header_text}' (Normalized type: '{normalized_album_type}'). Table found.")

                    album_sources_in_section = [] # Holds BeautifulSoup objects, each for one album's HTML block
                    
                    # Attempt to find direct <tr> children. `recursive=False` is important.
                    rows = current_table.find_all('tr', recursive=False)
                    
                    # Check if rows list is not empty AND if these rows actually contain <td> elements.
                    if rows and any(row.find('td') for row in rows):
                        logger.debug(f"Processing table with {len(rows)} <tr> elements for '{header_text}'.")
                        for row in rows:
                            cells = row.find_all('td') # Get all <td>s within this <tr>
                            for cell_tag in cells: # cell_tag is a bs4.element.Tag
                                cell_html_content = str(cell_tag)
                                # A single <td> can contain multiple albums separated by <br><br>
                                individual_album_html_blocks = re.split(r'(?:<br\s*/?>\s*){2,}', cell_html_content)
                                for block_html in individual_album_html_blocks:
                                    if not block_html.strip():
                                        continue
                                    album_sources_in_section.append(BeautifulSoup(block_html, 'html.parser'))
                    else: 
                        # No direct <tr> children, or they were empty/lacked <td>s.
                        # Find all <td> elements within the current_table.
                        all_tds_in_table = current_table.find_all('td')
                        if all_tds_in_table:
                            logger.debug(f"No direct <tr> found or they lacked <td>s. Processing {len(all_tds_in_table)} <td> elements directly within table for '{header_text}'.")
                            for cell_tag in all_tds_in_table: # cell_tag is a bs4.element.Tag
                                cell_html_content = str(cell_tag)
                                # A single <td> can also contain multiple albums separated by <br><br>
                                individual_album_html_blocks = re.split(r'(?:<br\s*/?>\s*){2,}', cell_html_content)
                                for block_html in individual_album_html_blocks:
                                    if not block_html.strip():
                                        continue
                                    album_sources_in_section.append(BeautifulSoup(block_html, 'html.parser'))
                        else:
                            logger.debug(f"No <tr> and no <td> elements found in table for '{header_text}'. Skipping this table.")

                    logger.debug(f"Found {len(album_sources_in_section)} potential album sources in table for discography section '{header_text}'")

                    processed_first_block_in_section = False # Logging flag for first block

                    for album_source_soup in album_sources_in_section: # album_source_soup is now always a BeautifulSoup object
                        album_title = None
                        album_url = None
                        album_year = None
                        album_rating = None
                        album_type = None

                        if not processed_first_block_in_section:
                            logger.debug(f"FIRST BLOCK in section '{header_text}': HTML content (first 500 chars): {str(album_source_soup)[:500]}")

                        album_link_tag = album_source_soup.find('a', href=re.compile(self.album_link_pattern))
                        
                        if album_link_tag:
                            album_url = album_link_tag['href']
                            if not processed_first_block_in_section:
                                logger.debug(f"FIRST BLOCK: album_url extracted: {album_url}")

                            strong_in_link = album_link_tag.find('strong')
                            if strong_in_link:
                                album_title = strong_in_link.get_text(strip=True)
                                if not processed_first_block_in_section:
                                    logger.debug(f"FIRST BLOCK: title from strong_in_link: {album_title}")
                            elif album_link_tag.get_text(strip=True):
                                album_title = album_link_tag.get_text(strip=True)
                                if not processed_first_block_in_section:
                                    logger.debug(f"FIRST BLOCK: title from album_link_tag.get_text(): {album_title}")
                            else: 
                                strong_tag_in_block = album_source_soup.find('strong')
                                if strong_tag_in_block:
                                    album_title = strong_tag_in_block.get_text(strip=True)
                                    if not processed_first_block_in_section:
                                        logger.debug(f"FIRST BLOCK: title from strong_tag_in_block: {album_title}")
                        
                            if not album_title: 
                                raw_text_for_title = album_source_soup.get_text(separator=' ', strip=True)
                                # Simplified cleaning for this fallback
                                cleaned_text_for_title = re.sub(r'\\s*\\d+\\.\\d+.*ratings', '', raw_text_for_title, flags=re.I).strip()
                                cleaned_text_for_title = re.sub(r'\\(\\d{4}\\)', '', cleaned_text_for_title).strip() # Remove (YYYY)
                                album_title = cleaned_text_for_title.splitlines()[0].strip() if cleaned_text_for_title else None
                                if not processed_first_block_in_section:
                                    logger.debug(f"FIRST BLOCK: title from raw_text_for_title: '{raw_text_for_title[:100]}...' -> extracted title: {album_title}")
                        elif not processed_first_block_in_section:
                            logger.debug(f"FIRST BLOCK: album_link_tag not found.")

                        if not (album_title and album_url):
                            if not processed_first_block_in_section or not album_sources_in_section : # Log for first or if only one source
                                block_text_for_log = album_source_soup.get_text(strip=True)[:200] # More context
                                logger.debug(f"No valid album link/title found in block for section '{header_text}'. Title='{album_title}', URL='{album_url}'. Block text: '{block_text_for_log}...'. Skipping.")
                            processed_first_block_in_section = True # Mark as processed for logging after all first block logs
                            continue

                        # Extract Year
                        year_match_text = album_source_soup.get_text(separator=' ', strip=True)
                        year_search = re.search(self.year_pattern, year_match_text)
                        album_year_str = None # Initialize
                        if year_search:
                            album_year_str = year_search.group(1)
                            album_year = int(album_year_str)
                        if not processed_first_block_in_section:
                            logger.debug(f"FIRST BLOCK: year_match_text (first 50): '{year_match_text[:50]}...', extracted year: {album_year}")
                        
                        # Extract Rating
                        rating_span = album_source_soup.find('span', style=lambda x: x and 'color:#C75D4F' in x)
                        album_rating_str = None # Initialize
                        if 'album_rating' not in locals() and 'album_rating' not in globals(): # Pythonic way to ensure init if not already
                            album_rating = None
                        
                        if rating_span:
                            rating_text = rating_span.get_text(strip=True)
                            # MODIFIED REGEX: Ensures a valid number format, won't match just "."
                            rating_match_re = re.search(r'(\d+(?:\.\d+)?)', rating_text) 
                            if rating_match_re:
                                album_rating_str = rating_match_re.group(1)
                                try:
                                    album_rating = float(album_rating_str)
                                except ValueError:
                                    logger.warning(f"Could not convert rating string '{album_rating_str}' to float for text '{rating_text}' in block. Setting rating to None.")
                                    album_rating = None # Explicitly set to None on error
                            elif rating_text: # If span has text but it didn't match valid number format
                                # Define regex string separately to avoid SyntaxWarning in f-string
                                rating_regex_pattern_str = r'(\\d+(?:\\.\\d+)?)'
                                logger.debug(f"Rating text '{rating_text}' in span did not match number format '{rating_regex_pattern_str}'. Rating remains None.")
                            
                        if not processed_first_block_in_section:
                            # Log current album_rating which might be None
                            logger.debug(f"FIRST BLOCK: rating_span found: {bool(rating_span)}, extracted rating value: {album_rating}")

                        full_album_path = None
                        if album_url: # Only attempt to resolve if URL was found
                            full_album_path = self._resolve_relative_path(self.current_artist_file_path, album_url)
                        
                        if not processed_first_block_in_section:
                            logger.debug(f"FIRST BLOCK: full_album_path: {full_album_path}")
                            processed_first_block_in_section = True # Mark as processed for logging after all first block logs

                        if album_title and album_url and full_album_path:
                            # Convert full_album_path to be relative to self.local_data_root
                            try:
                                relative_album_path_obj = full_album_path.relative_to(self.local_data_root)
                                # Convert to string and use forward slashes for consistency
                                album_path_str = str(relative_album_path_obj).replace('\\\\', '/')
                            except ValueError as e:
                                logger.error(f"Could not make album path {full_album_path} relative to {self.local_data_root}: {e}")
                                # Fallback: use the full_album_path as string, clean it as best as possible
                                # This path might be absolute or not what's desired if relative_to fails.
                                temp_path_str = str(full_album_path)
                                if temp_path_str.startswith(str(self.local_data_root)):
                                    temp_path_str = temp_path_str[len(str(self.local_data_root)):]
                                album_path_str = temp_path_str.lstrip('/\\\\').replace('\\\\', '/')

                            album_data = {
                                "title": album_title,
                                "local_path": album_path_str,
                                "year": album_year,
                                "rating": album_rating,
                                "type": normalized_album_type
                            }
                            discography.append(album_data)
                            # This INFO log should appear for every successfully added album
                            logger.info(f"Successfully added album to discography: {album_title} (Year: {album_data['year']}), Type: {normalized_album_type}, Rating: {album_data['rating']}, Path: {album_data['local_path']}")
                        else:
                            # This general skip log might be useful if the first block specific logs don't catch the issue
                            logger.debug(f"Skipped album block. Title: '{album_title}', URL: '{album_url}', Path: '{full_album_path}'")

            logger.info(f"Finished processing all potential headers. Found total of {len(discography)} albums for artist {name}")
            
            details = {
                'local_path': str(self.current_artist_file_path),
                'name': name,
                'genre': genre,
                'country': country, 
                'biography': biography_text,
                'albums': discography,
                'scraped_at': datetime.now().isoformat()
            }
            
            if use_cache:
                self._save_to_cache(str(self.current_artist_file_path), details)
            
            return details
            
        except Exception as e:
            error_msg = f"Error getting band details from {artist_id_or_path}: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg}

    def get_album_data(self, album_id_or_path: Union[str, Path], use_cache: bool = True) -> Dict[str, Any]:
        """Get all data for a specific album, including trying to parse a dedicated reviews page.
        
        This method reads both the main album page and the separate reviews page
        if one exists (matching album-reviewsXXXX.html pattern), combining the data.
        """
        logger.debug(f"get_album_data called with: {album_id_or_path}")
        try: # Restore main try-except block
            resolved_f_path = self._resolve_path_for_reading(album_id_or_path)
            logger.debug(f"Resolved path for get_album_data: {resolved_f_path}")

            if use_cache:
                cached = self._get_cached_result(str(resolved_f_path))
                if cached:
                    logger.info(f"Cache hit for album: {resolved_f_path}")
                    return cached

            html_content = self._read_local_html_content(resolved_f_path)
            if not html_content:
                error_msg = f"HTML content not found or unreadable for {resolved_f_path}"
                logger.error(error_msg)
                return {"error": error_msg, "source_file": str(resolved_f_path)}

            soup = BeautifulSoup(html_content, 'html.parser')

            album_title = self._find_album_title(soup)
            artist_name, artist_page_link_local = self._find_album_artist(soup) # Unpack both name and link
            album_year = self._find_album_year(soup)
            album_rating_value, album_rating_count, album_review_count = self._find_album_rating(soup) # unpack all 3
            album_genre = self._find_album_genre(soup)
            album_type = self._find_album_type(soup)
            
            cover_image_tag = soup.find('meta', property='og:image')
            cover_image_url = cover_image_tag['content'] if cover_image_tag else None
            
            # Find the <strong> tag with "Songs / Tracks Listing"
            songs_header_tag = soup.find('strong', string=re.compile(r"Songs / Tracks Listing", re.I))
            track_content = None
            if songs_header_tag:
                # Find the next sibling <p> tag
                track_content = songs_header_tag.find_next_sibling('p')
            
            tracks = self._extract_tracks(track_content)
            
            lineup_content_candidates = [
                soup.find('div', class_='lineupContainer'), # Progarchives new layout
                soup.find('div', string=re.compile(r"LINE-UP")) # Fallback based on some older structures
                # TODO: Add more candidates if necessary based on HTML structure variations
            ]
            lineup_content_element = next((candidate for candidate in lineup_content_candidates if candidate is not None), None)

            if not lineup_content_element:
                # New: Try to find <strong>Line-up / Musicians</strong> (case-insensitive)
                strong_tag_header = soup.find('strong', string=re.compile(r"Line-up / Musicians", re.I))
                if strong_tag_header:
                    # The actual lineup content is expected in the next <p> sibling tag
                    lineup_content_element = strong_tag_header.find_next_sibling('p')
                    logger.info(f"SCRAPER_LINEUP_DEBUG: Found lineup via <strong>Line-up / Musicians</strong> header. Next sibling <p> is: {str(lineup_content_element)[:200] if lineup_content_element else 'None'}")
                else:
                    logger.warning("SCRAPER_LINEUP_DEBUG: Could not find lineup via 'lineupContainer', 'div with LINE-UP', or 'strong Line-up / Musicians'.")

            lineup = self._extract_lineup(lineup_content_element) # Pass the found element (could be div or p)

            # Parse reviews from the main album page
            reviews = self._parse_reviews_from_page(soup, source_file_path=resolved_f_path)
            processed_review_files = {resolved_f_path.name} # Keep track of files already processed for reviews
            
            # --- Attempt to parse dedicated reviews page (album-reviewsXXXX.html) ---
            dedicated_reviews_link_tag = soup.find('a', href=re.compile(r"album-reviews[a-zA-Z0-9.-]+\.html"))
            if dedicated_reviews_link_tag:
                reviews_page_href = dedicated_reviews_link_tag.get('href')
                if reviews_page_href:
                    reviews_page_filename = reviews_page_href.split('?')[0]
                    logger.info(f"Found dedicated reviews page link (album-reviews type): {reviews_page_href} (filename: {reviews_page_filename})")
                    dedicated_reviews_file_path = resolved_f_path.parent / reviews_page_filename
                    
                    if dedicated_reviews_file_path.name not in processed_review_files and dedicated_reviews_file_path.exists():
                        logger.info(f"Dedicated reviews page (album-reviews type) found locally: {dedicated_reviews_file_path}")
                        reviews_html_content = self._read_local_html_content(dedicated_reviews_file_path)
                        if reviews_html_content:
                            reviews_soup = BeautifulSoup(reviews_html_content, 'html.parser')
                            additional_reviews = self._parse_reviews_from_page(reviews_soup, source_file_path=dedicated_reviews_file_path)
                            if additional_reviews:
                                logger.info(f"Parsed {len(additional_reviews)} reviews from {dedicated_reviews_file_path}")
                                existing_review_signatures = {(r['text'], r['reviewer']) for r in reviews}
                                for ar in additional_reviews:
                                    if (ar['text'], ar['reviewer']) not in existing_review_signatures:
                                        reviews.append(ar)
                                        existing_review_signatures.add((ar['text'], ar['reviewer']))
                                processed_review_files.add(dedicated_reviews_file_path.name)
                    elif dedicated_reviews_file_path.name in processed_review_files:
                        logger.debug(f"Skipping already processed file for album-reviews link: {dedicated_reviews_file_path.name}")
                    else:
                        logger.warning(f"Dedicated reviews page (album-reviews type) file not found locally: {dedicated_reviews_file_path}")
            else:
                logger.info("No link to a dedicated 'album-reviews...' page found on the main album page.")

            # --- Attempt to parse individual reviewXXXX.html pages linked from the main album page ---
            logger.info(f"Searching for individual 'reviewXXXX.html' links on {resolved_f_path.name}")
            individual_review_links = soup.find_all('a', href=re.compile(r"review[a-zA-Z0-9.-]+\.html"))
            logger.info(f"Found {len(individual_review_links)} potential individual review links.")
            
            unique_review_files_to_parse = set()
            for link_tag in individual_review_links:
                href = link_tag.get('href')
                if href:
                    review_filename = href.split('?')[0] # Get base filename
                    if review_filename not in processed_review_files:
                        unique_review_files_to_parse.add(review_filename)
            
            logger.info(f"Found {len(unique_review_files_to_parse)} unique, unprocessed 'reviewXXXX.html' files to attempt parsing.")
            logger.debug(f"About to loop through {len(unique_review_files_to_parse)} review files: {unique_review_files_to_parse}") # LOG BEFORE LOOP

            for review_filename in unique_review_files_to_parse:
                logger.debug(f"Looping for review_filename: {review_filename}") # DETAIL LOG 1
                individual_review_file_path = resolved_f_path.parent / review_filename
                logger.debug(f"Attempting to load individual review from: {individual_review_file_path}")
                if individual_review_file_path.exists():
                    logger.info(f"Individual review file exists: {individual_review_file_path}") # DETAIL LOG 2 (changed from .info to .debug for consistency if preferred, but .info is fine here)
                    review_html_content = self._read_local_html_content(individual_review_file_path)
                    if review_html_content:
                        logger.debug(f"Successfully read HTML content for {review_filename}") # DETAIL LOG 3
                        review_soup = BeautifulSoup(review_html_content, 'html.parser')
                        additional_reviews = self._parse_reviews_from_page(review_soup, source_file_path=individual_review_file_path)
                        logger.debug(f"_parse_reviews_from_page returned {len(additional_reviews)} reviews for {review_filename}") # DETAIL LOG 4
                        if additional_reviews:
                            logger.info(f"Parsed {len(additional_reviews)} review(s) from individual file: {individual_review_file_path}")
                            existing_review_signatures = {(r['text'], r['reviewer']) for r in reviews}
                            for ar_idx, ar in enumerate(additional_reviews): # Should typically be one
                                logger.debug(f"Processing additional_review index {ar_idx} from {review_filename}")
                                if (ar['text'], ar['reviewer']) not in existing_review_signatures:
                                    reviews.append(ar)
                                    logger.info(f"<<< REVIEW APPENDED FOR {review_filename} >>>")
                                    existing_review_signatures.add((ar['text'], ar['reviewer']))
                                    logger.debug(f"Successfully appended review index {ar_idx} from {review_filename} to main reviews list.")
                                else:
                                    logger.debug(f"Skipping duplicate review index {ar_idx} from {review_filename}: {ar['reviewer']} - {ar['text'][:50]}...")
                            logger.debug(f"Finished iterating through additional_reviews for {review_filename}.")
                        processed_review_files.add(review_filename)
                        logger.info(f">>> {review_filename} ADDED TO processed_review_files >>>")
                    else:
                        logger.warning(f"Could not read content of individual review file: {individual_review_file_path}")
                        processed_review_files.add(review_filename)
                        logger.info(f">>> {review_filename} ADDED TO processed_review_files (AFTER READ FAIL) >>>")
                else:
                    logger.debug(f"Individual review file not found locally: {individual_review_file_path}") # DETAIL LOG 5
                logger.debug(f"End of current iteration for review_filename: {review_filename}. Processed_review_files: {processed_review_files}") # Replaces/refines "Finished processing review_filename..."
            logger.debug(f"Exited loop for unique_review_files_to_parse. Total reviews collected: {len(reviews)}") # LOG AFTER LOOP
                    
            data = {
                "album_title": album_title,
                "artist_name": artist_name,
                "artist_page_link_local": artist_page_link_local, # Add the new key here
                "year": album_year,
                "rating_value": album_rating_value,
                "rating_count": album_rating_count,
                "review_count": album_review_count,
                "genre": album_genre,
                "album_type": album_type,
                "cover_image_url": cover_image_url,
                "tracks": tracks,
                "lineup": lineup,
                "reviews": reviews, # Add reviews here
                "source_file": resolved_f_path.name,
                "last_parsed": datetime.now().isoformat()
            }

            if use_cache:
                self._save_to_cache(str(resolved_f_path), data)
            
            logger.info(f"Successfully parsed album data for: {album_title} by {artist_name}")
            return data
        except Exception as e: # Restore main exception handling
            error_msg = f"Error in get_album_data for {album_id_or_path}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg, "details": str(e), "source_file": str(album_id_or_path)}

    def _parse_reviews_from_page(self, soup: BeautifulSoup, source_file_path: Optional[Path] = None) -> List[Dict]:
        """Extract reviews from a page (either main album page or dedicated reviews page)."""
        reviews = []
        
        is_single_review_page = False
        page_title = soup.title.string if soup.title else ""

        if source_file_path and "review" in source_file_path.name.lower() and source_file_path.name.startswith("review"):
            is_single_review_page = True
        elif "review by" in page_title.lower() and "music review by" in page_title.lower(): # More specific for actual review titles
            is_single_review_page = True

        if is_single_review_page:
            logger.debug(f"Parsing as single review page: {source_file_path or page_title}")
            try:
                review_data = {}
                
                # Reviewer
                title_reviewer_match = re.search(r'music review by (.+)$', page_title, re.I)
                if title_reviewer_match:
                    review_data['reviewer'] = title_reviewer_match.group(1).strip()
                else:
                    reviewer_itemprop = soup.select_one('span[itemprop="reviewer"]')
                    if reviewer_itemprop:
                        review_data['reviewer'] = self._clean_text(reviewer_itemprop)
                    else: 
                        # For single review page, the main strong tag under a Collaborators link in the central table
                        reviewer_link = soup.select_one('td[valign="top"] > a[href*="Collaborators"] strong')
                        if not reviewer_link: # Fallback for different structures if the above is too specific
                             reviewer_link = soup.select_one('a[href*="Collaborators"] strong, a[href*="member.asp"] strong')
                        review_data['reviewer'] = self._clean_text(reviewer_link) if reviewer_link else "Unknown"

                # Rating
                rating_itemprop = soup.select_one('span[itemprop="rating"]')
                if rating_itemprop:
                    try:
                        rating_val = self._clean_text(rating_itemprop)
                        # Handle "X/Y" or just "X"
                        rating_match_text = re.match(r'(\d+)', rating_val)
                        if rating_match_text:
                            review_data['rating'] = int(rating_match_text.group(1))
                        else:
                            review_data['rating'] = None
                    except ValueError:
                        review_data['rating'] = None
                else:
                    # In single review page, rating is often an image directly in the review content div
                    # Example: <div style="padding:0px 10px;..."> <img src=".../3stars.gif"> ... </div>
                    review_content_div = soup.select_one('td[valign="top"] > div[style*="padding:0px 10px;border-left:solid 5px #f0f0f0;"]')
                    star_tag = None
                    if review_content_div:
                        star_tag = review_content_div.select_one('img[src*="stars.gif"]')
                    
                    if star_tag:
                        src_attribute = star_tag.get('src', '')
                        logger.debug(f"Single review page: Found star image src: {src_attribute}")
                        rating_match_img = re.search(r'(\d+)stars\.gif', src_attribute) # Regex for stars.gif
                        if rating_match_img:
                            try:
                                review_data['rating'] = int(rating_match_img.group(1))
                            except ValueError:
                                logger.warning(f"Single review page: Could not parse rating from image: {src_attribute}")
                                review_data['rating'] = None
                        else:
                             review_data['rating'] = None # No match from img src
                    else:
                        review_data['rating'] = None # No itemprop, no img
                
                # Date
                date_itemprop = soup.select_one('time[itemprop="dtreviewed"]')
                if date_itemprop and date_itemprop.get('datetime'):
                    review_data['date'] = date_itemprop.get('datetime')
                else: 
                    review_data['date'] = None 
                    
                # Text
                # The main text container from review4cc3.html analysis
                review_text_container = soup.select_one('td[valign="top"] > div[style*="padding:0px 10px;border-left:solid 5px #f0f0f0;"]')
                text_parts = []
                if review_text_container:
                    for element in review_text_container.children:
                        if isinstance(element, NavigableString):
                            cleaned_nav_string = self._clean_text(str(element))
                            if cleaned_nav_string: # Add only if not just whitespace
                                text_parts.append(cleaned_nav_string)
                        elif isinstance(element, Tag):
                            if element.name == 'p':
                                text_parts.append(self._clean_text(element.get_text(separator=' ', strip=True)))
                            # Stop before structured data or forms if they are siblings inside this container
                            elif element.get('itemscope') and element.get('itemtype') == 'http://data-vocabulary.org/Review':
                                break 
                            elif element.get('id', '').startswith('divCommentReviewForm') or element.find("form", {"name": "frmLogin"}):
                                break
                            elif element.name == 'img' and 'stars.gif' in element.get('src',''): # Skip the rating image itself
                                continue
                            else: # For other tags like <a>, <span> within the main flow, get their text
                                # This might be too greedy, but let's start with it.
                                # Consider if we should only take top-level text and <p> tags.
                                # For now, let's get all text from unexpected tags too, then clean.
                                temp_text = self._clean_text(element.get_text(separator=' ', strip=True))
                                if temp_text: # Add only if not just whitespace
                                    text_parts.append(temp_text)
                    
                    full_text = " ".join(text_parts).strip()
                    # Further clean-up: remove the reviewer's name if it's repeated from itemprop block at the end.
                    itemprop_block = review_text_container.find('div', itemprop='Review')
                    if itemprop_block:
                        itemprop_text = self._clean_text(itemprop_block.get_text(separator=' ', strip=True))
                        if full_text.endswith(itemprop_text):
                            full_text = full_text[:-len(itemprop_text)].strip()

                    review_data['text'] = full_text
                else:
                    review_data['text'] = ""
                
                if review_data.get('text') or review_data.get('rating') is not None: # Add if there's text or at least a rating
                    reviews.append({
                        'text': review_data.get('text', ""),
                        'reviewer': review_data.get('reviewer', "Unknown"),
                        'date': review_data.get('date'),
                        'rating': review_data.get('rating')
                    })
                else:
                    logger.debug(f"Skipping single review entry due to missing text and rating for {source_file_path or page_title}")


            except Exception as e:
                logger.warning(f"Error parsing single review page ({source_file_path if source_file_path else 'unknown'}): {e}", exc_info=True)

        else: # Existing logic for pages with multiple review containers
            logger.debug(f"Parsing as multi-review page: {source_file_path or page_title}")
            review_containers = soup.select(
                '.review-container, .album-review, div[style*="border-bottom:1px dotted #ccc"], div.review, article.review, '
                'div[style*="background-color:#f0f0f0"][style*="padding:5px"]' 
            )
            
            for container in review_containers:
                try:
                    current_review = {}
                    # Try itemprop first
                    reviewer_itemprop = container.select_one('span[itemprop="reviewer"]')
                    if reviewer_itemprop:
                        current_review['reviewer'] = self._clean_text(reviewer_itemprop)
                    else:
                        reviewer_elem = container.select_one('.reviewer-name, .review-author, a[href*="member.asp"] b, a[href*="member.asp"] strong, a[href*="Collaborators"] strong')
                        current_review['reviewer'] = self._clean_text(reviewer_elem) if reviewer_elem else "Unknown"
                    
                    date_itemprop = container.select_one('time[itemprop="dtreviewed"]')
                    if date_itemprop and date_itemprop.get('datetime'):
                        current_review['date'] = date_itemprop.get('datetime')
                    else:
                        date_elem = container.select_one('.review-date, small, span.icon-date')
                        date = None
                        if date_elem:
                            date_text = self._clean_text(date_elem)
                            # Try to parse date in various formats
                            # Order: "Month Day, Year", "Month Day Year", "YYYY-MM-DD", "DD-MM-YYYY" (or with /)
                            date_match = re.search(r'(\\w+\\s+\\d+,\\s+\\d{4})', date_text, re.IGNORECASE) # Month Day, Year
                            if not date_match:
                                date_match = re.search(r'(\\w+\\s+\\d+\\s+\\d{4})', date_text, re.IGNORECASE) # Month Day Year
                            if not date_match:
                                date_match = re.search(r'(\\d{4}[-/]\\d{1,2}[-/]\\d{1,2})', date_text) # YYYY-MM-DD or YYYY/MM/DD
                            if not date_match:
                                date_match = re.search(r'(\\d{1,2}[-/]\\d{1,2}[-/]\\d{4})', date_text) # DD-MM-YYYY or DD/MM/YYYY
                                
                            if date_match:
                                date_str = date_match.group(0) 
                                dt_object = None
                                try:
                                    if ',' in date_str and len(date_str.split()) == 3: # "May 1, 2024"
                                        dt_object = datetime.strptime(date_str, "%B %d, %Y")
                                    elif len(date_str.split()) == 3: # "May 1 2024"
                                        parts = date_str.split()
                                        dt_object = datetime.strptime(f"{parts[0]} {parts[1]}, {parts[2]}", "%B %d, %Y")
                                    elif '-' in date_str or '/' in date_str: # Try ISO-like or common Euro/US with delimiters
                                        # Normalize delimiters to '-' for fromisoformat or strptime
                                        normalized_date_str = date_str.replace('/', '-')
                                        try: # Try YYYY-MM-DD
                                            dt_object = datetime.strptime(normalized_date_str, "%Y-%m-%d")
                                        except ValueError:
                                            try: # Try DD-MM-YYYY (common in some logs/contexts)
                                                dt_object = datetime.strptime(normalized_date_str, "%d-%m-%Y")
                                            except ValueError:
                                                try: # Try MM-DD-YYYY
                                                    dt_object = datetime.strptime(normalized_date_str, "%m-%d-%Y")
                                                except ValueError:
                                                    logger.debug(f"Could not parse delimited date: {date_str}")
                                    date = dt_object.strftime("%Y-%m-%d") if dt_object else date_str
                                except ValueError as ve_date: # Broad catch for strptime issues
                                    logger.debug(f"Final attempt parsing date string '{date_str}' failed: {ve_date}")
                                    date = date_str # Fallback to raw string
                            else:
                                date = date_text # Store raw text if no regex match
                        current_review['date'] = date

                    rating_itemprop = container.select_one('span[itemprop="rating"]')
                    rating_val = None
                    if rating_itemprop:
                        try:
                            rating_text_cleaned = self._clean_text(rating_itemprop)
                            rating_match_text = re.match(r'(\d+)', rating_text_cleaned)
                            if rating_match_text:
                                rating_val = int(rating_match_text.group(1))
                        except ValueError:
                            pass # Handled by star image fallback
                    
                    if rating_val is None: # Fallback to star images or other text
                        star_tag_list = container.select('img[src*="stars.gif"]') 
                        if star_tag_list: 
                            star_tag = star_tag_list[0] 
                            src_attribute = star_tag.get('src', '')
                            logger.debug(f"Multi-review: Found star image src: {src_attribute}")
                            rating_match_img = re.search(r'(\d+)stars\.gif', src_attribute) # Regex for stars.gif
                            if rating_match_img:
                                try:
                                    rating_val = int(rating_match_img.group(1))
                                except ValueError:
                                    logger.warning(f"Multi-review: Could not parse rating number from image src: {src_attribute}")
                        else:
                            rating_elem = container.select_one('.review-rating, span.rating, span.ReviewRating')
                            if rating_elem:
                                rating_text_cleaned = self._clean_text(rating_elem)
                                rating_match_text = re.search(r'(\\d+)(?:/\\d+)?', rating_text_cleaned)
                                if rating_match_text:
                                    try:
                                        rating_val = int(rating_match_text.group(1))
                                    except ValueError: pass
                            else:
                                container_text_content = container.get_text()
                                rating_match_container = re.search(r'Rating:\\s*(\\d+)(?:/\\d+)?', container_text_content, re.IGNORECASE)
                                if rating_match_container:
                                    try:
                                        rating_val = int(rating_match_container.group(1))
                                    except ValueError: pass
                    current_review['rating'] = rating_val

                    review_text_tag = container.select_one('.review-text, .review-body, div.text, blockquote.text, div[style*="color:#333;margin-top:5px;"]')
                    text = self._clean_text(review_text_tag) if review_text_tag else ""
                    current_review['text'] = text
                    
                    if current_review.get('text') or current_review.get('rating') is not None:
                        reviews.append(current_review)
                    else:
                        logger.debug(f"Skipping multi-review entry due to missing text and rating from container: {str(container)[:100]}")

                except Exception as e:
                    logger.warning(f"Error parsing a review container on multi-review page: {e}", exc_info=True)
                    
        return reviews

    def _find_album_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Find album title."""
        # Try main heading first specifically for album pages
        # Example: <h1 style="line-height:1em;">LEFTOVERTURE</h1>
        title_h1 = soup.find('h1', style=lambda x: 'line-height:1em' in x if x else False)
        if title_h1:
            return title_h1.get_text(strip=True)

        # Fallback to other h1 selectors if the specific style isn't found
        title_h1_generic = soup.select_one('h1.album-title, h1.albumname, h1.album_name, h1') # Added generic h1
        if title_h1_generic:
            return title_h1_generic.get_text(strip=True)
            
        # Try meta title
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            content = meta_title.get('content', '')
            # Format is usually "Artist - Album (Year)"
            match = re.match(r'.+?\s*-\s*(.+?)\s*\(', content)
            if match:
                return match.group(1).strip()
        
        return None

    def _find_album_artist(self, soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
        """Find album artist name and their page link."""
        artist_name = None
        artist_page_link = None
        # Structure: <h2 style="margin-top:1px;display:inline;"><a href="artist1ce3.html?id=630">Kansas</a></h2>
        artist_h2 = soup.find('h2', style=lambda x: 'margin-top:1px;display:inline;' in x if x else False)
        if artist_h2:
            artist_link_tag = artist_h2.find('a', href=re.compile(r"artist[a-zA-Z0-9]+\.html\?id=\d+"))
            if artist_link_tag:
                artist_name = artist_link_tag.get_text(strip=True)
                artist_page_link = artist_link_tag.get('href') # Capture the href
                # The link might be relative, e.g., "artistXXXX.html". 
                # _resolve_relative_path could be used later if needed, or ensure it's resolved before returning.
                # For now, just return the raw href as found.

        if not artist_name:
            # Fallback to less specific selectors
            artist_link_fallback = soup.select_one('h2 a[href*="artist.asp"], .artistname a, h2 a[href*="artist"]') # Made more generic
            if artist_link_fallback:
                artist_name = artist_link_fallback.get_text(strip=True)
                artist_page_link = artist_link_fallback.get('href')
        
        if not artist_name:
            # Try meta title
            meta_title = soup.find('meta', property='og:title')
            if meta_title:
                content = meta_title.get('content', '')
                match = re.match(r'(.+?)\s*-\s*.+?\s*\(', content)
                if match:
                    artist_name = match.group(1).strip()
                    # No direct link from this meta tag, so artist_page_link remains None
                
        return artist_name, artist_page_link

    def _find_album_year(self, soup: BeautifulSoup) -> Optional[int]:
        """Find album release year."""
        # Priority 1: Meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            content = meta_desc['content']
            # Example: "Leftoverture is a music studio album recording by KANSAS ... released in 1976 on cd..."
            # Simpler regex to capture "released in YYYY"
            year_match_meta = re.search(r'released in ((?:19|20)\d{2})', content, re.I)
            if year_match_meta:
                logger.info(f"Year found in meta description: {year_match_meta.group(1)}")
                return int(year_match_meta.group(1))
            else: # Try another pattern if the first fails for meta description
                year_match_meta_alt = re.search(r'((?:19|20)\d{2})\s+album', content, re.I) # e.g. "1976 album"
                if year_match_meta_alt:
                     logger.info(f"Year found in meta description (alt pattern): {year_match_meta_alt.group(1)}")
                     return int(year_match_meta_alt.group(1))

        # Priority 2: Release info strong tag
        # Example: <strong>Studio Album, released in 1976</strong>
        release_info_strong = soup.find('strong', string=re.compile(r"released in", re.I))
        if release_info_strong:
            year_match_strong = re.search(r'released in ((?:19|20)\\d{2})', release_info_strong.get_text(), re.I)
            if year_match_strong:
                logger.debug(f"Year found in strong tag: {year_match_strong.group(1)}")
                return int(year_match_strong.group(1))

        # Priority 3: From OpenGraph title: <meta property="og:title" content="ARTIST - ALBUM (YEAR)" />
        og_title_meta = soup.find('meta', property='og:title')
        if og_title_meta and og_title_meta.get('content'):
            content = og_title_meta['content']
            year_match_og = re.search(r'\\(((?:19|20)\\d{2})\\)', content)
            if year_match_og:
                logger.debug(f"Year found in og:title: {year_match_og.group(1)}")
                return int(year_match_og.group(1))
        
        logger.warning("Album year not found.")
        return None

    def _find_album_rating(self, soup: BeautifulSoup) -> Tuple[Optional[float], Optional[int], Optional[int]]:
        """Find album rating value, number of ratings, and number of reviews."""
        rating_value = None
        rating_count = None
        review_count = None

        # Selector for the container that often holds all rating info
        # Example: <div style="margin-bottom:10px;padding-bottom:10px;border-bottom:1px dotted #CCC;">
        #             <span itemprop="average" id="avgRatings_1862" style="font-size:1.5em;color:#C75D4F;font-weight:bold;" title="4.24 out of 5 (PA Average Rating Value)">4.03</span>
        #             <span style="font-size:10px;">/ 5 | <span itemprop="votes" id="nbRatings_1862">1460</span> ratings | <a href="album-reviews.asp?id=1862">30 reviews</a></span>
        #          </div>
        # Or sometimes the rating count/review count is near a different structure:
        # <span id="ratingLabel" style="cursor:help;" title="4.03 based on 1,460 ratings and 30 reviews">
        
        # Primary target: The span with itemprop="average" for the rating value
        rating_span_avg = soup.find('span', {'itemprop': 'average', 'id': re.compile(r"avgRatings_\\d+")})
        if rating_span_avg:
            try:
                rating_text = rating_span_avg.get_text(strip=True)
                rating_value = float(rating_text)
                logger.debug(f"Rating value found with itemprop='average': {rating_value}")

                # Try to find rating_count and review_count in sibling/parent structures
                parent_div = rating_span_avg.find_parent('div') # Common case
                if not parent_div: # Sometimes it might be a direct sibling span
                    parent_div = rating_span_avg.parent

                if parent_div:
                    # Rating count (itemprop="votes")
                    votes_span = parent_div.find('span', {'itemprop': 'votes', 'id': re.compile(r"nbRatings_\\d+")})
                    if votes_span:
                        try:
                            rating_count = int(self._clean_text(votes_span.get_text(strip=True)).replace(',', ''))
                            logger.debug(f"Rating count found with itemprop='votes': {rating_count}")
                        except ValueError:
                            logger.warning(f"Could not parse rating count from itemprop='votes': {votes_span.get_text(strip=True)}")
                    
                    # Review count (link with "reviews")
                    reviews_link = parent_div.find('a', href=re.compile(r"(album-reviews|reviews\\.asp\\?id=)"), string=re.compile(r"reviews", re.I))
                    if reviews_link:
                        review_text = reviews_link.get_text(strip=True)
                        review_match = re.search(r'(\\d+)\\s+reviews', review_text, re.I)
                        if review_match:
                            try:
                                review_count = int(review_match.group(1))
                                logger.debug(f"Review count found from 'a' tag: {review_count}")
                            except ValueError:
                                logger.warning(f"Could not parse review count from 'a' tag: {review_text}")
                        elif "Show all reviews" in review_text and not review_count: # If it just says "Show all reviews" and we haven't found a count yet
                            logger.debug(f"Found 'Show all reviews' link, but no specific count. Review count might be on reviews page.")
                    
                    # Fallback for rating_count if not found via itemprop="votes" but rating_value was found
                    if rating_value is not None and rating_count is None:
                        # Check for pattern like "1,460 ratings" in the parent_div text
                        text_content_for_counts = parent_div.get_text(" ", strip=True)
                        rc_match = re.search(r'(\\d{1,3}(?:,\\d{3})*)\\s+ratings', text_content_for_counts, re.I)
                        if rc_match:
                            try:
                                rating_count = int(rc_match.group(1).replace(',', ''))
                                logger.debug(f"Rating count found by text search in parent: {rating_count}")
                            except ValueError:
                                logger.warning(f"Could not parse rating count from text: {rc_match.group(1)}")
                        
                        # Fallback for review_count if not found in link but rating_value was found
                        if review_count is None: # only if not found by <a> tag
                           rev_c_match = re.search(r'(\\d+)\\s+reviews', text_content_for_counts, re.I)
                           if rev_c_match:
                               try:
                                   review_count = int(rev_c_match.group(1))
                                   logger.debug(f"Review count found by text search in parent: {review_count}")
                               except ValueError:
                                   logger.warning(f"Could not parse review count from text: {rev_c_match.group(1)}")


            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse rating from itemprop='average': {rating_span_avg.get_text(strip=True) if rating_span_avg else 'N/A'}, Error: {e}")
                # Reset rating_value if primary parsing failed, to allow fallbacks for value if any
                rating_value = None


        # Fallback for rating_value if not found above (e.g. on some older pages or different structures)
        if rating_value is None:
            rating_span_style = soup.find('span', style=lambda x: x and 'color:#C75D4F' in x and 'font-weight:bold' in x)
            if rating_span_style:
                try:
                    rating_text = rating_span_style.get_text(strip=True)
                    rating_value = float(rating_text)
                    logger.debug(f"Rating value found with style color:#C75D4F: {rating_value}")
                    # Attempt to find counts nearby if primary method failed for value
                    if rating_count is None and review_count is None: # Only if not found earlier
                        parent_for_fallback_counts = rating_span_style.parent
                        if parent_for_fallback_counts:
                            text_content_for_counts = parent_for_fallback_counts.get_text(" ", strip=True)
                            rc_match = re.search(r'(\\d{1,3}(?:,\\d{3})*)\\s+ratings', text_content_for_counts, re.I)
                            if rc_match:
                                try:
                                    rating_count = int(rc_match.group(1).replace(',', ''))
                                    logger.debug(f"Fallback rating count found by text search: {rating_count}")
                                except ValueError:
                                    logger.warning(f"Could not parse fallback rating count from text: {rc_match.group(1)}")
                            
                            rev_c_match = re.search(r'(\\d+)\\s+reviews', text_content_for_counts, re.I)
                            if rev_c_match:
                                try:
                                    review_count = int(rev_c_match.group(1))
                                    logger.debug(f"Fallback review count found by text search: {review_count}")
                                except ValueError:
                                    logger.warning(f"Could not parse fallback review count from text: {rev_c_match.group(1)}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not parse rating from style color:#C75D4F: {rating_span_style.get_text(strip=True) if rating_span_style else 'N/A'}, Error: {e}")

        # Final catch-all from # <span id="ratingLabel" title="4.03 based on 1,460 ratings and 30 reviews">
        if rating_value is None or rating_count is None or review_count is None:
            rating_label_span = soup.find('span', {'id': 'ratingLabel', 'title': True})
            if rating_label_span:
                title_text = rating_label_span['title']
                logger.debug(f"Found ratingLabel span with title: {title_text}")
                # Example title: "4.03 based on 1,460 ratings and 30 reviews"
                # Example title: "Not rated yet"
                # Example title: "3.5 based on 2 ratings" (no reviews mentioned)
                if "Not rated yet" not in title_text:
                    val_match = re.search(r'(\\d+(?:\\.\\d+)?)', title_text)
                    if val_match and rating_value is None:
                        try:
                            rating_value = float(val_match.group(1))
                            logger.debug(f"Rating value from ratingLabel title: {rating_value}")
                        except ValueError:
                            logger.warning(f"Could not parse rating value from ratingLabel title: {val_match.group(1)}")

                    rc_match = re.search(r'(\\d{1,3}(?:,\\d{3})*)\\s+ratings', title_text, re.I)
                    if rc_match and rating_count is None:
                        try:
                            rating_count = int(rc_match.group(1).replace(',', ''))
                            logger.debug(f"Rating count from ratingLabel title: {rating_count}")
                        except ValueError:
                            logger.warning(f"Could not parse rating count from ratingLabel title: {rc_match.group(1)}")
                    
                    rev_c_match = re.search(r'(\\d+)\\s+reviews', title_text, re.I)
                    if rev_c_match and review_count is None:
                        try:
                            review_count = int(rev_c_match.group(1))
                            logger.debug(f"Review count from ratingLabel title: {review_count}")
                        except ValueError:
                            logger.warning(f"Could not parse review count from ratingLabel title: {rev_c_match.group(1)}")
        
        if rating_value is None and rating_count is None and review_count is None:
            logger.warning("Album rating, rating count, and review count not found.")
        
        return rating_value, rating_count, review_count

    def _find_album_genre(self, soup: BeautifulSoup) -> Optional[str]:
        """Find album genre (specifically subgenre on album pages)."""
        # Structure on album page: <h1>ALBUM</h1><h2><a>ARTIST</a></h2> &bull; <h2 style="...color:#777...">SUBGENRE</h2>
        main_h1 = soup.find('h1', style=lambda x: 'line-height:1em' in x if x else False)
        if not main_h1: # Fallback to any h1 if specific one isn't found
            main_h1 = soup.find('h1')

        if main_h1:
            # Find the second h2 tag that is a sibling or very close, after the artist's h2
            artist_h2 = main_h1.find_next_sibling('h2')
            if artist_h2 and artist_h2.find_next_sibling('h2'):
                genre_h2 = artist_h2.find_next_sibling('h2')
                if genre_h2 and 'color:#777' in genre_h2.get('style', ''):
                    return genre_h2.get_text(strip=True)
        
        # Fallback: Try meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            # Example: "...by KANSAS (Symphonic Prog/Progressive Rock) released..."
            # We want the first part before a potential slash if multiple are listed.
            genre_match = re.search(r'\\(([^/)]+)(?:/[^)]*)?\\)\\s+released', meta_desc['content'])
            if genre_match:
                return genre_match.group(1).strip()

        # Fallback to existing general selectors (less likely for specific album subgenre)
        genre_row = soup.find('td', string=re.compile(r'Genre:', re.I))
        if genre_row:
            value = genre_row.find_next_sibling('td')
            if value:
                return value.get_text(strip=True)
                
        # Try genre heading
        genre_h2 = soup.find('h2', class_='genre')
        if genre_h2:
            return genre_h2.get_text(strip=True)
            
        return None

    def _find_album_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Find album type (Studio, Live, etc)."""
        # Priority 1: Strong tag near top of content, e.g., <strong>Studio Album, released in 1976</strong>
        # This is often found as a direct child of a div or td after the main album header.
        # Let's search for a strong tag containing "released in" and extract the type part.
        strong_tag_type = soup.find('strong', string=re.compile(r"(Studio Album|Live Album|EP|Single|Compilation|Boxset|Box Set|Video|DVD|Blu-ray).*, released in \\d{4}", re.I))
        if strong_tag_type:
            type_match = re.match(r"(Studio Album|Live Album|EP|Single|Compilation|Boxset|Box Set|Video|DVD|Blu-ray)", strong_tag_type.get_text(strip=True), re.I)
            if type_match:
                # Normalize common variations
                album_type_text = type_match.group(1).lower()
                if "studio" in album_type_text: return "Studio Album"
                if "live" in album_type_text: return "Live Album"
                if "ep" == album_type_text: return "EP"
                if "single" == album_type_text: return "Single"
                if "compilation" in album_type_text: return "Compilation"
                if "box" in album_type_text: return "Boxset" # Handles "Boxset", "Box Set"
                if "video" in album_type_text or "dvd" in album_type_text or "blu-ray" in album_type_text : return "Video/DVD"
                return type_match.group(1) # Return as is if not specifically mapped

        # Priority 2: Meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            content = meta_desc['content']
            # Example: "Leftoverture is a music studio album recording..."
            type_match_meta = re.search(r'is a music ([a-zA-Z ]+?) recording', content, re.I)
            if type_match_meta:
                album_type_text = type_match_meta.group(1).strip().lower()
                # Normalize common variations from meta description
                if "studio album" in album_type_text: return "Studio Album"
                if "live album" in album_type_text: return "Live Album"
                if "ep" == album_type_text : return "EP" # Exact match for EP
                if "single" == album_type_text: return "Single" # Exact match
                if "compilation" in album_type_text: return "Compilation"
                if "box set" in album_type_text or "boxset" in album_type_text : return "Boxset"
                # If it's just "album", it's likely a studio album if no other info
                if album_type_text == "album": return "Studio Album" 
                return type_match_meta.group(1).strip() # Return the extracted type
        
        # Fallback to old logic (less likely to be accurate for ProgArchives album pages)
        type_row = soup.find('td', string=re.compile(r'Type:', re.I))
        if type_row:
            value = type_row.find_next_sibling('td')
            if value:
                album_type = value.get_text(strip=True)
                # Normalize album types
                type_map = {
                    'studio': 'Studio Album',
                    'live': 'Live Album',
                    'compilation': 'Compilation',
                    'ep': 'EP',
                    'single': 'Single'
                }
                lower_type = album_type.lower()
                for key, normalized in type_map.items():
                    if key in lower_type:
                        return normalized
                return album_type
        return None

    def _extract_tracks(self, track_content: Optional[Tag]) -> List[Dict]:
        """Extract track information from track listing section."""
        tracks = []
        if not track_content:
            logger.warning("_extract_tracks called with no track_content.")
            return tracks

        track_lines = []
        current_line_segments = []
        # Iterate over all elements within track_content to build lines based on <br> tags
        for element in track_content.descendants: # Using descendants to catch text even within nested tags
            if isinstance(element, NavigableString):
                stripped_text = str(element).strip()
                if stripped_text:
                    current_line_segments.append(stripped_text)
            elif isinstance(element, Tag) and element.name == 'br':
                if current_line_segments: # End of a line
                    track_lines.append(" ".join(current_line_segments))
                current_line_segments = [] # Reset for next line
        
        if current_line_segments: # Add any remaining line content after the last <br> or if no <br>s
            track_lines.append(" ".join(current_line_segments))

        if not track_lines: # If track_content had no <br> and was just a block of text
            # Fallback to splitting by newline characters in the raw text of the container
            raw_text = track_content.get_text(separator='\n', strip=True)
            track_lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
            if track_lines:
                logger.debug(f"_extract_tracks: No <br> tags found, using text split by newline. Lines: {track_lines[:3]}")
        else:
            logger.debug(f"_extract_tracks: Lines extracted using <br> tags. Lines: {track_lines[:3]}")

        track_number_counter = 0
        # Regex to capture: Optional number, Title, Optional (Duration)
        # Duration can be (M:SS) or (H:MM:SS)
        # Title can have spaces, hyphens, almost anything.
        # Subtrack: "- a. Sub Title (Duration)"
        # Main track: "1. Title (Duration)" or "Title (Duration)" or "I. Title (Duration)"
        # Note: Subtrack numbering can be a, b, c or 1, 2, 3 or i, ii, iii or A, B, C
        # Refined sub_track_pattern to better handle multi-level identifiers like a.b.c
        sub_track_pattern = re.compile(r"^\s*-\s*([a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*)\.?\s*(.+?)(?:\s*\((\d{1,2}:\d{2}(?::\d{2})?)\))?$")
        # Add negative lookahead to main_track_pattern to avoid matching lines starting with typical sub-track indicators ("- ")
        main_track_pattern = re.compile(r"^(?!\s*-\s)(?:(\d+)\.(?:\s+|$))?(?:([A-Z])\.\s+)?(?:([IVXLCDM]+)\.\s+)?(.+?)(?:\s*\((\d{1,2}:\d{2}(?::\d{2})?)\))?$")

        for line_idx, line in enumerate(track_lines):
            line = line.strip()
            logger.debug(f"Processing track line {line_idx + 1}: '{line}'")

            # Must calculate main_match and sub_match *before* this conditional block
            # as the last condition depends on them.
            sub_match = sub_track_pattern.match(line)
            main_match = main_track_pattern.match(line)

            # Specific early skips for problematic lines observed in ELP album
            if line == "-":
                logger.debug(f"Skipping non-track line (is a hyphen): '{line}'")
                continue
            # Regex to catch lines like "7-18. High-Res stereo version..."
            if re.match(r"^\\s*\\d+\\s*-\\s*\\d+\\s*\\..*", line): 
                logger.debug(f"Skipping non-track line (looks like a track range summary): '{line}'")
                continue

            if not line or \
               line.lower().startswith("total time") or \
               line.lower().startswith("total side") or \
               line.lower().startswith("cd ") or \
               line.lower().startswith("lp ") or \
               line.lower().startswith("disc ") or \
               line.lower().startswith("* recorded at") or \
               line.lower().startswith("$ recorded at") or \
               line.lower().startswith("notes:") or \
               line.lower().startswith("previously unreleased") or \
               re.match(r"^\\s*on \\d{4} .*remaster", line.lower()) or \
               re.match(r"^-? ?bonus cd from", line.lower()) or \
               re.match(r"^-? ?bonus dvd from", line.lower()) or \
               re.match(r"^-? ?bonus dvd-audio from", line.lower()) or \
               re.match(r"^-? ?tracks? from", line.lower()) or \
               re.match(r"^\\s*Side [A-D1-4]:", line, re.IGNORECASE) or \
               re.match(r"^\\s*\\(Side [A-D1-4]\\)", line, re.IGNORECASE) or \
               re.match(r"^\\s*-\\s*$", line) or \
               re.match(r"^-? ?(?:\\d{4} )?(?:stereo|original|quad|5\\.1) mix(?:es)?(?: by .*)? ?-?$", line.lower().strip()) or \
               re.match(r"^-? ?(?:japanese )?bonus track(?:s)?:? ?-?$", line.lower().strip()) or \
               line.lower().startswith("bonus track") or \
               re.match(r"^\\s*\\d+\\s*-\\s*\\d+\\s*\\..*", line, re.IGNORECASE) or \
               (main_match is None and sub_match is None):
                logger.debug(f"Skipping non-track line: '{line}'")
                continue

            title = None
            duration = None
            number_str = None # Can be digit or roman/letter for subtracks
            is_sub_track = False

            if sub_match:
                is_sub_track = True
                number_str = sub_match.group(1) 
                raw_title_candidate = sub_match.group(2)
                duration_from_regex = sub_match.group(3)
                logger.debug(f"Sub-track matched: id='{number_str}', raw_title='{raw_title_candidate}', duration_regex='{duration_from_regex}'")
                # Check if it's an instrumental sub-part for a main track
                if raw_title_candidate and raw_title_candidate.lower() == "instrumental" and tracks and not tracks[-1].get('is_sub_track'):
                    tracks[-1]['title'] += " (Instrumental)"
                    logger.debug(f"Appended (Instrumental) to previous main track: {tracks[-1]['title']}")
                    continue 
            elif main_match:
                num_digit = main_match.group(1)
                num_letter_cap = main_match.group(2) 
                num_roman = main_match.group(3) 
                raw_title_candidate = main_match.group(4)
                duration_from_regex = main_match.group(5) 
                
                number_str = num_digit if num_digit else (num_letter_cap if num_letter_cap else num_roman)
                logger.debug(f"Main track matched: num_str='{number_str}', raw_title='{raw_title_candidate}', duration_regex='{duration_from_regex}'")
            
            if raw_title_candidate:
                title = raw_title_candidate.strip().rstrip(':').strip()
                duration = duration_from_regex.strip() if duration_from_regex else None

                # If duration wasn't captured by the main regex, try to parse it from the end of the title
                if not duration and title:
                    duration_search = re.search(r'\s+\((\d{1,2}:\d{2}(?::\d{2})?)\)$|\[(\d{1,2}:\d{2}(?::\d{2})?)\]$', title) # Supports (mm:ss) or [mm:ss]
                    if duration_search:
                        # The duration can be in group 1 (for parentheses) or group 2 (for brackets)
                        captured_duration = duration_search.group(1) or duration_search.group(2)
                        if captured_duration:
                            duration = captured_duration
                            title = title[:duration_search.start()].strip() # Update title by removing the duration part
                            logger.debug(f"Post-regex duration parse: title='{title}', duration='{duration}'")

                # Clean title further
                if title.lower().endswith(" bonus track"): title = title[:-12].strip()
                if title.lower().startswith("bonus:"): title = title[6:].strip()

                actual_track_number = None
                if is_sub_track:
                    actual_track_number = number_str
                elif number_str and number_str.isdigit():
                    actual_track_number = int(number_str)
                    track_number_counter = actual_track_number
                else: # No explicit number for a main track, or non-digit (roman)
                    track_number_counter += 1
                    actual_track_number = number_str if number_str else track_number_counter

                tracks.append({
                    'number': actual_track_number,
                    'title': title,
                    'duration': duration.strip() if duration else None,
                    'is_sub_track': is_sub_track
                })
                logger.debug(f"Added track: {tracks[-1]}")
            elif line: # Only log if it's a non-empty line that didn't match and wasn't filtered
                logger.warning(f"Line not parsed as track (no title extracted): '{line}'")
                    
        logger.info(f"Extracted {len(tracks)} tracks.")
        return tracks

    def _extract_lineup(self, lineup_content: Optional[Tag]) -> List[Dict]:
        """Extracts lineup information (musicians and their roles/instruments)."""
        logger.info(f"SCRAPER_LINEUP_DEBUG: _extract_lineup called. Received lineup_content: {str(lineup_content)[:200] if lineup_content else 'None'}")
        lineup_list = []
        if not lineup_content:
            logger.warning("SCRAPER_LINEUP_DEBUG: _extract_lineup received no content (lineup_content is None).")
            return lineup_list

        # The content often starts with a <b>Musicians</b> or similar, followed by <br /> tags and text lines.
        # Text lines can be "- Musician Name / Role1, Role2"
        # Or sometimes just "Musician Name (Role1, Role2)"
        # Or even tables <table><tr><td>Name</td><td>Roles</td></tr>...</table>

        # Attempt 1: Simple <br /> separated list after a <b> tag (common pattern)
        # Remove all <b> tags to simplify processing the text lines if any
        for b_tag in lineup_content.find_all('b'):
            b_tag.decompose() # Remove <b> tags like "Musicians", "Line-up", etc.

        # Get all direct string content, splitting by <br> might be an option
        # Or iterate through contents and process NavigableString nodes
        raw_text_lines = []
        for element in lineup_content.stripped_strings: # stripped_strings handles multiple lines and spacing well
            raw_text_lines.append(element)
        
        logger.info(f"SCRAPER_LINEUP_DEBUG: _extract_lineup - Raw text lines from lineup_content: {raw_text_lines}") # Changed to info

        for line in raw_text_lines:
            line = line.strip()
            line_lower = line.lower() # For case-insensitive checks

            # Skip headers, sub-headers, or common non-musician lines
            if not line or \
               line_lower == 'musicians' or \
               line_lower == 'line-up' or \
               line_lower.startswith('with:') or \
               line_lower.startswith('guest musicians:') or \
               line_lower.startswith('additional musicians:') or \
               line_lower.startswith('featuring:') or \
               line_lower == '-': # Skip standalone hyphens sometimes used as separators
                logger.info(f"SCRAPER_LINEUP_DEBUG: _extract_lineup - Skipping header/separator line: '{line}'")
                continue
            
            # Common pattern: "- Musician Name / Instrument1, Instrument2"
            # Or: "Musician Name - Instrument1, Instrument2"
            # Or: "Musician Name (Instrument1, Instrument2)"
            
            musician_name = None
            instruments_roles = None

            # Try splitting by " / " first, as it's a common delimiter
            parts = []
            if ' / ' in line:
                parts = line.split(' / ', 1)
            elif ' - ' in line and not line.startswith('-'): # Ensure " - " is not the leading bullet
                # Find the first " - " that is not at the beginning of the string
                match_dash = re.search(r'(.+?)\s+-\s+(.+)', line)
                if match_dash:
                    parts = [match_dash.group(1), match_dash.group(2)]
            
            if len(parts) == 2:
                musician_name = parts[0].strip()
                instruments_roles = parts[1].strip()
            else: # Fallback or if no clear delimiter / role found
                # Could be just a name, or name (roles in parentheses)
                # Check for roles in parentheses at the end of the line
                match_parens = re.match(r'(.+?)\s+\(([^)]+)\)$', line)
                if match_parens:
                    musician_name = match_parens.group(1).strip()
                    instruments_roles = match_parens.group(2).strip()
                else:
                    # Assume the whole line is the musician name if no roles are clearly identified
                    musician_name = line
                    instruments_roles = "Not specified" # Or None, depending on desired output
            
            # Clean up leading hyphens or bullets from musician_name if present
            if musician_name and musician_name.startswith('-'):
                musician_name = musician_name[1:].strip()
            
            if musician_name:
                logger.info(f"SCRAPER_LINEUP_DEBUG: _extract_lineup - Adding: Musician='{musician_name}', Roles='{instruments_roles}'") # Changed to info
                lineup_list.append({
                    'musician': musician_name,
                    'instruments': instruments_roles
                })
            else:
                logger.info(f"SCRAPER_LINEUP_DEBUG: _extract_lineup - Could not parse musician from line: '{line}'") # Changed to info
        
        if not lineup_list and lineup_content.get_text(strip=True):
             logger.warning(f"SCRAPER_LINEUP_DEBUG: _extract_lineup - Parsed 0 members, but lineup_content had text. Content: {lineup_content.get_text(strip=True)[:200]}")

        return lineup_list

    def _clean_text(self, text: Optional[Union[Tag, str]]) -> str:
        """Clean text content by removing extra whitespace and HTML."""
        if not text:
            return ""
        if hasattr(text, 'get_text'):
            # If it's a Tag, get its text
            text = text.get_text(strip=True)
        # Remove HTML tags and normalize whitespace
        text = re.sub(r'<[^>]+>', '', str(text))
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _resolve_path_for_reading(self, file_path_or_name: Union[str, Path]) -> Path:
        path_obj = Path(file_path_or_name)
        
        # If path_obj is already absolute and exists, use it
        if path_obj.is_absolute():
            if path_obj.exists():
                return path_obj
            else:
                raise FileNotFoundError(f"Absolute path {path_obj} provided does not exist.")

        # If path_obj is relative, check if it exists as is (relative to CWD)
        # This handles cases where glob provides a path like "ProgArchives Data/..."
        # or if the path is already correctly relative to the project root.
        if path_obj.exists():
            return path_obj.resolve() # Return absolute path

        # Fallback: try joining with self.local_data_root using only the filename part of path_obj
        # This is intended for cases where file_path_or_name might be just "albumXXXX.html"
        # and needs to be found within self.local_data_root.
        resolved_from_root = self.local_data_root / path_obj.name 
        if resolved_from_root.exists():
            logger.debug(f"Resolved {path_obj.name} using local_data_root to {resolved_from_root}")
            return resolved_from_root
            
        # If none of the above worked, the file is not found through expected mechanisms.
        raise FileNotFoundError(f"File not found. Checked absolute: {path_obj}, "
                                f"relative to CWD: {path_obj.resolve()} (exists: {path_obj.exists()}), "
                                f"and within data root (using name): {resolved_from_root} (exists: {resolved_from_root.exists()})")