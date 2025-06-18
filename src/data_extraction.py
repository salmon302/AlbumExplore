import os
import json
from bs4 import BeautifulSoup
import re

# --- Configuration ---
BASE_PATH = "c:\\Users\\salmo\\Documents\\GitHub\\AlbumExplore\\ProgArchives Data"
ALBUM_FILES_PATH = os.path.join(BASE_PATH, "Website", "ProgArchives", "www.progarchives.com")
SUBGENRE_DEF_PATH = os.path.join(BASE_PATH, "ProgSubgenres")
OUTPUT_PATH = "c:\\Users\\salmo\\Documents\\GitHub\\AlbumExplore" # Store JSON files in the root for now

ALBUMS_JSON_PATH = os.path.join(OUTPUT_PATH, "albums.json")
ARTISTS_JSON_PATH = os.path.join(OUTPUT_PATH, "artists.json")
SUBGENRES_JSON_PATH = os.path.join(OUTPUT_PATH, "subgenres.json")

# --- Helper Functions ---
def get_meta_content(soup, property_name=None, name_value=None):
    '''Extracts content from a meta tag.'''
    if property_name:
        tag = soup.find("meta", property=property_name)
    elif name_value:
        tag = soup.find("meta", attrs={"name": name_value})
    else:
        return None
    return tag["content"] if tag else None

def parse_album_file(file_path):
    '''Parses a single album HTML file.'''
    print(f"Parsing album: {file_path}")
    album_data = {"reviews": [], "lineup": [], "tracklist": []}
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f, 'html.parser')

        # Meta description: "Album Title by Artist (Year) (Recording Type) (Subgenre(s))"
        meta_desc = get_meta_content(soup, name_value="description")
        if meta_desc:
            # Basic parsing, will need refinement for complex cases
            parts = meta_desc.split(" by ")
            album_data["album_title"] = parts[0].strip()
            if len(parts) > 1:
                artist_year_type_genre = parts[1].split(" (")
                album_data["artist_name_raw"] = artist_year_type_genre[0].strip()
                if len(artist_year_type_genre) > 1:
                    album_data["year_raw"] = artist_year_type_genre[1].replace(")", "").strip()
                if len(artist_year_type_genre) > 2:
                    album_data["recording_type_raw"] = artist_year_type_genre[2].replace(")", "").strip()
                if len(artist_year_type_genre) > 3:
                    album_data["subgenres_raw"] = [s.replace(")", "").strip() for s in artist_year_type_genre[3:]]


        album_data["cover_image_url"] = get_meta_content(soup, property_name="og:image")

        # Artist link
        artist_link_tag = soup.find("h2").find("a") if soup.find("h2") else None
        if artist_link_tag and artist_link_tag.has_attr("href"):
            album_data["artist_page_url_relative"] = artist_link_tag["href"]


        # --- Extracting from main body (Example placeholders - needs detailed implementation) ---

        # Tracklist (highly variable structure)
        # Example: Look for divs with class 'trackList' or similar
        tracklist_section = soup.find("div", class_="trackList") # This is a guess, inspect HTML
        if tracklist_section:
            for track_item in tracklist_section.find_all("li"): # Another guess
                # Extract track title, duration, etc.
                album_data["tracklist"].append({"title": track_item.text.strip()}) # Simplified

        # Line-up/Musicians
        lineup_section = soup.find("div", id="lineup") # Guess
        if lineup_section:
            for member_item in lineup_section.find_all("p"): # Guess
                album_data["lineup"].append({"member": member_item.text.strip()}) # Simplified

        # Ratings (Overall)
        # Example: <span class="average">4.5</span> (<span class="votes">100</span> votes)
        avg_rating_tag = soup.find("span", class_="average") # Guess
        if avg_rating_tag:
            album_data["average_rating"] = avg_rating_tag.text.strip()
        votes_tag = soup.find("span", class_="votes") # Guess
        if votes_tag:
            album_data["rating_count"] = votes_tag.text.strip().split(" ")[0] # "100 votes" -> "100"

        # Individual Reviews (often on a separate page or dynamically loaded)
        # This part will likely require handling links to album-reviewsXXXX.html
        # For now, let's assume some reviews might be on the main page
        review_elements = soup.find_all("div", class_="review") # Guess
        for rev_el in review_elements:
            reviewer = rev_el.find(class_="reviewerName").text.strip() if rev_el.find(class_="reviewerName") else "N/A" # Guess
            rating = rev_el.find(class_="rating").text.strip() if rev_el.find(class_="rating") else "N/A" # Guess
            text = rev_el.find(class_="reviewText").text.strip() if rev_el.find(class_="reviewText") else "N/A" # Guess
            date = rev_el.find(class_="reviewDate").text.strip() if rev_el.find(class_="reviewDate") else "N/A" # Guess
            album_data["reviews"].append({"reviewer": reviewer, "rating": rating, "text": text, "date": date})

        # Link to all reviews page
        all_reviews_link = soup.find("a", string=lambda t: t and "show all reviews" in t.lower())
        if all_reviews_link and all_reviews_link.has_attr("href"):
            album_data["all_reviews_page_url_relative"] = all_reviews_link["href"]

        return album_data
    except Exception as e:
        print(f"Error parsing album {file_path}: {e}")
        return {"file_path": file_path, "error": str(e)}


def parse_artist_file(file_path):
    '''Parses a single artist HTML file.'''
    print(f"Parsing artist: {file_path}")
    artist_data = {}
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f, 'html.parser')

        # Meta description: "Artist Name (Genre) (Country)"
        meta_desc = get_meta_content(soup, name_value="description")
        if meta_desc:
            parts = meta_desc.split(" (")
            artist_data["artist_name"] = parts[0].strip()
            if len(parts) > 1:
                artist_data["genre_raw"] = parts[1].replace(")", "").strip()
            if len(parts) > 2:
                artist_data["country_raw"] = parts[2].replace(")", "").strip()

        # Biography
        bio_div = soup.find("div", id="artist-biography") # As per plan
        if bio_div:
            short_bio_span = bio_div.find("span", id="shortBio")
            more_bio_span = bio_div.find("span", id="moreBio")
            if more_bio_span and more_bio_span.get_text(strip=True): # Prefer full bio
                artist_data["biography"] = more_bio_span.get_text(separator="\n", strip=True)
            elif short_bio_span:
                artist_data["biography"] = short_bio_span.get_text(separator="\n", strip=True)
            else: # Fallback to the whole div if spans are not there or empty
                artist_data["biography"] = bio_div.get_text(separator="\n", strip=True)


        # Official Website
        # Example: <a href="http://www.example.com" title="Official Website">Official Website</a>
        # This needs to be more robust, look for specific patterns or link text
        website_link_tag = soup.find("a", title="Official Website") # Guess
        if not website_link_tag: # Try another common pattern
             website_link_tag = soup.find("a", string=lambda t: t and "official website" in t.lower())

        if website_link_tag and website_link_tag.has_attr("href"):
            artist_data["official_website_url"] = website_link_tag["href"]

        return artist_data
    except Exception as e:
        print(f"Error parsing artist {file_path}: {e}")
        return {"file_path": file_path, "error": str(e)}

def parse_subgenre_definitions(file_path):
    """
    Parses the subgenre definitions text file.
    Assumes each subgenre starts with a title in ALL CAPS,
    followed by descriptive paragraphs.
    """
    subgenres = {}
    current_subgenre_title = None
    current_definition_lines = []
    in_definition_body = False

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped_line = line.strip()

            if not stripped_line: # Skip empty lines
                continue

            # Check for a new subgenre title (ALL CAPS, not a footnote, not the metadata lines)
            if stripped_line.isupper() and len(stripped_line) > 1 and \
               "FOOTNOTE:" not in stripped_line and \
               "A PROGRESSIVE ROCK SUB-GENRE" not in stripped_line.upper() and \
               "FROM PROGARCHIVES.COM" not in stripped_line.upper():
                
                if current_subgenre_title and current_definition_lines:
                    # Save the previous subgenre's definition
                    definition = "\n".join(current_definition_lines).strip()
                    subgenres[current_subgenre_title] = definition
                
                current_subgenre_title = stripped_line
                current_definition_lines = []
                in_definition_body = False # Reset for the new subgenre
                # print(f"Found title: {current_subgenre_title}") # for debugging
                continue

            if current_subgenre_title:
                # Skip the standard header lines after a title is found
                if not in_definition_body:
                    if stripped_line.lower() == "a progressive rock sub-genre" or \
                       stripped_line.lower() == "from progarchives.com, the ultimate progressive rock music website" or \
                       stripped_line.lower() == f"{current_subgenre_title.lower()} definition":
                        # print(f"Skipping header: {stripped_line}") # for debugging
                        continue
                    else:
                        # First line of the actual definition body
                        in_definition_body = True
                        # print(f"Starting definition body for {current_subgenre_title} with: {stripped_line}") # for debugging
                
                if in_definition_body:
                    # Stop if we hit a footnote for the current subgenre's definition body
                    if "FOOTNOTE:" in stripped_line:
                        # Save the current definition before processing the footnote or next title
                        if current_subgenre_title and current_definition_lines:
                            definition = "\n".join(current_definition_lines).strip()
                            subgenres[current_subgenre_title] = definition
                            # print(f"Saved definition for {current_subgenre_title} before footnote.") # for debugging
                        current_subgenre_title = None # Reset to avoid appending footnote to this definition
                        in_definition_body = False
                        continue # Skip the footnote line itself from being added to any definition
                    
                    current_definition_lines.append(stripped_line)
        
        # Save the last subgenre's definition
        if current_subgenre_title and current_definition_lines:
            definition = "\n".join(current_definition_lines).strip()
            subgenres[current_subgenre_title] = definition
            # print(f"Saved last definition: {current_subgenre_title}") # for debugging
            
    return subgenres

# --- Main Execution ---
def main():
    all_albums_data = []
    all_artists_data = {} # Use dict to store by URL to avoid duplicates
    processed_artist_urls = set()

    # 1. Identify and Parse Album Files
    print("\n--- Starting Album Parsing ---")
    album_files_found = 0
    for item in os.listdir(ALBUM_FILES_PATH):
        if item.startswith("album") and item.endswith(".html"):
            album_files_found +=1
            file_path = os.path.join(ALBUM_FILES_PATH, item)
            album_data = parse_album_file(file_path)
            if album_data and "error" not in album_data:
                all_albums_data.append(album_data)
                # Queue artist page for parsing if not already processed
                artist_url = album_data.get("artist_page_url_relative")
                if artist_url and artist_url not in processed_artist_urls:
                    # Construct full path for artist HTML file
                    # Assuming artist URLs are relative to ALBUM_FILES_PATH
                    artist_file_path = os.path.join(ALBUM_FILES_PATH, artist_url)
                    if os.path.exists(artist_file_path):
                         # Add to a temporary list to parse after all albums
                        pass # Will be handled in the artist parsing section
                    else:
                        print(f"Artist file not found: {artist_file_path} (linked from {item})")

    print(f"--- Finished Album Parsing. Found {album_files_found} album files. Parsed {len(all_albums_data)} successfully. ---")


    # 2. Process Artist Information (compile unique list first)
    print("\n--- Starting Artist Parsing ---")
    artist_urls_to_parse = set()
    for album in all_albums_data:
        artist_url = album.get("artist_page_url_relative")
        if artist_url:
            artist_urls_to_parse.add(artist_url)

    parsed_artist_count = 0
    for artist_url_rel in artist_urls_to_parse:
        if artist_url_rel not in processed_artist_urls:
            artist_file_path = os.path.join(ALBUM_FILES_PATH, artist_url_rel)
            if os.path.exists(artist_file_path):
                artist_data = parse_artist_file(artist_file_path)
                if artist_data and "error" not in artist_data:
                    # Use the relative URL as a key to avoid duplicates if multiple albums point to same artist
                    all_artists_data[artist_url_rel] = artist_data
                    parsed_artist_count +=1
                processed_artist_urls.add(artist_url_rel)
            else:
                print(f"Artist file not found during dedicated artist parsing: {artist_file_path}")
    print(f"--- Finished Artist Parsing. Found {len(artist_urls_to_parse)} unique artist URLs. Parsed {parsed_artist_count} successfully. ---")


    # 3. Process Subgenre Definitions
    print("\n--- Starting Subgenre Parsing ---")
    subgenres_data = []
    if os.path.exists(SUBGENRE_DEF_PATH):
        subgenres_data = parse_subgenre_definitions(SUBGENRE_DEF_PATH)
        print(f"--- Finished Subgenre Parsing. Found {len(subgenres_data)} subgenres. ---")
    else:
        print(f"Subgenre definition file not found: {SUBGENRE_DEF_PATH}")


    # 4. Initial Data Storage
    print("\n--- Saving Data to JSON ---")
    try:
        with open(ALBUMS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(all_albums_data, f, indent=4)
        print(f"Successfully saved albums to {ALBUMS_JSON_PATH}")
    except Exception as e:
        print(f"Error saving albums JSON: {e}")

    try:
        # Convert dict values to list for JSON output
        with open(ARTISTS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(list(all_artists_data.values()), f, indent=4)
        print(f"Successfully saved artists to {ARTISTS_JSON_PATH}")
    except Exception as e:
        print(f"Error saving artists JSON: {e}")

    try:
        with open(SUBGENRES_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(subgenres_data, f, indent=4)
        print(f"Successfully saved subgenres to {SUBGENRES_JSON_PATH}")
    except Exception as e:
        print(f"Error saving subgenres JSON: {e}")

    print("\n--- Data Extraction Script Finished ---")

if __name__ == "__main__":
    # Ensure BeautifulSoup is installed
    try:
        import bs4
    except ImportError:
        print("BeautifulSoup4 is not installed. Please install it: pip install beautifulsoup4")
        exit()
    main()
