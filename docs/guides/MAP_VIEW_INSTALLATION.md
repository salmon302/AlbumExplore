# World Map View Installation Guide

## Overview
The World Map View has been created as a stub implementation. To fully enable it, you'll need to install additional dependencies.

## Required Dependencies

Add the following to your `requirements.txt`:

```
folium>=0.14.0
PyQt6-WebEngine>=6.4.0
```

## Installation

### Option 1: Using pip directly
```bash
pip install folium PyQt6-WebEngine
```

### Option 2: Using requirements.txt
Add the dependencies above to your requirements.txt, then run:
```bash
pip install -r requirements.txt
```

## Integrating the Map View

To add the Map View to your application:

### 1. Update `app.py`

Add the import:
```python
from .views.world_map_view import WorldMapView
```

Initialize the view:
```python
self.map_view = WorldMapView()
```

Add to stacked widget:
```python
self.stacked_widget.addWidget(self.map_view)
```

Add menu action:
```python
map_action = QAction("&Map View", self)
map_action.triggered.connect(lambda: self._handle_view_switch(ViewType.MAP))
map_action.setEnabled(False)  # Disabled until data is loaded
view_menu.addAction(map_action)
self.map_action = map_action
```

Enable after data load:
```python
self.map_action.setEnabled(True)
```

### 2. Update `_update_active_view` method

Add the map view case:
```python
elif current_view_type == ViewType.MAP:
    graphics_logger.info(f"AlbumExplorer: Setting MapView. Data type: {render_data.get('type')}")
    self.map_view.update_data(render_data)
    self.stacked_widget.setCurrentWidget(self.map_view)
```

### 3. Ensure location data is included in nodes

The map view expects nodes to have location data. Ensure your data processing includes:
```python
node_data = {
    'id': album.id,
    'label': f"{album.pa_artist_name_on_album} - {album.title}",
    'artist': album.pa_artist_name_on_album,
    'year': album.release_year,
    'genre': album.primary_genre,  # or however you determine this
    'tags': [tag.name for tag in album.tags],
    'location': album.pa_country_of_origin,  # KEY: This field is required
    'data': {
        'artist': album.pa_artist_name_on_album,
        'year': album.release_year,
        'genre': album.primary_genre,
        'tags': [tag.name for tag in album.tags],
        'location': album.pa_country_of_origin
    }
}
```

## Features

Once installed, the Map View provides:

1. **Three View Modes**:
   - Individual Markers: Each location shows as a separate marker
   - Clustered Markers: Automatically clusters nearby markers at low zoom
   - Heatmap: Shows density of albums across regions

2. **Filtering**:
   - Filter by genre
   - Filter by year range (from/to)

3. **Interactive Elements**:
   - Click markers to see album details
   - Hover for quick location info
   - Statistics panel showing album count and countries

4. **Performance**:
   - Handles 17k+ albums efficiently
   - Marker clustering prevents overcrowding
   - Lazy loading of map tiles

## Extending the Location Cache

The `LocationCache` class in `world_map_view.py` contains a basic set of country coordinates. To improve geocoding accuracy:

### Option A: Add more locations manually
Edit the `_load_default_locations` method to add more countries/regions.

### Option B: Use an external geocoding service
Replace the `get_coordinates` method to use:
- Google Maps Geocoding API
- OpenStreetMap Nominatim
- Geopy library

Example with Geopy:
```python
from geopy.geocoders import Nominatim

def get_coordinates(self, location: str) -> Optional[Tuple[float, float]]:
    if location in self._cache:
        return self._cache[location]
    
    try:
        geolocator = Nominatim(user_agent="albumexplore")
        result = geolocator.geocode(location)
        if result:
            coords = (result.latitude, result.longitude)
            self._cache[location] = coords
            return coords
    except Exception as e:
        graphics_logger.error(f"Geocoding failed for {location}: {e}")
    
    return None
```

### Option C: Pre-compute and cache all locations
Create a script to geocode all unique locations once and save to a JSON file:

```python
import json
from collections import Counter

# Get all unique locations from database
locations = set()
for album in session.query(Album).all():
    if album.pa_country_of_origin:
        locations.add(album.pa_country_of_origin)

# Geocode and save
geocoded = {}
for location in locations:
    coords = geocode(location)  # Your geocoding function
    if coords:
        geocoded[location] = coords

with open('location_cache.json', 'w') as f:
    json.dump(geocoded, f, indent=2)
```

Then load in `LocationCache.__init__`:
```python
def __init__(self):
    self._cache = {}
    cache_file = Path(__file__).parent / 'location_cache.json'
    if cache_file.exists():
        with open(cache_file) as f:
            self._cache = json.load(f)
    else:
        self._load_default_locations()
```

## Troubleshooting

### Map doesn't load
- Check that PyQt6-WebEngine is installed correctly
- Verify that temp files can be created (check permissions)
- Look for errors in the graphics logger output

### No markers appear
- Verify that album data includes 'location' field
- Check that locations are being geocoded (add debug logging)
- Ensure filtered album count is > 0

### Performance issues
- Use "Clusters" view mode for large datasets
- Reduce the year range filter
- Filter by specific genre

## Next Steps

1. Install the dependencies
2. Integrate into app.py as described above
3. Test with your album data
4. Extend the location cache for better coverage
5. Consider adding more features:
   - Click marker to filter main table view
   - Show album art in popups
   - Export map as PNG/PDF
   - Save/load map views
   - Custom base map tiles (satellite, terrain, etc.)

Enjoy exploring your album collection geographically! 🗺️🎵
