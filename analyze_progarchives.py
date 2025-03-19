#!/usr/bin/env python
"""Script to analyze ProgArchives HTML structure for updating scraper."""
import requests
import json
import re
import time
from pathlib import Path
from bs4 import BeautifulSoup

def fetch_url(url):
    """Fetch URL with appropriate headers and return HTML content."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'https://www.progarchives.com/'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(f"Successfully fetched {url} (HTTP {response.status_code})")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def save_html(html, filename):
    """Save HTML content to a file."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Saved HTML to {filename}")

def analyze_bands_alpha(html):
    """Analyze bands alphabetical listing page structure."""
    results = {}
    soup = BeautifulSoup(html, 'html.parser')
    
    print("\n=== Bands Alpha Page Analysis ===")
    
    # Find all artist links
    artist_links = soup.select('a[href*="artist.asp"]')
    results["artist_links_count"] = len(artist_links)
    print(f"Found {len(artist_links)} artist links")
    
    # Find the container structure
    containers = []
    for container in soup.select('div.grid-container'):
        artist_links_in_container = container.select('a[href*="artist.asp"]')
        if artist_links_in_container:
            containers.append({
                "tag": container.name,
                "class": container.get('class'),
                "id": container.get('id'),
                "link_count": len(artist_links_in_container)
            })
            print(f"Container: {container.name}, class={container.get('class')}, contains {len(artist_links_in_container)} artist links")
    
    results["containers"] = containers
    
    # Sample some artist links
    sample_artists = []
    for i, link in enumerate(artist_links[:5]):
        artist = {
            "name": link.get_text().strip(),
            "url": link.get('href'),
            "parent_element": {
                "tag": link.parent.name,
                "class": link.parent.get('class'),
            }
        }
        sample_artists.append(artist)
        print(f"Artist {i+1}: {artist['name']} -> {artist['url']}")
    
    results["sample_artists"] = sample_artists
    
    # Check for pagination
    pagination = soup.select('.pagination, .pages')
    results["has_pagination"] = bool(pagination)
    if pagination:
        print(f"Found pagination element: {pagination[0].name}, class={pagination[0].get('class')}")
    
    return results

def analyze_artist_page(html):
    """Analyze artist page structure."""
    results = {}
    soup = BeautifulSoup(html, 'html.parser')
    
    print("\n=== Artist Page Analysis ===")
    
    # Find artist name
    h1_elements = soup.find_all('h1')
    if h1_elements:
        results["artist_name"] = h1_elements[0].get_text().strip()
        print(f"Artist name: {results['artist_name']}")
        print(f"H1 element: tag={h1_elements[0].name}, class={h1_elements[0].get('class')}")
    
    # Find genre information
    genre_elements = soup.select('.genresubtitle, .genre-title, .artist-genre')
    if genre_elements:
        results["genre"] = genre_elements[0].get_text().strip()
        print(f"Genre: {results['genre']} (element: {genre_elements[0].name}, class={genre_elements[0].get('class')})")
    
    # Find country information
    country_elements = soup.select('.countrysubtitle, .country, .artist-country')
    if country_elements:
        results["country"] = country_elements[0].get_text().strip()
        print(f"Country: {results['country']} (element: {country_elements[0].name}, class={country_elements[0].get('class')})")
    
    # Find albums section
    albums_section = soup.select('.artist-discography-td')
    results["albums_count"] = len(albums_section)
    print(f"Found {len(albums_section)} album entries")
    
    # Sample some albums
    sample_albums = []
    for i, album in enumerate(albums_section[:3]):
        link = album.select_one('a[href*="album.asp"]')
        if link:
            album_info = {
                "title": link.get_text().strip(),
                "url": link.get('href'),
                "container_class": album.get('class'),
                "container_tag": album.name
            }
            sample_albums.append(album_info)
            print(f"Album {i+1}: {album_info['title']} -> {album_info['url']}")
    
    results["sample_albums"] = sample_albums
    
    return results

def analyze_album_page(html):
    """Analyze album page structure."""
    results = {}
    soup = BeautifulSoup(html, 'html.parser')
    
    print("\n=== Album Page Analysis ===")
    
    # Find album title
    album_title_elements = soup.select('.albumtitle')
    if album_title_elements:
        results["album_title"] = album_title_elements[0].get_text().strip()
        print(f"Album title: {results['album_title']} (element: {album_title_elements[0].name}, class={album_title_elements[0].get('class')})")
    
    # Find artist name
    artist_elements = soup.select('.albumPerformer a')
    if artist_elements:
        results["artist"] = artist_elements[0].get_text().strip()
        results["artist_url"] = artist_elements[0].get('href')
        print(f"Artist: {results['artist']} -> {results['artist_url']}")
    
    # Find album cover
    cover_img = soup.select_one('.albumcover img')
    if cover_img and cover_img.get('src'):
        results["cover_image"] = cover_img.get('src')
        print(f"Album cover: {results['cover_image']}")
    
    # Find album info section 
    info_elements = soup.select('.albuminfo')
    if info_elements:
        print(f"Album info section: tag={info_elements[0].name}, class={info_elements[0].get('class')}")
        
        # Extract structured info
        genre_elem = info_elements[0].select_one('.detailTagGenre')
        year_elem = info_elements[0].select_one('.detailPressLabelYear')
        type_elem = info_elements[0].select_one('.detailFormat')
        
        if genre_elem:
            results["genre"] = genre_elem.get_text().strip()
            print(f"Genre: {results['genre']}")
            
        if year_elem:
            results["year"] = year_elem.get_text().strip()
            print(f"Year: {results['year']}")
            
        if type_elem:
            results["type"] = type_elem.get_text().strip()
            print(f"Type: {results['type']}")
    
    # Find tracklist
    tracklist = soup.select('.tracklist')
    if tracklist:
        print(f"Found tracklist: tag={tracklist[0].name}, class={tracklist[0].get('class')}")
        track_items = tracklist[0].select('li')
        results["tracks_count"] = len(track_items)
        print(f"Found {len(track_items)} tracks")
        
        # Sample some tracks
        sample_tracks = []
        for i, track in enumerate(track_items[:3]):
            track_info = {"text": track.get_text().strip()}
            sample_tracks.append(track_info)
            print(f"Track {i+1}: {track_info['text']}")
        
        results["sample_tracks"] = sample_tracks
    
    # Find ratings section
    ratings = soup.select('.albumratings')
    if ratings:
        rating_text = ratings[0].get_text()
        rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
        if rating_match:
            results["rating"] = float(rating_match.group(1))
            print(f"Album rating: {results['rating']}")
    
    return results

def analyze_reviews_page(html):
    """Analyze album reviews page structure."""
    results = {}
    soup = BeautifulSoup(html, 'html.parser')
    
    print("\n=== Album Reviews Page Analysis ===")
    
    # Find album title
    title_elements = soup.select('.albumtitle')
    if title_elements:
        results["album_title"] = title_elements[0].get_text().strip()
        print(f"Album title: {results['album_title']}")
    
    # Find artist name
    artist_elements = soup.select('.albumPerformer a')
    if artist_elements:
        results["artist"] = artist_elements[0].get_text().strip()
        print(f"Artist: {results['artist']}")
    
    # Find reviews
    review_elements = soup.select('.reviewtext')
    results["reviews_count"] = len(review_elements)
    print(f"Found {len(review_elements)} reviews")
    
    # Sample some reviews
    sample_reviews = []
    for i, review in enumerate(review_elements[:2]):  # Just first 2 reviews as samples
        reviewer_elem = review.select_one('.username')
        rating_elem = review.select_one('.reviewrating')
        date_elem = review.select_one('.reviewdate')
        text_elem = review.select_one('.reviewcomment')
        
        review_info = {}
        
        if reviewer_elem:
            review_info["reviewer"] = reviewer_elem.get_text().strip()
            print(f"Reviewer {i+1}: {review_info['reviewer']}")
            
        if rating_elem:
            rating_text = rating_elem.get_text()
            rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
            if rating_match:
                review_info["rating"] = float(rating_match.group(1))
                print(f"Rating: {review_info['rating']}")
        
        if date_elem:
            review_info["date"] = date_elem.get_text().strip()
            print(f"Date: {review_info['date']}")
        
        if text_elem:
            text = text_elem.get_text().strip()
            review_info["text_preview"] = text[:100] + "..." if len(text) > 100 else text
            print(f"Text preview: {review_info['text_preview']}")
        
        sample_reviews.append(review_info)
    
    results["sample_reviews"] = sample_reviews
    
    return results

def main():
    """Main function to analyze all target pages."""
    pages = [
        ('bands-alpha', 'https://www.progarchives.com/bands-alpha.asp?letter=A'),
        ('artist', 'https://www.progarchives.com/artist.asp?id=3095'),  # NE ZHDALI
        ('album', 'https://www.progarchives.com/album.asp?id=42765'),   # The Dillinger Escape Plan - Calculating Infinity
        ('album-reviews', 'https://www.progarchives.com/album-reviews.asp?id=42765')
    ]
    
    results = {}
    
    for page_type, url in pages:
        print(f"\nFetching {page_type} page: {url}")
        html = fetch_url(url)
        
        if html:
            # Save HTML for reference
            filename = f"sample_{page_type}.html"
            save_html(html, filename)
            
            # Analyze specific page type
            if page_type == 'bands-alpha':
                results[page_type] = analyze_bands_alpha(html)
            elif page_type == 'artist':
                results[page_type] = analyze_artist_page(html)
            elif page_type == 'album':
                results[page_type] = analyze_album_page(html)
            elif page_type == 'album-reviews':
                results[page_type] = analyze_reviews_page(html)
            
            # Save results to JSON
            with open('progarchives_output.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            print("Updated analysis results saved to progarchives_output.json")
        
        # Be kind to the server
        time.sleep(5)

if __name__ == "__main__":
    main()