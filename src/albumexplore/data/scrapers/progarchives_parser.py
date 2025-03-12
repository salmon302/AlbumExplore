"""Scraper for ProgArchives.com with ethical rate limiting."""
// ...existing code...

    def get_band_details(self, band_url: str) -> Dict:
        """Get detailed information about a band."""
        logger.info(f"Getting details for band at {band_url}")
        content = self.get_page(band_url)
        soup = BeautifulSoup(content, 'html.parser')
        
        try:
            details = {'description': '', 'formed_info': '', 'albums': []}
            
            # Get band info from the profile section
            profile_table = soup.find('table', {'class': 'artist_description'})
            if profile_table:
                # Find description
                desc_td = profile_table.find('td', {'style': 'text-align:justify'})
                if desc_td:
                    details['description'] = self._clean_text(desc_td.text)
                    logger.debug("Found band description")
                
                # Find formation info
                formed_td = profile_table.find('td', text=re.compile(r'Formed', re.I))
                if formed_td:
                    details['formed_info'] = self._clean_text(formed_td.text)
                    logger.debug(f"Found formation info: {details['formed_info']}")
            
            # Get album list - need to find the discography section
            discography_table = soup.find('table', {'class': 'discog'})
            if discography_table:
                logger.info("Found discography table")
                # Process each album row
                for row in discography_table.find_all('tr')[1:]:  # Skip header row
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 3:  # Need title, type/year, rating cells
                            continue
                        
                        # Get album link and title
                        title_cell = cells[0]
                        album_link = title_cell.find('a', href=re.compile(r'album\.asp'))
                        if not album_link:
                            continue

                        # Get album info (type and year)
                        info_text = cells[1].get_text(strip=True)
                        
                        # Parse record type
                        record_type = None
                        for rt in self.valid_record_types:
                            if rt.lower() in info_text.lower():
                                record_type = rt
                                break
                        
                        if not record_type:
                            continue
                        
                        # Parse year
                        year_match = re.search(r'\b(19|20)\d{2}\b', info_text)
                        if not year_match:
                            continue
                        
                        year = int(year_match.group())
                        
                        # Get rating
                        rating = None
                        rating_cell = cells[2]
                        rating_text = rating_cell.get_text(strip=True)
                        if rating_text:
                            try:
                                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                                if rating_match:
                                    rating = float(rating_match.group(1))
                            except ValueError:
                                pass
                        
                        album_url = album_link['href']
                        if not album_url.startswith('http'):
                            album_url = self.base_url + '/' + album_url
                        
                        album = {
                            'title': album_link.text.strip(),
                            'url': album_url,
                            'record_type': record_type,
                            'year': year,
                            'rating': rating
                        }
                        
                        logger.info(f"Found album: {album['title']} ({album['year']}) - {record_type}")
                        details['albums'].append(album)
                        
                    except Exception as e:
                        logger.error(f"Error parsing album row: {str(e)}")
                        continue
            else:
                logger.warning("Could not find discography table")
            
            return details
            
        except Exception as e:
            logger.error(f"Error parsing band page {band_url}: {str(e)}")
            return {'error': str(e)}

    def get_album_details(self, album_url: str) -> Dict:
        """Get detailed information about an album."""
        logger.info(f"Getting details for album at {album_url}")
        content = self.get_page(album_url)
        soup = BeautifulSoup(content, 'html.parser')
        
        try:
            details = {'description': '', 'lineup': []}
            
            # Get album info from the main table
            album_table = soup.find('table', {'class': 'album_description'})
            if album_table:
                # Get album description
                desc_td = album_table.find('td', {'style': 'text-align:justify'})
                if desc_td:
                    details['description'] = self._clean_text(desc_td.text)
                    logger.debug("Found album description")
                
                # Get lineup information - it's typically in a section after "Line-up"
                lineup_td = album_table.find('td', text=re.compile(r'Line-up', re.I))
                if lineup_td:
                    current_role = None
                    # Look at next td elements for lineup info
                    for td in lineup_td.find_next_siblings('td'):
                        text = td.get_text(strip=True)
                        if not text:
                            continue
                        
                        if text.endswith(':'):
                            current_role = text[:-1].strip()
                        elif current_role:
                            details['lineup'].append({
                                'role': current_role,
                                'name': text.strip()
                            })
                    
                    logger.debug(f"Found {len(details['lineup'])} lineup entries")
            
            return details
            
        except Exception as e:
            logger.error(f"Error parsing album page {album_url}: {str(e)}")
            return {'error': str(e)}