"""World Map visualization view for geographic album distribution."""
from typing import Dict, Any, List, Optional, Set, Tuple
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QComboBox, QCheckBox, QSpinBox, QGroupBox)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, pyqtSignal
import folium
from folium.plugins import MarkerCluster, HeatMap
import tempfile
import os
from pathlib import Path

from .base_view import BaseView
from albumexplore.visualization.state import ViewType
from albumexplore.gui.gui_logging import graphics_logger


class LocationCache:
    """Cache for geocoded locations."""
    
    def __init__(self):
        self._cache: Dict[str, Tuple[float, float]] = {}
        self._load_default_locations()
    
    def _load_default_locations(self):
        """Load known country/region coordinates."""
        # Countries
        self._cache.update({
            "United States": (37.0902, -95.7129),
            "US": (37.0902, -95.7129),
            "United Kingdom": (55.3781, -3.4360),
            "UK": (55.3781, -3.4360),
            "Canada": (56.1304, -106.3468),
            "Germany": (51.1657, 10.4515),
            "France": (46.2276, 2.2137),
            "Italy": (41.8719, 12.5674),
            "Netherlands": (52.1326, 5.2913),
            "Sweden": (60.1282, 18.6435),
            "Norway": (60.4720, 8.4689),
            "Japan": (36.2048, 138.2529),
            "Australia": (-25.2744, 133.7751),
            "Brazil": (-14.2350, -51.9253),
            "Mexico": (23.6345, -102.5528),
            "Spain": (40.4637, -3.7492),
            "Poland": (51.9194, 19.1451),
            "Russia": (61.5240, 105.3188),
            "Argentina": (-38.4161, -63.6167),
            "Greece": (39.0742, 21.8243),
            "Switzerland": (46.8182, 8.2275),
            "Belgium": (50.5039, 4.4699),
            "Austria": (47.5162, 14.5501),
            "Denmark": (56.2639, 9.5018),
            "Finland": (61.9241, 25.7482),
            "Portugal": (39.3999, -8.2245),
            "Czech Republic": (49.8175, 15.4730),
            "Ireland": (53.4129, -8.2439),
            "New Zealand": (-40.9006, 174.8860),
            "Chile": (-35.6751, -71.5430),
            "Israel": (31.0461, 34.8516),
            "Turkey": (38.9637, 35.2433),
            "Iceland": (64.9631, -19.0208),
            "Scotland": (56.4907, -4.2026),
            "Wales": (52.1307, -3.7837),
            "Indonesia": (-0.7893, 113.9213),
            "South Africa": (-30.5595, 22.9375),
            "Ukraine": (48.3794, 31.1656),
            "Jordan": (30.5852, 36.2384),
            "Mauritania": (21.0079, -10.9408),
            "Serbia": (44.0165, 21.0059),
            "Hungary": (47.1625, 19.5033),
            "Monaco": (43.7384, 7.4246),
        })
        
        # Major US cities
        self._cache.update({
            "New York, NY": (40.7128, -74.0060),
            "Brooklyn, NY": (40.6782, -73.9442),
            "Los Angeles, CA": (34.0522, -118.2437),
            "Chicago, IL": (41.8781, -87.6298),
            "San Francisco, CA": (37.7749, -122.4194),
            "Boston, MA": (42.3601, -71.0589),
            "Seattle, WA": (47.6062, -122.3321),
            "Portland, OR": (45.5152, -122.6784),
            "Philadelphia, PA": (39.9526, -75.1652),
            "Nashville, TN": (36.1627, -86.7816),
            "Denver, CO": (39.7392, -104.9903),
            "Minneapolis, MN": (44.9778, -93.2650),
            "Dallas, TX": (32.7767, -96.7970),
            "Richmond, VA": (37.5407, -77.4360),
            "Buffalo, NY": (42.8864, -78.8784),
            "Detroit, MI": (42.3314, -83.0458),
            "Queens, NY": (40.7282, -73.7949),
            "Oakland, CA": (37.8044, -122.2712),
            "San Diego, CA": (32.7157, -117.1611),
            "Atlanta, GA": (33.7490, -84.3880),
            "New Jersey, NJ": (40.0583, -74.4057),
            "Rochester, NY": (43.1566, -77.6088),
            "Pittsburgh, PA": (40.4406, -79.9959),
            "Louisville, KY": (38.2527, -85.7585),
            "Bloomington, IN": (39.1653, -86.5264),
            "Jersey City, NJ": (40.7178, -74.0431),
            "Santa Cruz, CA": (36.9741, -122.0308),
            "Lincoln, NE": (40.8136, -96.7026),
            "Gainesville, FL": (29.6516, -82.3248),
            "Raleigh, NC": (35.7796, -78.6382),
            "Columbus, OH": (39.9612, -82.9988),
            "St. Louis, MO": (38.6270, -90.1994),
            "New Haven, CT": (41.3083, -72.9279),
            "New Brunswick, NJ": (40.4862, -74.4518),
            "Dayton, OH": (39.7589, -84.1916),
            "Hammonton, NJ": (39.6368, -74.8021),
            "Teaneck, NJ": (40.8976, -74.0160),
            "Durham, NC": (35.9940, -78.8986),
            "Denton, TX": (33.2148, -97.1331),
            "Ripton, VT": (43.9995, -73.0395),
            "Nazareth, PA": (40.7401, -75.3096),
            "Carrboro, NC": (35.9101, -79.0753),
            "Harrisonburg, VA": (38.4496, -78.8689),
            "Oklahoma City, OK": (35.4676, -97.5164),
            "Memphis, TN": (35.1495, -90.0490),
            "Norfolk, VA": (36.8508, -76.2859),
            "Northampton, MA": (42.3251, -72.6410),
            "Little Rock, AR": (34.7465, -92.2896),
            "Santa Margarita, CA": (35.3911, -120.6088),
            "Hartford, CT": (41.7658, -72.6734),
            "Kansas City, MO": (39.0997, -94.5786),
            "Athens, GA": (33.9519, -83.3576),
            "Milwaukee, WI": (43.0389, -87.9065),
            "Houghton, MI": (47.1186, -88.5694),
            "Cooperstown, NY": (42.7006, -74.9244),
            "Ithaca, NY": (42.4430, -76.5019),
            "St. Paul, MN": (44.9537, -93.0900),
            "Lawrence, KS": (38.9717, -95.2353),
            "Muscle Shoals, AL": (34.7448, -87.6675),
            "Ocala, FL": (29.1872, -82.1401),
            "Orlando, FL": (28.5383, -81.3792),
            "California, CA": (36.7783, -119.4179),
            "Maine, ME": (45.2538, -69.4455),
        })
        
        # UK cities
        self._cache.update({
            "London, UK": (51.5074, -0.1278),
            "Manchester, UK": (53.4808, -2.2426),
            "Birmingham, UK": (52.4862, -1.8904),
            "Leeds, UK": (53.8008, -1.5491),
            "Glasgow, Scotland": (55.8642, -4.2518),
            "Brighton, UK": (50.8225, -0.1372),
            "Oxford, UK": (51.7520, -1.2577),
            "Sheffield, UK": (53.3811, -1.4701),
            "Bristol, UK": (51.4545, -2.5879),
            "Cambridge, UK": (52.2053, 0.1218),
            "Scunthorpe, UK": (53.5905, -0.6500),
            "Colchester, UK": (51.8959, 0.8919),
            "Huddersfield, UK": (53.6458, -1.7850),
            "Whitby, UK": (54.4858, -0.6206),
            "Newcastle, UK": (54.9783, -1.6178),
            "Portsmouth, UK": (50.8198, -1.0880),
            "Bracknell, UK": (51.4167, -0.7500),
            "Saint Leonards, UK": (50.8550, 0.5720),
            "Norwich, UK": (52.6309, 1.2974),
            "Worcester, UK": (52.1936, -2.2210),
            "Dundee, Scotland": (56.4620, -2.9707),
            "Cardiff, Wales": (51.4816, -3.1791),
        })
        
        # Canadian cities
        self._cache.update({
            "Toronto, Canada": (43.6532, -79.3832),
            "Montreal, Canada": (45.5017, -73.5673),
            "Montréal, Canada": (45.5017, -73.5673),
            "Vancouver, Canada": (49.2827, -123.1207),
            "Calgary, Canada": (51.0447, -114.0719),
            "Ottawa, Canada": (45.4215, -75.6972),
            "Winnipeg, Canada": (49.8951, -97.1384),
            "Halifax, Canada": (44.6488, -63.5752),
            "Oakville, Canada": (43.4675, -79.6877),
            "Nanaimo, Canada": (49.1659, -123.9401),
            "Edmonton, Canada": (53.5461, -113.4938),
        })
        
        # European cities
        self._cache.update({
            "Paris, France": (48.8566, 2.3522),
            "Berlin, Germany": (52.5200, 13.4050),
            "Hamburg, Germany": (53.5511, 9.9937),
            "Frankfurt, Germany": (50.1109, 8.6821),
            "Cologne, Germany": (50.9375, 6.9603),
            "Köln, Germany": (50.9375, 6.9603),
            "Halle, Germany": (51.4969, 11.9688),
            "Bielefeld, Germany": (52.0302, 8.5325),
            "Oslo, Norway": (59.9139, 10.7522),
            "Bergen, Norway": (60.3913, 5.3221),
            "Egersund, Norway": (58.4510, 6.0007),
            "Tønsberg, Norway": (59.2673, 10.4079),
            "Stockholm, Sweden": (59.3293, 18.0686),
            "Gothenburg, Sweden": (57.7089, 11.9746),
            "Örebro, Sweden": (59.2753, 15.2134),
            "Copenhagen, Denmark": (55.6761, 12.5683),
            "Helsinki, Finland": (60.1695, 24.9354),
            "Rovaniemi, Finland": (66.5039, 25.7294),
            "Tampere, Finland": (61.4978, 23.7610),
            "Kuopio, Finland": (62.8924, 27.6782),
            "Reykjavík, Iceland": (64.1466, -21.9426),
            "Reykjavik, Iceland": (64.1466, -21.9426),
            "Grindavík, Iceland": (63.8424, -22.4338),
            "Dublin, Ireland": (53.3498, -6.2603),
            "Cork, Ireland": (51.8985, -8.4756),
            "Galway, Ireland": (53.2707, -9.0568),
            "Rome, Italy": (41.9028, 12.4964),
            "Bologna, Italy": (44.4949, 11.3426),
            "Padua, Italy": (45.4064, 11.8768),
            "Cagliari, Italy": (39.2238, 9.1217),
            "Iglesias, Italy": (39.3106, 8.5372),
            "Fossano, Italy": (44.5500, 7.7233),
            "Trieste, Italy": (45.6495, 13.7768),
            "Amsterdam, Netherlands": (52.3676, 4.9041),
            "Brussels, Belgium": (50.8476, 4.3572),
            "Ghent, Belgium": (51.0543, 3.7174),
            "Liège, Belgium": (50.6326, 5.5797),
            "Bern, Switzerland": (46.9480, 7.4474),
            "Geneva, Switzerland": (46.2044, 6.1432),
            "Genève, Switzerland": (46.2044, 6.1432),
            "Schwyz, Switzerland": (47.0207, 8.6531),
            "Madrid, Spain": (40.4168, -3.7038),
            "Barcelona, Spain": (41.3874, 2.1686),
            "Porto, Portugal": (41.1579, -8.6291),
            "Coja, Portugal": (40.2833, -8.1667),
            "Athens, Greece": (37.9838, 23.7275),
            "Warszawa, Poland": (52.2297, 21.0122),
            "Gdynia, Poland": (54.5189, 18.5305),
            "Budapest, Hungary": (47.4979, 19.0402),
            "Innsbruck, Austria": (47.2692, 11.4041),
            "Angers, France": (47.4784, -0.5632),
            "Toulouse, France": (43.6047, 1.4442),
            "Toulon, France": (43.1242, 5.9280),
            "Rouen, France": (49.4432, 1.0993),
            "Lyon, France": (45.7640, 4.8357),
            "Montpellier, France": (43.6108, 3.8767),
            "Bordeaux, France": (44.8378, -0.5792),
            "Bergerac, France": (44.8528, 0.4831),
            "Kyiv, Ukraine": (50.4501, 30.5234),
            "Belgrade, Serbia": (44.7866, 20.4489),
            "Amman, Jordan": (31.9454, 35.9284),
        })
        
        # Australian cities
        self._cache.update({
            "Sydney, Australia": (-33.8688, 151.2093),
            "Melbourne, Australia": (-37.8136, 144.9631),
            "Brisbane, Australia": (-27.4698, 153.0251),
            "Perth, Australia": (-31.9505, 115.8605),
            "Hobart, Australia": (-42.8821, 147.3272),
        })
        
        # Asian cities
        self._cache.update({
            "Tokyo, Japan": (35.6762, 139.6503),
            "Osaka, Japan": (34.6937, 135.5023),
        })
        
        # South American cities
        self._cache.update({
            "Buenos Aires, Argentina": (-34.6037, -58.3816),
            "São Paulo, Brazil": (-23.5505, -46.6333),
            "Rio De Janeiro, Brazil": (-22.9068, -43.1729),
        })
        
        # Other international cities
        self._cache.update({
            "Mexico City, Mexico": (19.4326, -99.1332),
            "Monterrey, Mexico": (25.6866, -100.3161),
            "Ensenada, Mexico": (31.8667, -116.6167),
            "Cape Town, South Africa": (-33.9249, 18.4241),
            "Auckland, New Zealand": (-36.8485, 174.7633),
            "Wellington, New Zealand": (-41.2865, 174.7762),
            "Christchurch, New Zealand": (-43.5321, 172.6362),
            "Accra, Ghana": (5.6037, -0.1870),
            "Bangkok, Thailand": (13.7563, 100.5018),
            "Singapore": (1.3521, 103.8198),
            "New Delhi, India": (28.6139, 77.2090),
            "India": (20.5937, 78.9629),
            "Jakarta, Indonesia": (-6.2088, 106.8456),
            "Wenzhou, China": (28.0000, 120.6667),
            "Cairo, Egypt": (30.0444, 31.2357),
            "Beirut, Lebanon": (33.8886, 35.4955),
            "Magangué, Colombia": (9.2417, -74.7544),
            "Rwanda": (-1.9403, 29.8739),
            "Slovenia": (46.1512, 14.9955),
            "Estonia": (58.5953, 25.0136),
            "Cyprus": (35.1264, 33.4299),
            "Slovakia": (48.6690, 19.6990),
            "Colombia": (4.5709, -74.2973),
            "Lebanon": (33.8547, 35.8623),
            "Ghana": (7.9465, -1.0232),
            "Thailand": (15.8700, 100.9925),
            "Egypt": (26.8206, 30.8025),
        })
        
        # Additional European cities from logs
        self._cache.update({
            "Vienna, Austria": (48.2082, 16.3738),
            "Graz, Austria": (47.0707, 15.4395),
            "Uppsala, Sweden": (59.8586, 17.6389),
            "Falun, Sweden": (60.6042, 15.6262),
            "Umeå, Sweden": (63.8258, 20.2630),
            "Malmö, Sweden": (55.6050, 13.0038),
            "Warsaw, Poland": (52.2297, 21.0122),
            "Gdańsk, Poland": (54.3520, 18.6466),
            "Katowice, Poland": (50.2649, 19.0238),
            "Kraków, Poland": (50.0647, 19.9450),
            "Milan, Italy": (45.4642, 9.1900),
            "Milano, Italy": (45.4642, 9.1900),
            "Livorno, Italy": (43.5485, 10.3106),
            "Mores, Italy": (40.5333, 8.8500),
            "Bassano Del Grappa, Italy": (45.7667, 11.7333),
            "Tromsø, Norway": (69.6492, 18.9553),
            "Trondheim, Norway": (63.4305, 10.3951),
            "Haugesund, Norway": (59.4138, 5.2680),
            "Kopervik, Norway": (59.2833, 5.3000),
            "Jyväskylä, Finland": (62.2426, 25.7473),
            "Preston, UK": (53.7632, -2.7031),
            "Watford, UK": (51.6565, -0.3903),
            "Tranmere, UK": (53.3733, -3.0278),
            "Nottingham, UK": (52.9548, -1.1581),
            "Newport, UK": (51.5842, -2.9977),
            "Berkhamsted, UK": (51.7606, -0.5633),
            "Twickenham, UK": (51.4482, -0.3342),
            "Southend, UK": (51.5459, 0.7077),
            "Durham, UK": (54.7753, -1.5849),
            "Hull, UK": (53.7457, -0.3367),
            "Corby, UK": (52.4911, -0.6969),
            "Salisbury, UK": (51.0693, -1.7944),
            "Camden, UK": (51.5390, -0.1426),
            "Lancaster, UK": (54.0465, -2.8010),
            "Luton, UK": (51.8787, -0.4200),
            "Bedford, UK": (52.1360, -0.4667),
            "Bath, UK": (51.3811, -2.3590),
            "Goole, UK": (53.7007, -0.8700),
            "Stourbridge, UK": (52.4569, -2.1486),
            "St. Ives, UK": (50.2109, -5.4803),
            "Southampton, UK": (50.9097, -1.4044),
            "Liverpool, UK": (53.4084, -2.9916),
            "Edinburgh, Scotland": (55.9533, -3.1883),
            "Greenock, Scotland": (55.9486, -4.7647),
            "Swansea, Wales": (51.6214, -3.9436),
            "Machynlleth, Wales": (52.5944, -3.8519),
            "Dundalk, Ireland": (54.0000, -6.4167),
            "Sligo, Ireland": (54.2697, -8.4694),
            "Lisboa, Portugal": (38.7223, -9.1393),
            "Murcia, Spain": (37.9922, -1.1307),
            "Roda De Ter, Spain": (42.0000, 2.3000),
            "Rennes, France": (48.1173, -1.6778),
            "Nancy, France": (48.6921, 6.1844),
            "Nantes, France": (47.2184, -1.5536),
            "Marseille, France": (43.2965, 5.3698),
            "Dresden, Germany": (51.0504, 13.7373),
            "Kiel, Germany": (54.3233, 10.1394),
            "Munich, Germany": (48.1351, 11.5820),
            "Darmstadt, Germany": (49.8728, 8.6512),
            "Kassel, Germany": (51.3127, 9.4797),
            "Kirchen, Germany": (50.8167, 7.8833),
            "Merzig, Germany": (49.4431, 6.6386),
            "Helmbrechts, Germany": (50.2333, 11.7167),
            "Leuven, Belgium": (50.8798, 4.7005),
            "Herzele, Belgium": (50.8833, 3.8833),
            "Antwerp, Belgium": (51.2194, 4.4025),
            "Basel, Switzerland": (47.5596, 7.5886),
            "Lausanne, Switzerland": (46.5197, 6.6323),
            "Bratislava, Slovakia": (48.1486, 17.1077),
            "Ljubljana, Slovenia": (46.0569, 14.5058),
            "Saint Petersburg, Russia": (59.9311, 30.3609),
            "Roden, Netherlands": (53.1333, 6.4333),
            "Arnhem, Netherlands": (51.9851, 5.8987),
            "Oudemolen, Netherlands": (53.0000, 6.3333),
            "Limburg, Netherlands": (51.0000, 6.0000),
            "Aarhus, Denmark": (56.1629, 10.2039),
        })
        
        # Additional US cities from logs
        self._cache.update({
            "Madison, WI": (43.0731, -89.4012),
            "Tucson, AZ": (32.2226, -110.9747),
            "Irvine, CA": (33.6846, -117.8265),
            "Flint, MI": (43.0125, -83.6875),
            "Austin, TX": (30.2672, -97.7431),
            "Cincinnati, OH": (39.1031, -84.5120),
            "San Jose, CA": (37.3382, -121.8863),
            "El Paso, TX": (31.7619, -106.4850),
            "Santa Rosa, CA": (38.4404, -122.7141),
            "Phoenix, AZ": (33.4484, -112.0740),
            "Quincy, MA": (42.2529, -71.0023),
            "Bozeman, MT": (45.6770, -111.0429),
            "Inglewood, CA": (33.9617, -118.3531),
            "Washington, DC": (38.9072, -77.0369),
            "Indianapolis, IN": (39.7684, -86.1581),
            "Floyd, VA": (36.9115, -80.3200),
            "Uniontown, PA": (39.9001, -79.7170),
            "Lancaster, PA": (40.0379, -76.3055),
            "Sterling, VA": (38.9862, -77.4283),
            "Providence, RI": (41.8240, -71.4128),
            "Amherst, MA": (42.3732, -72.5199),
            "Miami, FL": (25.7617, -80.1918),
            "Kent, OH": (41.1534, -81.3579),
            "Merced, CA": (37.3022, -120.4830),
            "Montclair, NJ": (40.8259, -74.2090),
            "Ventura, CA": (34.2746, -119.2290),
            "Columbia, SC": (34.0007, -81.0348),
            "Sharon, VT": (43.7778, -72.4473),
            "Illinois, IL": (40.6331, -89.3985),
            "Elmira, Canada": (43.5992, -80.5558),
            "Lethbridge, Canada": (49.6942, -112.8328),
            "Tacoma, WA": (47.2529, -122.4443),
            "Asheville, NC": (35.5951, -82.5515),
            "Easthampton, MA": (42.2668, -72.6687),
            "New Bedford, MA": (41.6362, -70.9342),
            "North Carolina, NC": (35.7596, -79.0193),
            "Harrisburg, PA": (40.2732, -76.8867),
            "Yonkers, NY": (40.9312, -73.8987),
            "Cleveland, OH": (41.4993, -81.6944),
            "Houston, TX": (29.7604, -95.3698),
            "Oshawa, Canada": (43.8971, -78.8658),
            "Michigan, MI": (44.3148, -85.6024),
            "York, PA": (39.9626, -76.7277),
            "Waldorf, MD": (38.6201, -76.9392),
            "Tallahassee, FL": (30.4383, -84.2807),
            "Texas, TX": (31.9686, -99.9018),
            "Hiroshima, Japan": (34.3853, 132.4553),
            "Norwalk, CT": (41.1176, -73.4079),
            "Fort Collins, CO": (40.5853, -105.0844),
            "Anacortes, WA": (48.5126, -122.6127),
            "Olympia, WA": (47.0379, -122.9007),
            "Ashville, NC": (35.5951, -82.5515),
            "Lansing, MI": (42.7325, -84.5555),
            "Baltimore, MD": (39.2904, -76.6122),
            "San Antonio, TX": (29.4241, -98.4936),
            "Joshua Tree, CA": (34.1347, -116.3131),
            "Chapel Hill, NC": (35.9132, -79.0558),
            "Burlington, VT": (44.4759, -73.2121),
            "Florida, FL": (27.6648, -81.5158),
            "Winter Haven, FL": (28.0222, -81.7329),
            "Vashon, WA": (47.4479, -122.4598),
            "Lowell, MA": (42.6334, -71.3162),
            "Franklin, TN": (35.9251, -86.8689),
            "Montana, MT": (46.8797, -110.3626),
            "Lewiston, ID": (46.4165, -117.0177),
            "Peoria, IL": (40.6936, -89.5890),
            "Baton Rouge, LA": (30.4515, -91.1871),
            "Englewood, NJ": (40.8929, -73.9726),
            "Toledo, OH": (41.6528, -83.5379),
            "Beverly, MA": (42.5584, -70.8800),
            "Grand Rapids, MI": (42.9634, -85.6681),
            "Eugene, OR": (44.0521, -123.0868),
            "Martinsville, VA": (36.6915, -79.8725),
            "Long Beach, CA": (33.7701, -118.1937),
            "Newark, NJ": (40.7357, -74.1724),
            "Marquette, MI": (46.5436, -87.3954),
            "Kalamazoo, MI": (42.2917, -85.5872),
            "West Springfield, MA": (42.1070, -72.6209),
            "Charleston, SC": (32.7765, -79.9311),
            "Oshkosh, WI": (44.0247, -88.5426),
            "Scranton, PA": (41.4090, -75.6624),
            "New Orleans, LA": (29.9511, -90.0715),
            "Springfield, MO": (37.2090, -93.2923),
            "Richmond, CA": (37.9358, -122.3477),
            "Downey, CA": (33.9401, -118.1332),
            "Lubbock, TX": (33.5779, -101.8552),
            "Newbury Park, CA": (34.1858, -118.9104),
            "Hollister, CA": (36.8525, -121.4016),
            "Abilene, TX": (32.4487, -99.7331),
            "Sacramento, CA": (38.5816, -121.4944),
            "Omaha, NE": (41.2565, -95.9345),
            "Ukiah, CA": (39.1502, -123.2078),
            "Staten Island, NY": (40.5795, -74.1502),
            "Colorado, CO": (39.5501, -105.7821),
            "Eau Claire, WI": (44.8113, -91.4985),
            "Mason City, IA": (43.1536, -93.2010),
            "Charlotte, NC": (35.2271, -80.8431),
            "Portland, ME": (43.6591, -70.2568),
            "San Luis Obispo, CA": (35.2828, -120.6596),
            "Albuquerque, NM": (35.0844, -106.6504),
            "Birmingham, AL": (33.5207, -86.8025),
            "Stillwater, OK": (36.1156, -97.0584),
            "Greenville, NC": (35.6127, -77.3664),
            "New Paltz, NY": (41.7473, -74.0865),
            "Mississippi, MS": (32.3547, -89.3985),
            "Brampton, Canada": (43.7315, -79.7624),
            "Québec City, Canada": (46.8139, -71.2080),
            "Dunnville, Canada": (42.9000, -79.6167),
            "Welland, Canada": (42.9834, -79.2482),
            "Adelaide, Australia": (-34.9285, 138.6007),
            "Byron Bay, Australia": (-28.6474, 153.6020),
            "Wollongong, Australia": (-34.4278, 150.8931),
            "Newcastle, Australia": (-32.9283, 151.7817),
            
            # Additional locations from error logs - Phase 3 (massive expansion)
            "Mount Pleasant, MI": (43.5978, -84.7675),
            "Sankt Wendel, Germany": (49.4667, 7.1667),
            "Treguaco, Chile": (-36.4333, -72.6833),
            "Espoo, Finland": (60.2055, 24.6559),
            "Rotterdam, Netherlands": (51.9225, 4.4792),
            "Utrecht, Netherlands": (52.0907, 5.1214),
            "Fortaleza, Brazil": (-3.7172, -38.5433),
            "Rhode Island, RI": (41.5801, -71.4774),
            "Paderborn, Germany": (51.7189, 8.7575),
            "Brugg, Switzerland": (47.4814, 8.2097),
            "Upper Darby, PA": (39.9548, -75.2868),
            "Koblenz, Germany": (50.3569, 7.5890),
            "Erlangen, Germany": (49.5897, 11.0089),
            "Zürich, Switzerland": (47.3769, 8.5417),
            "Lappi, Finland": (66.5039, 25.7294),
            "Praha, Czechia": (50.0755, 14.4378),
            "Barnsley, UK": (53.5526, -1.4797),
            "Turin, Italy": (45.0703, 7.6869),
            "Norrtälje, Sweden": (59.7580, 18.7046),
            "Greenville, SC": (34.8526, -82.3940),
            "The Hague, Netherlands": (52.0705, 4.3007),
            "Hamar, Norway": (60.7945, 11.0680),
            "Arkansas, AR": (35.2010, -91.8318),
            "Kyoto, Japan": (35.0116, 135.7681),
            "Salzburg, Austria": (47.8095, 13.0550),
            "Wrocław, Poland": (51.1079, 17.0385),
            "Mechelen, Belgium": (51.0259, 4.4777),
            "Assam, India": (26.2006, 92.9376),
            "Stavanger, Norway": (58.9700, 5.7331),
            "Costa Rica": (9.7489, -83.7534),
            "UAE": (23.4241, 53.8478),
            "Georgetown, MA": (42.7251, -70.9759),
            "Kristiansand, Norway": (58.1467, 7.9956),
            "Marshalltown, IA": (42.0494, -92.9080),
            "Monrovia, CA": (34.1442, -118.0015),
            "Karlsruhe, Germany": (49.0069, 8.4037),
            "Växjö, Sweden": (56.8777, 14.8091),
            "Esens, Germany": (53.6467, 7.6136),
            "Oulu, Finland": (65.0121, 25.4651),
            "Corrimal, Australia": (-34.3667, 150.8833),
            "St Louis, MO": (38.6270, -90.1994),
            "Saratoga Springs, NY": (43.0831, -73.7846),
            "Bielsko Biala, Poland": (49.8224, 19.0444),
            "Udine, Italy": (46.0710, 13.2345),
            "Normal, IL": (40.5142, -88.9906),
            "Pori, Finland": (61.4851, 21.7974),
            "Augsburg, Germany": (48.3705, 10.8978),
            "East Java, Indonesia": (-7.5361, 112.2384),
            "Warren, MI": (42.4774, -83.0465),
            "Ballarat, Australia": (-37.5622, 143.8503),
            "Belfast, Northern Ireland": (54.5973, -5.9301),
            "Würzburg, Germany": (49.7913, 9.9534),
            "New Jersey, United States": (40.0583, -74.4057),
            "Burlington, Canada": (43.3255, -79.7990),
            "İstanbul, Turkey": (41.0082, 28.9784),
            "Haarlem, Netherlands": (52.3874, 4.6462),
            "Brest, France": (48.3905, -4.4860),
            "Valparaíso, Chile": (-33.0472, -71.6127),
            "Odesa, Ukraine": (46.4825, 30.7233),
            "Salem, OR": (44.9429, -123.0351),
            "Genova, Italy": (44.4056, 8.9463),
            "Manaus, Brazil": (-3.1190, -60.0217),
            "Seoul, South Korea": (37.5665, 126.9780),
            "Turku, Finland": (60.4518, 22.2666),
            "Schio, Italy": (45.7144, 11.3583),
            "Halifax, UK": (53.7256, -1.8632),
            "Emsdetten, Germany": (52.1722, 7.5333),
            "Leipzig, Germany": (51.3397, 12.3731),
            "Lahti, Finland": (60.9827, 25.6612),
            "Wausau, WI": (44.9591, -89.6301),
            "Brescia, Italy": (45.5416, 10.2118),
            "Lombardy, Italy": (45.4654, 9.1859),
            "Ely, MN": (47.9032, -91.8671),
            "Wien, Austria": (48.2082, 16.3738),
            "Silverdale, WA": (47.6445, -122.6946),
            "Odense, Denmark": (55.4038, 10.4024),
            "Salt Lake City, UT": (40.7608, -111.8910),
            "Oklahoma, OK": (35.4676, -97.5164),
            "Herne, Germany": (51.5383, 7.2256),
            "Modena, Italy": (44.6471, 10.9252),
            "Hamilton, Canada": (43.2557, -79.8711),
            "Pesaro, Italy": (43.9102, 12.9130),
            "Helden, Netherlands": (51.3167, 6.0000),
            "Hurst, TX": (32.8234, -97.1706),
            "British Columbia, Canada": (53.7267, -127.6476),
            "Bengaluru, India": (12.9716, 77.5946),
            "Walhalla, SC": (34.7651, -83.0638),
            "Minnesota, MN": (46.7296, -94.6859),
            "Dijon, France": (47.3220, 5.0415),
            "Kettering, OH": (39.6895, -84.1689),
            "Ontario, Canada": (51.2538, -85.3232),
            "Temple, TX": (31.0982, -97.3428),
            "Gondar, Ethiopia": (12.6000, 37.4667),
            "Zagreb, Croatia": (45.8150, 15.9819),
            "Concepción, Chile": (-36.8201, -73.0444),
            "Münster, Germany": (51.9607, 7.6261),
            "Lisbon, Portugal": (38.7223, -9.1393),
            "Forest Lake, MN": (45.2791, -92.9852),
            "Mikkeli, Finland": (61.6886, 27.2719),
            "White Plains, NY": (41.0340, -73.7629),
            "Orland, ME": (44.5717, -68.7336),
            "Eksjö, Sweden": (57.6667, 14.9667),
            "Ravenna, Italy": (44.4184, 12.2035),
            "Olsztyn, Poland": (53.7784, 20.4801),
            "Worcester, MA": (42.2626, -71.8023),
            "Pembroke, Canada": (45.8167, -77.1000),
            "Port Elizabeth, South Africa": (-33.9608, 25.6022),
            "Arizona, AZ": (34.0489, -111.0937),
            "Potsdam, Germany": (52.3906, 13.0645),
            "Gevelsberg, Germany": (51.3167, 7.3333),
            "Des Moines, IA": (41.5868, -93.6250),
            "San José, Costa Rica": (9.9281, -84.0907),
            "Santa Barbara, CA": (34.4208, -119.6982),
            "Nice, France": (43.7102, 7.2620),
            "Maryville, TN": (35.7565, -83.9705),
            "Moncton, Canada": (46.0878, -64.7782),
            "Berkeley, CA": (37.8715, -122.2730),
            "Rostrenen, France": (48.2378, -3.3181),
            "Czechia": (49.8175, 15.4730),
            "Pescara, Italy": (42.4618, 14.2158),
            "Oxnard, CA": (34.1975, -119.1771),
            "Bowling Green, KY": (36.9685, -86.4808),
            "Guadalajara, Mexico": (20.6597, -103.3496),
            "Tanvald, Czechia": (50.7333, 15.3167),
            "Las Vegas, NV": (36.1699, -115.1398),
            "Binghamton, NY": (42.0987, -75.9180),
            "Huntsville, AL": (34.7304, -86.5861),
            "Ufa, Russia": (54.7388, 55.9721),
            "Dubai, UAE": (25.2048, 55.2708),
            "Ulm, Germany": (48.4011, 9.9876),
            "Bremen, Germany": (53.0793, 8.8017),
            "Brussel, Belgium": (50.8503, 4.3517),
            "Lyndhurst, NJ": (40.8120, -74.1243),
            "Longview, TX": (32.5007, -94.7405),
            "Peñaflor, Chile": (-33.6097, -70.9114),
            "Bialystok, Poland": (53.1325, 23.1688),
            "Colima, Mexico": (19.2452, -103.7241),
            "Landgraaf, Netherlands": (50.8833, 6.0167),
            "Siegen, Germany": (50.8748, 8.0243),
            "Lowell, NC": (35.2723, -81.1009),
            "Notodden, Norway": (59.5594, 9.2594),
            "Boise, ID": (43.6150, -116.2023),
            "Forli, Italy": (44.2226, 12.0408),
            "Ludwigshafen, Germany": (49.4815, 8.4353),
            "Albany, NY": (42.6526, -73.7562),
            "Rugby, UK": (52.3707, -1.2650),
            "Trosa, Sweden": (58.8833, 17.5500),
            "Chicopee, MA": (42.1487, -72.6079),
            "Cancún, Mexico": (21.1619, -86.8515),
            "Grenoble, France": (45.1885, 5.7245),
            "Dunedin, New Zealand": (-45.8788, 170.5028),
            "Massachusetts, MA": (42.4072, -71.3824),
            "Santander, Spain": (43.4623, -3.8099),
            "Kediri, Indonesia": (-7.8167, 112.0167),
            "Beijing, China": (39.9042, 116.4074),
            "Kimberley, Canada": (49.6703, -115.9773),
            "Connecticut, CT": (41.6032, -73.0877),
            "Dickson, TN": (36.0770, -87.3878),
            "Winterthur, Switzerland": (47.5000, 8.7500),
            "Leiden, Netherlands": (52.1601, 4.4970),
            "Bogotá, Colombia": (4.7110, -74.0721),
            "Aalborg, Denmark": (57.0488, 9.9217),
            "Linden, NJ": (40.6220, -74.2446),
            "Wiesbaden, Germany": (50.0826, 8.2400),
            "Torhout, Belgium": (51.0667, 3.1000),
            "Virginia, VA": (37.4316, -78.6569),
            "Laitila, Finland": (60.8667, 21.7000),
            "Voerde, Germany": (51.5833, 6.6833),
            "Brandoa, Portugal": (41.1667, -8.6500),
            "Eastbourne, UK": (50.7684, 0.2903),
            "Saint Louis, MO": (38.6270, -90.1994),
            "Hagen, Germany": (51.3587, 7.4761),
            "Vigo, Spain": (42.2406, -8.7207),
            "Istiaia, Greece": (38.9833, 23.1667),
            "Chattanooga, TN": (35.0456, -85.3097),
            "Groveland, MA": (42.7584, -71.0328),
            "Nijmegen, Netherlands": (51.8126, 5.8372),
            "Kotka, Finland": (60.4664, 26.9458),
            "Szczecin, Poland": (53.4285, 14.5528),
            "Armenia": (40.0691, 45.0382),
            "Montague, MA": (42.5348, -72.5381),
            "Kouvola, Finland": (60.8681, 26.7042),
            "Kelowna, Canada": (49.8880, -119.4960),
            "Gatineau, Canada": (45.4765, -75.7013),
            "Mannheim, Germany": (49.4875, 8.4660),
            "Rock Hill, SC": (34.9249, -81.0251),
            "Guildford, UK": (51.2362, -0.5704),
            "Ramona, CA": (33.0417, -116.8678),
            "Winston-Salem, NC": (36.0999, -80.2442),
            "Lviv, Ukraine": (49.8397, 24.0297),
            "Reading, UK": (51.4543, -0.9781),
            "Costa Mesa, CA": (33.6411, -117.9187),
            "Karmøy, Norway": (59.2728, 5.2889),
            "Bilbao, Spain": (43.2630, -2.9350),
            "Rijeka, Croatia": (45.3271, 14.4422),
            "Bollnäs, Sweden": (61.3492, 16.3939),
            "Richmond, IN": (39.8289, -84.8903),
            "Montijo, Portugal": (38.7078, -8.9742),
            "Lower Saxony, Germany": (52.6367, 9.8451),
            "Prague, Czechia": (50.0755, 14.4378),
            "South Carolina, SC": (33.8361, -81.1637),
            "Vicenza, Italy": (45.5455, 11.5354),
            "Vara, Sweden": (58.2633, 12.9575),
            "Eisenach, Germany": (50.9807, 10.3189),
            "Santiago, Chile": (-33.4489, -70.6693),
            "Minsk, Belarus": (53.9006, 27.5590),
            "Kings Mountain, NC": (35.2451, -81.3412),
            "Eupen, Belgium": (50.6269, 6.0333),
            "Marietta, GA": (33.9526, -84.5499),
            "Tallahassee, Florida": (30.4383, -84.2807),
            "Arvika, Sweden": (59.6553, 12.5906),
            "Methuen, MA": (42.7262, -71.1909),
            "New York, United States": (40.7128, -74.0060),
            "Collingswood, NJ": (39.9179, -75.0713),
            "Wichita, KS": (37.6872, -97.3301),
            "Tennessee, TN": (35.5175, -86.5804),
            "Taiwan": (23.6978, 120.9605),
            "Beaverton, OR": (45.4871, -122.8037),
            "Tübingen, Germany": (48.5216, 9.0576),
            "Boonton, NJ": (40.9023, -74.4071),
            "Canterbury, UK": (51.2802, 1.0789),
            "Sindelfingen, Germany": (48.7136, 8.9906),
            "Sofia, Bulgaria": (42.6977, 23.3219),
            "Kingston, NY": (41.9270, -73.9974),
            "Lafayette, LA": (30.2241, -92.0198),
            "Shiga, Japan": (35.0045, 135.8686),
            "Thunder Bay, Canada": (48.3809, -89.2477),
            "Cádiz, Spain": (36.5270, -6.2886),
            "Vevey, Switzerland": (46.4610, 6.8431),
            "Fukuoka, Japan": (33.5904, 130.4017),
            "Marfa, TX": (30.3044, -104.0178),
            "Johannesburg, South Africa": (-26.2041, 28.0473),
            "Athens, OH": (39.3292, -82.1013),
            "San Antonio, Chile": (-33.5950, -71.6128),
            "Topanga, CA": (34.0942, -118.6007),
            "Tours, France": (47.3941, 0.6848),
            "Lille, France": (50.6292, 3.0573),
            "Lucerne, Switzerland": (47.0502, 8.3093),
            "Sarnia, Canada": (42.9994, -82.3089),
            "Konstanz, Germany": (47.6633, 9.1753),
            "Roma, Italy": (41.9028, 12.4964),
            "Jensen Beach, FL": (27.2545, -80.2298),
            "Coxsackie, NY": (42.3509, -73.8026),
            "Brittany, France": (48.2020, -2.9326),
            "Jacksonville, FL": (30.3322, -81.6557),
            "Recanati, Italy": (43.4067, 13.5489),
            "Champaign, IL": (40.1164, -88.2434),
            "Mukilteo, WA": (47.9445, -122.3046),
            "Longmont, CO": (40.1672, -105.1019),
            "Hayfork, CA": (40.5540, -123.1836),
            "Nuremberg, Germany": (49.4521, 11.0767),
            "Canberra, Australia": (-35.2809, 149.1300),
            "Victoria, Canada": (48.4284, -123.3656),
            "Tunis, Tunisia": (36.8065, 10.1815),
            "Rochester, MN": (44.0121, -92.4802),
            "Moscow, Russia": (55.7558, 37.6173),
            "Osnabrück, Germany": (52.2799, 8.0472),
            "Thessaloniki, Greece": (40.6401, 22.9444),
            "Culver City, CA": (34.0211, -118.3965),
            "Užice, Serbia": (43.8583, 19.8483),
            "Pompano Beach, FL": (26.2379, -80.1248),
            "Cardiff, UK": (51.4816, -3.1791),
            "Saarbrücken, Germany": (49.2401, 6.9969),
            "Hasselt, Belgium": (50.9307, 5.3378),
            "St. John's, Canada": (47.5615, -52.7126),
            "Michigan City, IN": (41.7073, -86.8950),
            "Agadez, Niger": (16.9740, 7.9910),
            "Croydon, UK": (51.3762, -0.0982),
            "Wakefield, UK": (53.6833, -1.4953),
            "Eindhoven, Netherlands": (51.4416, 5.4697),
            "Augusta, ME": (44.3106, -69.7795),
            "Valdivia, Chile": (-39.8142, -73.2459),
            "Tulsa, OK": (36.1540, -95.9928),
            "Appleton, WI": (44.2619, -88.4154),
            "Genoa, Italy": (44.4056, 8.9463),
            "Malibu, CA": (34.0259, -118.7798),
            "Norman, OK": (35.2226, -97.4395),
            "Waxhaw, NC": (34.9243, -80.7434),
            "Hastings, UK": (50.8541, 0.5728),
            "Lansdale, PA": (40.2415, -75.2838),
            "Exeter, UK": (50.7184, -3.5339),
            "Beacon, NY": (41.5048, -73.9696),
            "Hadley, MA": (42.3526, -72.5717),
            "Curitiba, Brazil": (-25.4284, -49.2733),
            "Newport, RI": (41.4901, -71.3128),
            "Stephenville, TX": (32.2207, -98.2023),
            "Chester, UK": (53.1906, -2.8910),
            "Heroica Veracruz, Mexico": (19.1738, -96.1342),
            "Latvia / Georgia": (56.8796, 24.6032),
            "Venice, Italy": (45.4408, 12.3155),
            "Utah, UT": (39.3210, -111.0937),
            "Sierra Vista, AZ": (31.5455, -110.2773),
            "Stevenage, UK": (51.9022, -0.2022),
            "Middlesbrough, UK": (54.5742, -1.2350),
            "Dripping Springs, TX": (30.1902, -98.0864),
            "Palma, Spain": (39.5696, 2.6502),
            "Columbia, MO": (38.9517, -92.3341),
            "Dublin, CA": (37.7022, -121.9358),
            "Borlänge, Sweden": (60.4858, 15.4357),
            "Syracuse, NY": (43.0481, -76.1474),
            "Drammen, Norway": (59.7439, 10.2045),
            "Flanders, Belgium": (51.0167, 3.7333),
            "Launceston, Australia": (-41.4332, 147.1441),
            "Gävle, Sweden": (60.6749, 17.1413),
            "Ecuador": (-1.8312, -78.1834),
            "Logan, UT": (41.7370, -111.8338),
            "Granville, France": (48.8378, -1.5978),
            "Jabłonka, Poland": (49.4833, 19.7333),
            "Ada, OH": (40.7695, -83.8222),
            "Akron, OH": (41.0814, -81.5190),
            "Tallinn, Estonia": (59.4370, 24.7536),
            "Regina, Canada": (50.4452, -104.6189),
            "Doylestown, PA": (40.3101, -75.1299),
            "Ethiopia": (9.1450, 40.4897),
            "Wenatchee, WA": (47.4235, -120.3103),
            "Ohio, OH": (40.4173, -82.9071),
            "Pennsylvania, PA": (41.2033, -77.1945),
            "Fort Wayne, IN": (41.0793, -85.1394),
            "Mitzpe Ramon, Israel": (30.6100, 34.8017),
            "Solan, India": (30.9045, 77.0967),
            "Hamilton, New Zealand": (-37.7870, 175.2793),
            "Linköping, Sweden": (58.4108, 15.6214),
            "Riverside, CA": (33.9533, -117.3962),
            "Bayonne, France": (43.4832, -1.4748),
            "Tàrrega, Spain": (41.6469, 1.1397),
            "Wicklow, Ireland": (52.9808, -6.0431),
            "Vannes, France": (47.6584, -2.7606),
            "Cambridge, MA": (42.3736, -71.1097),
            "Virginia Beach, VA": (36.8529, -75.9780),
            "Santa Fe, NM": (35.6870, -105.9378),
            "Charlottesville, VA": (38.0293, -78.4767),
            "Muskegon, MI": (43.2342, -86.2484),
            "Bamberg, Germany": (49.8988, 10.9027),
            "Fremantle, Australia": (-32.0569, 115.7439),
            "Cheshire, UK": (53.2000, -2.5333),
            "Butte, MT": (46.0038, -112.5348),
            "Purchase, NY": (41.0401, -73.7146),
            "Istanbul, Turkey": (41.0082, 28.9784),
            "West Virginia, WV": (38.5976, -80.4549),
            "Wigan, UK": (53.5448, -2.6318),
            "Reading, PA": (40.3356, -75.9269),
            "Myrtle Beach, SC": (33.6891, -78.8867),
            "Piracicaba, Brazil": (-22.7250, -47.6477),
            "Moss, Norway": (59.4358, 10.6571),
            "Cleveland, Ohio": (41.4993, -81.6944),
            "Kalachinsk, Russia": (55.0500, 74.5833),
            "Grøa, Norway": (60.1667, 11.1667),
            "Passau, Germany": (48.5665, 13.4318),
            "Luzern, Switzerland": (47.0502, 8.3093),
            "Laramie, WY": (41.3114, -105.5911),
            "Palm Coast, FL": (29.5845, -81.2079),
            "Waterlooville, UK": (50.8800, -1.0300),
            "Cesena, Italy": (44.1389, 12.2428),
            "Marburg, Germany": (50.8021, 8.7667),
            "Hattiesburg, MS": (31.3271, -89.2903),
            "Dover, UK": (51.1279, 1.3134),
            "Le Mans, France": (48.0077, 0.1984),
            "Asbury Park, NJ": (40.2204, -74.0121),
            "Duluth, MN": (46.7867, -92.1005),
            "Stroud, UK": (51.7450, -2.2169),
            "Lund, Sweden": (55.7047, 13.1910),
            "Hopewell, NJ": (40.3887, -74.7610),
            "Pilsen, Czechia": (49.7384, 13.3736),
            "Catania, Italy": (37.5079, 15.0830),
            "Port Angeles, WA": (48.1181, -123.4307),
            "Tel Aviv, Israel": (32.0853, 34.7818),
            "California, United States": (36.7783, -119.4179),
            "Leicester, UK": (52.6369, -1.1398),
            "Amarillo, TX": (35.2220, -101.8313),
            "Bellingham, WA": (48.7519, -122.4787),
            "Zambia": (-13.1339, 27.8493),
            "München, Germany": (48.1351, 11.5820),
            "Uttran, Sweden": (63.3333, 18.9333),
            "Georgia / Germany": (42.3154, 43.3569),
            "La Quinta, CA": (33.6633, -116.3100),
            
            # Phase 4: Additional missing locations from error logs (200+ cities)
            "Mississauga, Canada": (43.5890, -79.6441),
            "Los Angeles, California": (34.0522, -118.2437),
            "Rocklin, CA": (38.7907, -121.2358),
            "Waukesha, WI": (43.0117, -88.2315),
            "Brugge, Belgium": (51.2093, 3.2247),
            "West Midlands, UK": (52.4862, -1.8904),
            "Akureyri, Iceland": (65.6835, -18.1000),
            "Freehold, NJ": (40.2607, -74.2738),
            "Ryebrook, NY": (41.0026, -73.6832),
            "Boca Raton, FL": (26.3683, -80.1289),
            "Glasgow, UK": (55.8642, -4.2518),
            "Faroe Islands": (62.0000, -6.7833),
            "San Clemente, CA": (33.4270, -117.6120),
            "Westfield, MA": (42.1251, -72.7495),
            "Somerville, MA": (42.3876, -71.0995),
            "Yogyakarta, Indonesia": (-7.7956, 110.3695),
            "Knoxville, TN": (35.9606, -83.9207),
            "Larvik, Norway": (59.0540, 10.0353),
            "Ulricehamn, Sweden": (57.7932, 13.4140),
            "Cornwall, UK": (50.2660, -5.0527),
            "Correggio, Italy": (44.7706, 10.7806),
            "Ellicott City, MD": (39.2673, -76.7983),
            "Walnut Creek, CA": (37.9101, -122.0652),
            "Belfast, UK": (54.5973, -5.9301),
            "Kalispell, MT": (48.1958, -114.3160),
            "Monterrey, MX": (25.6866, -100.3161),
            "Swansea, UK": (51.6214, -3.9436),
            "Borjomi, Georgia": (41.8500, 43.3833),
            "Røyken, Norway": (59.7500, 10.4000),
            "Mainz, Germany": (50.0000, 8.2711),
            "Coatesville, PA": (39.9831, -75.8238),
            "Seattle, Washington": (47.6062, -122.3321),
            "Geelong, Australia": (-38.1499, 144.3617),
            "Aberystwyth, UK": (52.4140, -4.0820),
            "Düsseldorf, Germany": (51.2277, 6.7735),
            "Gold Coast, Australia": (-28.0167, 153.4000),
            "Fort Worth, TX": (32.7555, -97.3308),
            "Old Tappan, NJ": (41.0148, -73.9918),
            "Coeur D'Alene, ID": (47.6777, -116.7805),
            "Traverse City, MI": (44.7631, -85.6206),
            "Fargo, ND": (46.8772, -96.7898),
            "Encinitas, CA": (33.0370, -117.2920),
            "Castlewood, VA": (36.8773, -82.2868),
            "York, UK": (53.9591, -1.0815),
            "Meriden, CT": (41.5382, -72.8070),
            "Reno, NV": (39.5296, -119.8138),
            "Henderson, NV": (36.0395, -114.9817),
            "Cottonwood Heights, UT": (40.6197, -111.8099),
            "St. Petersburg, FL": (27.7676, -82.6403),
            "Durant, OK": (33.9940, -96.3708),
            "Taipei, Taiwan": (25.0330, 121.5654),
            "Lysekil, Sweden": (58.2744, 11.4354),
            "Weston Super Mare, UK": (51.3461, -2.9770),
            "Catskill, NY": (42.2187, -73.8646),
            "Rancho Cucamonga, CA": (34.1064, -117.5931),
            "Caldicot, UK": (51.5881, -2.7528),
            "Boulder, CO": (40.0150, -105.2705),
            "A Coruña, Spain": (43.3623, -8.4115),
            "Québec, Canada": (46.8139, -71.2080),
            "Wisborough Green, UK": (51.0169, -0.5450),
            "Shelburne Falls, MA": (42.6042, -72.7395),
            "Belarus": (53.9045, 27.5615),
            "New City, NY": (41.1476, -73.9893),
            "Ashland, NH": (43.6970, -71.6306),
            "Quebec City, Canada": (46.8139, -71.2080),
            "Bowling Green, OH": (41.3748, -83.6513),
            "Veszprém, Hungary": (47.0930, 17.9093),
            "Monaco, Monaco": (43.7384, 7.4246),
            "Stuttgart, Germany": (48.7758, 9.1829),
            "Prince George, Canada": (53.9171, -122.7497),
            "Bournemouth, UK": (50.7192, -1.8808),
            "Whitby, Canada": (43.8975, -78.9429),
            "Parma, Italy": (44.8015, 10.3279),
            "Milton Keynes, UK": (52.0406, -0.7594),
            "Maastricht, Netherlands": (50.8514, 5.6909),
            "Bayreuth, Germany": (49.9481, 11.5783),
            "Marlborough, MA": (42.3459, -71.5523),
            "Palm Desert, CA": (33.7222, -116.3744),
            "Suhescun, France": (43.3333, -0.9167),
            "Bradford, UK": (53.7960, -1.7594),
            "Rangiora, New Zealand": (-43.3033, 172.5950),
            "Bellevue, OH": (41.2734, -82.8410),
            "Kettering, UK": (52.3987, -0.7260),
            "Rotherham, UK": (53.4326, -1.3635),
            "Ada, OK": (34.7746, -96.6783),
            "New Braunfels, TX": (29.7030, -98.1245),
            "Fort Myers, FL": (26.6406, -81.8723),
            "Metz, France": (49.1193, 6.1757),
            "Ann Arbor, MI": (42.2808, -83.7430),
            "Pamplona, Spain": (42.8125, -1.6458),
            "Tuusula, Finland": (60.4036, 25.0267),
            "Spokane, WA": (47.6588, -117.4260),
            "Middelburg, Netherlands": (51.4988, 3.6143),
            "Tilburg, Netherlands": (51.5555, 5.0913),
            "Huntington Beach, CA": (33.6603, -117.9992),
            "Tinley Park, IL": (41.5731, -87.7845),
            "Haifa, Israel": (32.7940, 34.9896),
            "Savona, Italy": (44.3091, 8.4812),
            "Greenwich, NY": (43.0898, -73.4982),
            "Limerick, Ireland": (52.6680, -8.6305),
            "Dumaguete, Philippines": (9.3068, 123.3054),
            "Tuscany, Italy": (43.7711, 11.2486),
            "Waterloo, Canada": (43.4643, -80.5204),
            "Salford, UK": (53.4875, -2.2901),
            "Provo, UT": (40.2338, -111.6585),
            "Rockford, IL": (42.2711, -89.0940),
            "Timișoara, Romania": (45.7489, 21.2087),
            "Valencia, Spain": (39.4699, -0.3763),
            "Nevers, France": (46.9898, 3.1577),
            "Gloucester, MA": (42.6159, -70.6620),
            "Prato, Italy": (43.8777, 11.0955),
            "Sardinia, Italy": (40.1209, 9.0129),
            "Rockaway, NJ": (40.9009, -74.5141),
            "LaSalle, Canada": (42.2167, -83.0500),
            "Crawley, UK": (51.1073, -0.1863),
            "Mayne Island, Canada": (48.8500, -123.2833),
            "Bendigo, Australia": (-36.7570, 144.2794),
            "Wokingham, UK": (51.4110, -0.8340),
            "Antibes, France": (43.5808, 7.1251),
            "Oldenburg, Germany": (53.1435, 8.2146),
            "Čakovec, Croatia": (46.3850, 16.4344),
            "Twentynine Palms, CA": (34.1356, -116.0542),
            "Brattleboro, VT": (42.8509, -72.5579),
            "Northampton, UK": (52.2405, -0.9027),
            "Rīga, Latvia": (56.9496, 24.1052),
            "Ebeltoft, Denmark": (56.1944, 10.6806),
            "Yeovil, UK": (50.9452, -2.6400),
            "Yirrkala, Australia": (-12.2500, 136.8833),
            "Tampa, FL": (27.9506, -82.4572),
            "Chiliomodi, Greece": (37.9000, 22.7667),
            "Saint Gallen, Switzerland": (47.4245, 9.3767),
            "Luxembourg": (49.6116, 6.1319),
            "Yukon, Canada": (64.2823, -135.0000),
            "Perm, Russia": (58.0105, 56.2502),
            "Groningen, Netherlands": (53.2194, 6.5665),
            "Kidal, Mali": (18.4411, 1.4078),
            "Faenza, Italy": (44.2858, 11.8814),
            "Cesky Krumlov, Czechia": (48.8127, 14.3175),
            "Margate, UK": (51.3813, 1.3862),
            "Ciudad Juárez, Mexico": (31.6904, -106.4245),
            "Loveland, CO": (40.3978, -105.0750),
            "Tehran, Iran": (35.6892, 51.3890),
            "Geleen, Netherlands": (50.9670, 5.8237),
            "Vacaville, CA": (38.3566, -121.9877),
            "Auburn, CA": (38.8966, -121.0770),
            "Stroudsburg, PA": (40.9865, -75.1946),
            "Lithuania": (55.1694, 23.8813),
            "Strasbourg, France": (48.5734, 7.7521),
            "Limoges, France": (45.8336, 1.2611),
            "Frederick, MD": (39.4143, -77.4105),
            "Oxford, OH": (39.5070, -84.7453),
            "Modesto, CA": (37.6391, -120.9969),
            "Giarre, Italy": (37.7267, 15.1817),
            "Białystok, Poland": (53.1325, 23.1688),
            "Iowa City, IA": (41.6611, -91.5302),
            "Washington, D.C.": (38.9072, -77.0369),
            "Foligno, Italy": (42.9569, 12.7036),
            "Coffs Harbour, Australia": (-30.2986, 153.1094),
            "Besançon, France": (47.2380, 6.0243),
            "Vesoul, France": (47.6200, 6.1600),
            "Puerto La Cruz, Venezuela": (10.2167, -64.6333),
            "Poznań, Poland": (52.4064, 16.9252),
            "Connecticut, United States": (41.6032, -73.0877),
            "Wilkes Barre, PA": (41.2459, -75.8813),
            "New Hampshire, NH": (43.1939, -71.5724),
            "Bergamo, Italy": (45.6983, 9.6773),
            "Porto Alegre, Brazil": (-30.0346, -51.2177),
            "Wuppertal, Germany": (51.2562, 7.1508),
            "Romania": (45.9432, 24.9668),
            "Danville, VA": (36.5860, -79.3950),
            "Fribourg, Switzerland": (46.8063, 7.1608),
            
            # Phase 5: Additional missing locations from latest error logs
            "Draper, UT": (40.5246, -111.8638),
            "Gloucester Township, NJ": (39.7420, -75.0293),
            "Lleida, Spain": (41.6176, 0.6200),
            "Otterberg, Germany": (49.5019, 7.7719),
            "Essex, NJ": (40.7923, -74.2832),
            "Leobendorf, Austria": (48.3667, 16.3333),
            "Quispamsis, Canada": (45.4326, -65.9453),
            "Fredericia, Denmark": (55.5657, 9.7519),
            "Santa Monica, CA": (34.0195, -118.4912),
            "Sparta, MI": (43.1622, -85.7100),
            "Johnson City, TN": (36.3134, -82.3535),
            "Oneonta, NY": (42.4528, -75.0635),
            "Mlini, Croatia": (42.6000, 18.2833),
            "Pancevo, Serbia": (44.8711, 20.6400),
            "Amiens, France": (49.8942, 2.2957),
            "International": (20.0, 0.0),  # Generic international location
            "Hertfordshire, UK": (51.8097, -0.2379),
            "Poitiers, France": (46.5802, 0.3404),
            "Joliet, IL": (41.5250, -88.0817),
            "Zwolle, Netherlands": (52.5125, 6.0944),
            "Spartanburg, SC": (34.9496, -81.9320),
            "Nisterau, Germany": (50.5833, 7.8167),
            "Menton, France": (43.7750, 7.4950),
            "Leeuwarden, Netherlands": (53.2012, 5.8086),
            "Sisikon, Switzerland": (46.9333, 8.6167),
            "Farmingdale, NY": (40.7326, -73.4454),
            "Roanne, France": (46.0333, 4.0667),
            "Croatia": (45.1, 15.2),
            "Belfort, France": (47.6333, 6.8500),
            "Höör, Sweden": (55.9333, 13.5333),
            "Lima, OH": (40.7425, -84.1052),
            "Aschaffenburg, Germany": (49.9747, 9.1467),
            "Florence, Italy": (43.7696, 11.2558),
            "Trnava, Slovakia": (48.3774, 17.5881),
            "Ocean City, MD": (38.3365, -75.0849),
            "Guelph, Canada": (43.5448, -80.2482),
            "Makó, Hungary": (46.2167, 20.4833),
            "Heredia, Costa Rica": (9.9981, -84.1197),
            "Alma, Canada": (48.5500, -71.6500),
            "Pertuis, France": (43.6944, 5.5022),
            "Morgantown, WV": (39.6295, -79.9559),
            "Northampton. UK": (52.2405, -0.9027),
            "Missoula, MT": (46.8721, -113.9940),
            "Culiacán, Mexico": (24.8091, -107.3940),
            "Hof, Germany": (50.3167, 11.9167),
            "Castrop Rauxel, Germany": (51.5556, 7.3167),
            "Harwich, UK": (51.9333, 1.2833),
            "Västerås, Sweden": (59.6099, 16.5448),
            "Scarborough, UK": (54.2797, -0.4044),
            "Rovereto, Italy": (45.8900, 11.0400),
            "La Plata, Argentina": (-34.9215, -57.9545),
            "Volos, Greece": (39.3667, 22.9500),
            "Lübeck, Germany": (53.8655, 10.6866),
            "Nyon, Switzerland": (46.3833, 6.2333),
            "Amersfoort, Netherlands": (52.1561, 5.3878),
            "Clarence Center, NY": (43.0089, -78.6381),
            "Savannah, GA": (32.0809, -81.0912),
            "Krasnoyarsk, Russia": (56.0153, 92.8932),
            "Levis, Canada": (46.8000, -71.1778),
            "Kerava, Finland": (60.4022, 25.1050),
            "Zurich, Switzerland": (47.3769, 8.5417),
            "Uusimaa, Finland": (60.3172, 24.9633),
            "Talcahuano, Chile": (-36.7167, -73.1167),
            "Almaty, Kazakhstan": (43.2220, 76.8512),
            "Devon, UK": (50.7156, -3.5309),
            "Terrassa, Spain": (41.5667, 2.0167),
            "Gambolò, Italy": (45.2667, 8.8500),
            "Speyer, Germany": (49.3167, 8.4333),
            "Silkeborg, Denmark": (56.1697, 9.5450),
            "Košice, Slovakia": (48.7164, 21.2611),
            "Brunswick, Germany": (52.2689, 10.5268),
            "Evansville, IN": (37.9716, -87.5711),
            "Novara, Italy": (45.4469, 8.6219),
            "Sioux Falls, SD": (43.5460, -96.7313),
            "Al Rudayyif, Tunisia": (34.3833, 8.1667),
            "Hattingen, Germany": (51.4000, 7.1833),
            "Avignon, France": (43.9493, 4.8055),
            "Wisconsin, WI": (44.5000, -89.5000),
            "Seinäjoki, Finland": (62.7903, 22.8403),
            "Olomouc, Czechia": (49.5938, 17.2509),
            "Nitra, Slovakia": (48.3081, 18.0872),
            "Montepulciano, Italy": (43.1000, 11.7833),
            "Prescott, AZ": (34.5400, -112.4685),
            "Rio Grande, Argentina": (-53.7875, -67.7094),
            "Remscheid, Germany": (51.1789, 7.1933),
            "Palermo, Italy": (38.1157, 13.3615),
            "Verona, Italy": (45.4384, 10.9916),
            "Concord, CA": (37.9780, -122.0311),
            "Plymouth, MN": (45.0105, -93.4555),
            "Stoke, UK": (53.0027, -2.1794),
            "Glendale, CA": (34.1425, -118.2551),
            "Bari, Italy": (41.1171, 16.8719),
            "Whitehorse, Canada": (60.7212, -135.0568),
            "Vysočina Region, Czechia": (49.5000, 15.5833),
            "Ceará, Brazil": (-5.0000, -39.0000),
            "Kharkiv, Ukraine": (49.9935, 36.2304),
            "Alabama, US": (32.8067, -86.7911),
            "Saint-Nazaire, France": (47.2733, -2.2133),
            "England, UK": (52.3555, -1.1743),
            "Illinois, US": (40.6331, -89.3985),
            "Sao Paulo, Brazil": (-23.5505, -46.6333),
            "Oregon, US": (43.8041, -120.5542),
            "West Kirby, UK": (53.3733, -3.1800),
            "New Jersey, US": (40.0583, -74.4057),
            "Pennsylvania, US": (41.2033, -77.1945),
            "Maryland, US": (39.0458, -76.6413),
            "Georgia, US": (32.1656, -82.9001),
            "Texas, US": (31.9686, -99.9018),
            "Birmingham, England": (52.4862, -1.8904),
            "Wrexham, Wales": (53.0467, -2.9933),
            "New York": (40.7128, -74.0060),
            "Arkansas, US": (35.2010, -91.8318),
            "Bayamón, Puerto Rico": (18.3996, -66.1535),
            "Latvia": (56.8796, 24.6032),
            "England": (52.3555, -1.1743),
            "Clare, Australia": (-33.8333, 138.6000),
            "Motherwell, UK": (55.7875, -3.9817),
            "Ohio, US": (40.4173, -82.9071),
            "USA": (37.0902, -95.7129),
            "New York, USA": (40.7128, -74.0060),
            "Hay On Wye, UK": (52.0744, -3.1283),
            "Quebec, Canada": (52.9399, -73.5491),
            "Alpine, CA": (32.8350, -116.7664),
            "England / US": (40.0, -50.0),
            "Larne, UK": (54.8528, -5.8150),
            
            # Phase 5 continuation: More missing locations from error logs
            "Chambéry, France": (45.5667, 5.9167),
            
            # Phase 6: Additional missing locations from latest error log
            "West Lafayette, IN": (40.4259, -86.9081),
            "Gympie, Australia": (-26.1905, 152.6660),
            "Zadar, Croatia": (44.1194, 15.2314),
            "Nova Scotia, Canada": (44.6820, -63.7443),
            "Bethesda, MD": (38.9807, -77.1015),
            "Copiague, NY": (40.6812, -73.3996),
            "Jaén, Spain": (37.7796, -3.7849),
            "Saint Paul, MN": (44.9537, -93.0900),
            "Pula, Croatia": (44.8666, 13.8496),
            "Beaumont, TX": (30.0860, -94.1018),
            "Dublin, Ireland": (53.3498, -6.2603),  # Note: "Dublin, UK" in errors - using Ireland
            "Heinola, Finland": (61.2055, 26.0372),
            "Hrodna, Belarus": (53.6884, 23.8258),
            "Nodeland, Norway": (58.7580, 5.7330),
            "Illinois, USA": (40.6331, -89.3985),
            "Kent, UK": (51.2787, 0.5217),
            "Mantova, Italy": (45.1564, 10.7914),
            "Montreux, Switzerland": (46.4312, 6.9106),
            "Clifton, NJ": (40.8584, -74.1638),
            "Lempäälä, Finland": (61.3144, 23.7569),
            "Örnsköldsvik, Sweden": (63.2909, 18.7155),
            "Blacksburg, VA": (37.2296, -80.4139),
            "Guimaraes, Portugal": (41.4416, -8.2918),
            "Princeton, NJ": (40.3573, -74.6672),
            "Missouri, MO": (37.9643, -91.8318),
            "Östersund, Sweden": (63.1792, 14.6357),
            "San Rafael, CA": (37.9735, -122.5311),
            "Wales, UK": (52.1307, -3.7837),
            "Ireland, UK": (53.4129, -8.2439),  # Using Ireland
            "Torreilles, France": (42.7583, 3.0289),
            "Syktyvkar, Russia": (61.6681, 50.8372),
            "Friûl, Italy": (46.0569, 13.2358),
            "Florence, KY": (39.0067, -84.6266),
            "Newington, CT": (41.6981, -72.7237),
            "Tulungagung, Indonesia": (-8.0657, 111.9037),
            "Sacile, Italy": (45.9558, 12.5003),
            "Brunico, Italy": (46.7977, 11.9358),
            "Wakefield, MA": (42.5064, -71.0723),
            "Livonia, MI": (42.3970, -83.3527),
            "Nebraska, NE": (41.4925, -99.9018),
            "Ypres, Belgium": (50.8510, 2.8857),
            "Springfield, MA": (42.1015, -72.5898),
            "Frederikshavn, Denmark": (57.4407, 10.5368),
            "La Paz, Bolivia": (-16.5000, -68.1500),
            "Cheyenne, WY": (41.1400, -104.8202),
            "Sudbury, UK": (52.0414, 0.7310),
            "Redwood City, CA": (37.4852, -122.2364),
            "Worthington, OH": (40.0931, -83.0180),
            "Aberdeen, WA": (46.9754, -123.8157),
            "Perth, UK": (56.3958, -3.4374),
            "Amstetten, Austria": (48.1225, 14.8722),
            "Farr West, UT": (41.2974, -112.0277),
            "Oviedo, Spain": (43.3614, -5.8593),
            "San Sebastian, Spain": (43.3183, -1.9812),
            "Gorliz, Spain": (43.4167, -2.9500),
            "Hundvåg, Norway": (59.0683, 5.7061),
            "Lewiston, ME": (44.1004, -70.2148),
            "Anchorage, AK": (61.2181, -149.9003),
            "Inverness, UK": (57.4778, -4.2247),
            "Nizhny Novgorod, Russia": (56.2965, 43.9361),
            "Tarnow, Poland": (50.0121, 20.9858),
            "Hjordkær, Denmark": (55.0167, 9.3167),
            "Sevilla, Spain": (37.3891, -5.9845),
            "Anaheim, CA": (33.8366, -117.9143),
            "Sikkim, India": (27.5330, 88.5122),
            "Corona, CA": (33.8753, -117.5664),
            "Keyport, NJ": (40.4398, -74.1993),
            "Freiburg, Germany": (47.9990, 7.8421),
            "Nepal": (28.3949, 84.1240),
            "Hanoi, Vietnam": (21.0285, 105.8542),
            "Patras, Greece": (38.2466, 21.7346),
            "Nashua, NH": (42.7654, -71.4676),
            "Richmond, MI": (42.8078, -82.7549),
            "Mandurah, Australia": (-32.5269, 115.7219),
            "Viña Del Mar, Chile": (-33.0247, -71.5517),
            "Douglassville, PA": (40.2562, -75.7399),
            "Reus, Spain": (41.1560, 1.1068),
            "Podolsk, Russia": (55.4242, 37.5544),
            "Lisburn, UK": (54.5162, -6.0583),
            "Carlow, Ireland": (52.8408, -6.9261),
            "Hagerstown, MD": (39.6418, -77.7200),
            "Chico, CA": (39.7285, -121.8375),
            "João Pessoa, Brazil": (-7.1195, -34.8450),
            "Hamelin, Germany": (52.1033, 9.3570),
            "Whittier, CA": (33.9792, -118.0326),
            "Hessen, Germany": (50.6521, 9.1624),
            "Fredrikstad, Norway": (59.2181, 10.9298),
            "Johnstown, PA": (40.3267, -78.9220),
            "Sarasota, FL": (27.3364, -82.5307),
            "Worldwide": (0.0, 0.0),  # Generic global location
            "Limache, Chile": (-33.0170, -71.2667),
            "Oakland, California": (37.8044, -122.2712),
            "Texas, United States": (31.9686, -99.9018),
            "Windsor, Canada": (42.3149, -83.0364),
            "Rochester Hills, MI": (42.6583, -83.1499),
            "New England, MA": (42.5000, -71.5000),  # Central New England
            "Wolfsburg, Germany": (52.4227, 10.7865),
            "Gerstetten, Germany": (48.6255, 10.0223),
            "Hoboken, NJ": (40.7439, -74.0323),
            "Lafayette, CA": (37.8857, -122.1180),
            "Toronto, Ontario, Canada": (43.6532, -79.3832),
            "Emsland, Germany": (52.8167, 7.3000),
            "Antwerpen, Belgium": (51.2194, 4.4025),
            "Hannover, Germany": (52.3759, 9.7320),
            "Minnasota": (46.7296, -94.6859),  # Typo for Minnesota
            "New Jersey": (40.0583, -74.4057),
            "Kansas City": (39.0997, -94.5786),  # Kansas City, MO
            "Boise, Idaho": (43.6150, -116.2023),
            "Vermont": (44.5588, -72.5778),
            "Erfurt, Germany": (50.9848, 11.0299),
            "Kópavogur, Iceland": (64.1093, -21.9111),
            "Switzerland, Geneva": (46.2044, 6.1432),
            "Columbus, Ohio": (39.9612, -82.9988),
            "Vancouver, BC, Canada": (49.2827, -123.1207),
            "Neuchâtel, Switzerland": (46.9899, 6.9300),
            "Atlanta, GA, USA": (33.7490, -84.3880),
            "Cincinnati, Ohio": (39.1031, -84.5120),
            "Chicago, Illinois": (41.8781, -87.6298),
            "Dallas, Texas": (32.7767, -96.7970),
            "Wörgl, Austria": (47.4864, 12.0736),
            "Newark, Delaware": (39.6837, -75.7497),
            "Sacramento, California": (38.5816, -121.4944),
            "Portland, Oregon": (45.5152, -122.6784),
            "Vancouver, BC": (49.2827, -123.1207),
            "Massachusetts": (42.4072, -71.3824),
            "Bellingham, Washington": (48.7519, -122.4787),
            "Dallas, TX, USA": (32.7767, -96.7970),
            "Iowa": (41.8780, -93.0977),
            "Texas": (31.9686, -99.9018),
            "Orlando, Florida": (28.5383, -81.3792),
            "New Haven, Connecticut": (41.3083, -72.9279),
            "Colestin, Oregon": (42.0804, -122.6569),
            "Pittsburgh, Pennsylvania": (40.4406, -79.9959),
            "Bourg en Bresse, France": (46.2051, 5.2258),
            "Columbia, South Carolina": (34.0007, -81.0348),
            "Ocean City, Maryland": (38.3365, -75.0849),
            "New York City, NY": (40.7128, -74.0060),
            "Frederick, Maryland": (39.4143, -77.4105),
            "California": (36.7783, -119.4179),
            "Philadelphia Pennsylvania": (39.9526, -75.1652),
            "Bakkafjörður, Iceland": (66.0331, -14.8139),
            "Colorado": (39.5501, -105.7821),
            "Ankara, Turkey": (39.9334, 32.8597),
            "Malta": (35.9375, 14.3754),
            "Wilmington, DE": (39.7459, -75.5466),
            "Todmorden, UK": (53.7124, -2.0972),
            "Sundsvall, Sweden": (62.3908, 17.3069),
            "Azkoitia, Spain": (43.1822, -2.3019),
            "Coral Springs, FL": (26.2709, -80.2706),
            "Middletown, CT": (41.5623, -72.6506),
            "Saugerties, NY": (42.0776, -73.9526),
            "Montville, NJ": (40.9007, -74.3632),
            "Melbourne, FL": (28.0836, -80.6081),
            "Erie, PA": (42.1292, -80.0851),
            "Deaux, France": (44.1667, 4.2667),
            "Neratov, Czechia": (50.1667, 16.6333),
            "Medway, UK": (51.3881, 0.5464),
            "Visalia, CA": (36.3302, -119.2921),
            "Perivale, England": (51.5367, -0.3231),
            "Keansburg, NJ": (40.4473, -74.1293),
            "Manitoba, Canada": (53.7609, -98.8139),
            "Fort Walton, FL": (30.4058, -86.6222),
            "Naples, Italy": (40.8518, 14.2681),
            "South Bend, IN": (41.6764, -86.2520),
            "Redmond, WA": (47.6740, -122.1215),
            "Lanzarote, Spain": (29.0469, -13.5900),
            "Laval, France": (48.0733, -0.7700),
            "St. Catharines, Canada": (43.1594, -79.2469),
            "Oregon, OR": (43.8041, -120.5542),
            "Ingolstadt, Germany": (48.7665, 11.4257),
            "Cuneo, Italy": (44.3841, 7.5420),
            "Tula, Russia": (54.2044, 37.6175),
            "Clare, UK": (52.2500, -8.9833),
            "Lillestrøm, Norway": (59.9554, 11.0497),
            "Vermont, VT": (44.5588, -72.5778),
            "West Brookfield, MA": (42.2354, -72.1425),
            "Córdoba, Argentina": (-31.4201, -64.1888),
            "Stockholm, NY": (44.4570, -74.9833),
            "Tiree, Scotland": (56.5000, -6.8833),
            "Molise, Italy": (41.6736, 14.7474),
            "Viterbo, Italy": (42.4208, 12.1078),
            "Fredericksburg, VA": (38.3032, -77.4605),
            "Newark, OH": (40.0581, -82.4013),
            "Trois-Rivières, Canada": (46.3432, -72.5477),
            "Peterborough, NH": (42.8714, -71.9520),
            "Guangzhou, China": (23.1291, 113.2644),
            "Lorraine, Canada": (45.6914, -73.7806),
            "Tbilisi, Georgia": (41.7151, 44.8271),
            "Victoria, Australia": (-37.0201, 144.9646),
            "Bremervörde, Germany": (53.4867, 9.1419),
            "Caen, France": (49.1829, -0.3707),
            "Tamanghasset, Algeria": (22.7833, 5.5167),
            "Toluca, Mexico": (19.2827, -99.6557),
            "Niš, Serbia": (43.3209, 21.8954),
            "Sandvika, Norway": (59.8909, 10.5229),
            "Preston, Australia": (-37.7417, 145.0028),
            "Albany, CA": (37.8869, -122.2978),
            "Vex, Switzerland": (46.2167, 7.4000),
            "Mallorca, Spain": (39.6953, 3.0176),
            "Weirton, WV": (40.4189, -80.5895),
            "Greenfield, MA": (42.5876, -72.5995),
            "South Korea": (35.9078, 127.7669),
            "Hillsboro, OR": (45.5229, -122.9898),
            "Corralitos, CA": (36.9883, -121.8083),
            "Ernée, France": (48.2964, -0.9297),
            "Staffordshire, UK": (52.8783, -2.0522),
            "New Orleans, NO": (29.9511, -90.0715),  # Note: NO should be LA
            "Tarbes, France": (43.2333, 0.0833),
            "Salem, MA": (42.5195, -70.8967),
            "Surabaya, Indonesia": (-7.2575, 112.7521),
            "Mount Kisco, NY": (41.2037, -73.7274),
            "Newquay, UK": (50.4120, -5.0757),
            "California, MD": (38.2973, -76.4966),
            "Wirral, United Kingdom": (53.3727, -3.0738),
            "New Mexico, NM": (34.5199, -105.8701),
            "Totnes, UK": (50.4319, -3.6842),
            "Creswick, Australia": (-37.4236, 143.8947),
            "Rognan, Norway": (67.0953, 15.3903),
            "Toronto, Ontario": (43.6532, -79.3832),
            "Goldendale, WA": (45.8204, -120.8217),
            "Warwick, NY": (41.2568, -74.3593),
            "Blois, France": (47.5933, 1.3289),
            "Edmonton, KY": (36.9803, -85.6111),
            "Stony Brook, NY": (40.9243, -73.1412),
            "Costa Mesa, California": (33.6411, -117.9187),
            "Nottinghamshire, UK": (53.1000, -1.0000),
            "Glastonbury, UK": (51.1489, -2.7142),
            "Ferndown, UK": (50.8022, -1.9015),
            "Nashville, TN, USA": (36.1627, -86.7816),
            "Southend On Sea, UK": (51.5460, 0.7075),
            "Brentwood, TN": (36.0331, -86.7828),
            "Indianapolis, Indiana": (39.7684, -86.1581),
            "Aurich, Germany": (53.4708, 7.4836),
            "Toledo, Ohio": (41.6639, -83.5552),
            "Portland, Maine": (43.6591, -70.2568),
            "Chobham, UK": (51.3500, -0.6167),
            "Philadelphia, Pennsylvania": (39.9526, -75.1652),
            "Maryland, MD": (39.0458, -76.6413),
            "North Carolina, US": (35.7596, -79.0193),
            "Valparaiso, Chile": (-33.0472, -71.6127),
            "Sunderland, UK": (54.9069, -1.3838),
            "NJ": (40.0583, -74.4057),
            "Union City, NJ": (40.6976, -74.0238),
            "Desnogorsk, Russia": (54.1500, 33.2833),
            "Lima, Peru": (-12.0464, -77.0428),
            "Soure, Coimbra, Portugal": (40.0583, -8.6278),
            "Barnsley, England": (53.5526, -1.4797),
            "Cortland, NY": (42.6011, -76.1805),
            "Kentucky, US": (37.8393, -84.2700),
            "Sanremo, Italy": (43.8167, 7.7667),
            "Gelsenkirchen, Germany": (51.5177, 7.0857),
            "Taipei City, Taiwan": (25.0330, 121.5654),
            "South Wales, Australia": (-33.8688, 151.2093),  # New South Wales
            "Unknown": (0.0, 0.0),
            "Vezeronce Curtin, France": (45.6333, 5.5167),
            "Washington, US": (47.7511, -120.7401),
            "Taastrup, Denmark": (55.6506, 12.2997),
            "Andorra la Vella, Andorra": (42.5063, 1.5218),
            "Chisinau, Moldova": (47.0105, 28.8638),
            "Mansfield, PA": (41.8095, -77.0747),
            "Setubal, Portugal": (38.5244, -8.8882),
            "San Marcos, CA": (33.1434, -117.1661),
            "Glendale, AZ": (33.5387, -112.1860),
            "UK, England": (52.3555, -1.1743),
            "Braunschweig, Germany": (52.2689, 10.5268),
            "Corfu, Greece": (39.6243, 19.9217),
            "Alkmaar, Netherlands": (52.6321, 4.7483),
            "Riga, Latvia": (56.9496, 24.1052),
            "Nottinghamshire, England": (53.1000, -1.0000),
            "Milford, CT": (41.2223, -73.0565),
            "St. Gallen, Switzerland": (47.4239, 9.3744),
            "Arrasate, Spain": (43.0833, -2.5167),
            "Langres, France": (47.8600, 5.3333),
            "Evanston, IL": (42.0451, -87.6877),
            "Tiberias, Israel": (32.7956, 35.5311),
            "Kemi, Finland": (65.7369, 24.5631),
            "Päijät-Häme, Finland": (61.0000, 25.6500),
            "Tunisia": (33.8869, 9.5375),
            "Brindisi, Italy": (40.6328, 17.9414),
            "Sendai, Japan": (38.2682, 140.8694),
            "Almada, Portugal": (38.6792, -9.1567),
            "Veneto, Italy": (45.4408, 12.3155),
            "Beveren, Belgium": (51.2122, 4.2536),
            "București, Romania": (44.4268, 26.1025),
            "Ogden, UT": (41.2230, -111.9738),
            "Kingston Upon Hull, UK": (53.7457, -0.3367),
            "Monza, Italy": (45.5845, 9.2744),
            "Quilpué, Chile": (-33.0478, -71.4431),
            "Dnipro, Ukraine": (48.4647, 35.0462),
            "Rouyn-Noranda, Canada": (48.2359, -79.0242),
            "Kajaani, Finland": (64.2278, 27.7285),
            "Kolbotn, Norway": (59.8167, 10.8000),
            "Grafing, Germany": (48.0483, 11.9667),
            "Pennsylvanian, PA": (41.2033, -77.1945),  # Pennsylvania center
            "Jelenia Góra, Poland": (50.8997, 15.7323),
            "Nevada City, CA": (39.2616, -121.0161),
            "Tokyo Japan": (35.6762, 139.6503),
            "Kampen, Netherlands": (52.5558, 5.9114),
            "Runavík, Faroe Islands": (62.1167, -6.7333),
            "Balbigny, France": (45.8208, 4.1917),
            "Uganda": (1.3733, 32.2903),
            "Tel Aviv Yafo, Israel": (32.0853, 34.7818),
            "Greensburg, PA": (40.3014, -79.5389),
            "Willowbrook, IL": (41.7697, -87.9403),
            "Périgueux, France": (45.1833, 0.7167),
            "Salem, NH": (42.7876, -71.2009),
            "Wilson, NC": (35.7213, -77.9155),
            "Taree, Australia": (-31.8986, 152.4553),
            "Dunfermline, UK": (56.0719, -3.4393),
            "Den Helder, Netherlands": (52.9600, 4.7597),
            "Trysil, Norway": (61.3167, 12.2667),
            "Asbury Park, New Jersey": (40.2204, -74.0121),
            "Mulhouse, France": (47.7508, 7.3359),
            "Trier, Germany": (49.7596, 6.6441),
            "Napoli, Italy": (40.8518, 14.2681),
            "Augusta, GA": (33.4735, -82.0105),
            "Perugia, Italy": (43.1107, 12.3908),
            "Levittown, NY": (40.7259, -73.5143),
            "Santa Clara, CA": (37.3541, -121.9552),
            "Bredene, Belgium": (51.2333, 2.9667),
            "Vietnam": (14.0583, 108.2772),
            "Chula Vista, CA": (32.6401, -117.0842),
            "Baden Baden, Germany": (48.7606, 8.2397),
            "Ashford, UK": (51.1465, 0.8750),
            "Denderleeuw, Belgium": (50.8833, 4.0667),
            "Zaporizhia, Ukraine": (47.8388, 35.1396),
            "Springfield, NJ": (40.7001, -74.3171),
            "Valdese, NC": (35.7407, -81.5620),
            "Greater Sudbury, Canada": (46.4917, -80.9930),
            "Arcata, CA": (40.8665, -124.0828),
            "Mo I Rana, Norway": (66.3128, 14.1428),
            "Zhytomyr, Ukraine": (50.2547, 28.6587),
            "Gent, Belgium": (51.0543, 3.7174),
            "Highland, IN": (41.5536, -87.4519),
            "Drummondville, Canada": (45.8833, -72.4833),
            "Murfreesboro, TN": (35.8456, -86.3903),
            "Punta Arenas, Chile": (-53.1638, -70.9171),
            "Toscana, Italy": (43.7711, 11.2486),
            "Valence, France": (44.9333, 4.8833),
            "Old Town, ME": (44.9345, -68.6711),
            "Maitland, Australia": (-32.7333, 151.5583),
            "Dhahran, Saudi Arabia": (26.2361, 50.0393),
            "Dunedin, FL": (28.0198, -82.7873),
            "Valparaiso, IN": (41.4731, -87.0611),
            "Arlington, TX": (32.7357, -97.1081),
            "Pereira, Colombia": (4.8133, -75.6961),
            "Woodbridge, VA": (38.6581, -77.2497),
            "Parkersburg, WV": (39.2667, -81.5615),
            "Kalix, Sweden": (65.8533, 23.1492),
            "Brandenburg, Germany": (52.4125, 12.5316),
            "Söderköping, Sweden": (58.4833, 16.3167),
            "Niort, France": (46.3236, -0.4594),
            "Damascus, Syria": (33.5138, 36.2765),
            "Sayreville, NJ": (40.4590, -74.3610),
            "Paradise, CA": (39.7596, -121.6219),
            "Orem, UT": (40.2969, -111.6946),
            "Veneskoski, Finland": (61.8167, 28.7667),
            "Alba, Italy": (44.7000, 8.0333),
            "Umhlanga, South Africa": (-29.7283, 31.0819),
            "Datteln, Germany": (51.6533, 7.3450),
            "Bruck an der Mur, Austria": (47.4097, 15.2686),
            "Sonora, CA": (37.9830, -120.3821),
            "Arnsberg, Germany": (51.3958, 8.0597),
            "Kalijaga, Indonesia": (-7.8014, 110.3644),
            "Guebwiller, France": (47.9067, 7.2117),
            "Piacenza, Italy": (45.0522, 9.6933),
            "Manitowoc, WI": (44.0886, -87.6576),
            "Delhi, India": (28.7041, 77.1025),
            "Torino, Italy": (45.0703, 7.6869),
            "Corpus Christi, TX": (27.8006, -97.3964),
            "Togo": (8.6195, 0.8248),
            "Lake Grove, NY": (40.8526, -73.1151),
            "Windsor, CA": (38.5471, -122.8167),
            "Red Deer, Canada": (52.2681, -113.8111),
            "Yaroslavl, Russia": (57.6261, 39.8845),
            "Martins Ferry, OH": (40.0967, -80.7245),
            "Galicia, Spain": (42.5751, -8.1339),
            "Viareggio, Italy": (43.8667, 10.2500),
            "Fremont, OH": (41.3503, -83.1216),
            "Gaspé, Canada": (48.8333, -64.4833),
            "Caserta, Italy": (41.0667, 14.3333),
            "Asenovgrad, Bulgaria": (42.0167, 24.8667),
            "Urbana, IL": (40.1106, -88.2073),
            "Medford, NY": (40.8176, -73.0001),
            "Independence, MO": (39.0911, -94.4155),
            "Lecce, Italy": (40.3515, 18.1750),
            "Bretagne, France": (48.2020, -2.9326),
            "Georgia, GA": (32.1656, -82.9001),
            "Keuruu, Finland": (62.2667, 24.7167),
            "Tårnåsen, Norway": (60.0000, 11.0000),
            "Arad, Romania": (46.1667, 21.3167),
            "Kieldrecht, Belgium": (51.3333, 4.2667),
            "Hamden, CT": (41.3959, -72.8968),
            "Liberec, Czechia": (50.7671, 15.0561),
            "Temecula, CA": (33.4936, -117.1484),
            "Askim, Norway": (59.5833, 11.1667),
            "Mykolaiv, Ukraine": (46.9750, 31.9946),
            "İstanbul, Türkiye": (41.0082, 28.9784),
            "Huntington, WV": (38.4192, -82.4452),
            "Scottsdale, AZ": (33.4942, -111.9261),
            "Eboli, Italy": (40.6167, 14.9833),
            "Marília, Brazil": (-22.2139, -49.9458),
            "Weymouth, MA": (42.2180, -70.9404),
            "Lohja, Finland": (60.2486, 24.0653),
            "Genoa, NV": (39.0027, -119.8438),
            "Charleroi, Belgium": (50.4108, 4.4446),
            "Halden, Norway": (59.1242, 11.3878),
            "Älmhult, Sweden": (56.5500, 14.1333),
            "Homyel, Belarus": (52.4345, 30.9754),
            "San Ramon, CA": (37.7799, -121.9780),
            "Swindon, UK": (51.5558, -1.7797),
            "Waterford, MI": (42.6614, -83.3880),
            "Ham, Belgium": (51.1000, 5.1667),
            "San José, CA": (37.3382, -121.8863),
            "Manchester, NH": (42.9956, -71.4548),
            "Val D'Or, Canada": (48.0970, -77.7828),
            "Karlskoga, Sweden": (59.3267, 14.5239),
            "Gronau, Germany": (52.2117, 7.0233),
            "Dewey Humboldt, AZ": (34.5317, -112.2460),
            "Shillong, India": (25.5788, 91.8933),
            "Brasília, Brazil": (-15.8267, -47.9218),
            "Agnone, Italy": (41.8000, 14.3833),
            "Rælingen, Norway": (59.9333, 11.0667),
            "Rio de Janeiro, Brazil": (-22.9068, -43.1729),
            "Baden, Switzerland": (47.4725, 8.3061),
            "Orléans, France": (47.9029, 1.9093),
            "Pittsfield, MA": (42.4501, -73.2454),
            "Lublin, Poland": (51.2465, 22.5684),
            "Burbank, CA": (34.1808, -118.3090),
            "Maple Ridge, Canada": (49.2194, -122.5987),
            "Stockholm, NJ": (41.0912, -74.5382),
            "Sosnowiec, Poland": (50.2864, 19.1043),
            "Ostend, Belgium": (51.2167, 2.9167),
            "Passaic, NJ": (40.8568, -74.1285),
            "Bend, OR": (44.0582, -121.3153),
            "Waterford, Ireland": (52.2593, -7.1101),
            "Lommel, Belgium": (51.2314, 5.3133),
            "İstanbul, Turkey": (41.0082, 28.9784),
            "Somerset, UK": (51.1050, -2.9260),
            "Ōtepoti, New Zealand": (-45.8788, 170.5028),
            "Athens, AL": (34.8026, -86.9722),
            "Brno, Czechia": (49.1951, 16.6068),
            "Montreal, QC": (45.5017, -73.5673),
            "Brooklyn, New York": (40.6782, -73.9442),
            "London, England": (51.5074, -0.1278),
            "England / US / Germany": (40.0, -10.0),
            "La Rochelle, France": (46.1603, -1.1511),
            "Cecina, Italy": (43.3089, 10.5147),
            "Monroe, CT": (41.3326, -73.2088),
            "Bronx, NY": (40.8448, -73.8648),
            "Long Island, NY": (40.7891, -73.1350),
            "Allentown, PA": (40.6084, -75.4902),
            "Lugo, Spain": (43.0097, -7.5567),
            "Lakefield, Canada": (44.4333, -78.2667),
            "Ernee, France": (48.2950, -0.9325),
            "Lexington, KY": (38.0406, -84.5037),
            "Viken, Norway": (59.7414, 10.2045),
            "Tyrol, Austria": (47.2692, 11.4041),
            "Fort Lauderdale, FL": (26.1224, -80.1373),
            "Walla Walla, WA": (46.0646, -118.3430),
            "Lewes, UK": (50.8738, 0.0096),
            "Blackpool, UK": (53.8175, -3.0357),
            "Dortmund, Germany": (51.5136, 7.4653),
            "Alessandria, Italy": (44.9137, 8.6153),
            "Norrköping, Sweden": (58.5877, 16.1924),
            "Vancouver, WA": (45.6387, -122.6615),
            "Kennett, MO": (36.2362, -90.0551),
            "Edinburgh, UK": (55.9533, -3.1883),
            "Treviso, Italy": (45.6669, 12.2428),
            "Ripon, Canada": (45.8000, -75.1167),
            "Albone, Italy": (44.0333, 8.2167),
            "Medford, OR": (42.3265, -122.8756),
            "Taos, NM": (36.4072, -105.5731),
            "Bochum, Germany": (51.4818, 7.2162),
            "Hollywood, CA": (34.0928, -118.3287),
            "Worthing, UK": (50.8148, -0.3728),
            "Orange County, CA": (33.7175, -117.8311),
            "Bakersfield, CA": (35.3733, -119.0187),
            "Falmouth, UK": (50.1538, -5.0718),
            "Lutsk, Ukraine": (50.7472, 25.3254),
            "Santa Maria, CA": (34.9530, -120.4357),
            "Rakovnik, Czech Republic": (50.1033, 13.7331),
            "Holyoke, MA": (42.2043, -72.6162),
            "Cedar Rapids, IA": (41.9779, -91.6656),
            "Aberdeen, UK": (57.1497, -2.0943),
            "Segovia, Spain": (40.9429, -4.1088),
            "Quezon City, Philippines": (14.6760, 121.0437),
            "Abalak, Niger": (15.4500, 6.2833),
            "Dundee, UK": (56.4620, -2.9707),
            "Bruzzelle, Italy": (38.4333, 16.1667),
            "Jerusalem, Israel": (31.7683, 35.2137),
            "Southington, CT": (41.5959, -72.8773),
            "Middletown, NY": (41.4459, -74.4229),
            "Tyler, TX": (32.3513, -95.3011),
            "Shimla, India": (31.1048, 77.1734),
            "Bulle, Switzerland": (46.6167, 7.0500),
            "Borås, Sweden": (57.7210, 12.9401),
            "Harrogate, UK": (53.9921, -1.5418),
            "Walsall, UK": (52.5862, -1.9829),
            "Calabasas, CA": (34.1378, -118.6382),
            "St. Augustine, FL": (29.9012, -81.3124),
            "Pasadena, CA": (34.1478, -118.1445),
            "West Somerville, MA": (42.3876, -71.1165),
            "Dartmouth, MA": (41.5993, -70.9802),
            "Gilbert, AZ": (33.3528, -111.7890),
            "Zug, Switzerland": (47.1667, 8.5167),
            "Toccoa, GA": (34.5773, -83.3321),
            "Manhattan, NY": (40.7831, -73.9712),
            "Yellowknife, Canada": (62.4540, -114.3718),
            "Beograd, Serbia": (44.7866, 20.4489),
            "Delft, Netherlands": (52.0116, 4.3571),
            "Kitchener, Canada": (43.4516, -80.4925),
            "Katoomba, Australia": (-33.7125, 150.3117),
            "Vimmerby, Sweden": (57.6667, 15.8500),
            "Aberfeldy, UK": (56.6217, -3.8667),
            "St.Paul, MN": (44.9537, -93.0900),
            "Philippines / South Korea": (20.0, 125.0),
            "Indiana, IN": (40.2672, -86.1349),
            "Washington, WA": (47.7511, -120.7401),
            "Trollhättan, Sweden": (58.2836, 12.2886),
            "Landshut, Germany": (48.5375, 12.1514),
            "San Salvo, Italy": (42.0500, 14.7333),
            "Kaskinen, Finland": (62.3833, 21.2167),
            "Málaga, Spain": (36.7213, -4.4214),
            "Lightning Ridge, Australia": (-29.4239, 147.9775),
            "Siloam Springs, AR": (36.1881, -94.5405),
            "Seesen, Germany": (51.8942, 10.1775),
            "Hanover, Germany": (52.3759, 9.7320),
            "Ludvika, Sweden": (60.1497, 15.1883),
            "Esztergom, Hungary": (47.7833, 18.7333),
            "China": (35.8617, 104.1954),
            "Spokane, Washington": (47.6588, -117.4260),
            "Arlington, VA": (38.8816, -77.0910),
            "Boston, Massachusetts": (42.3601, -71.0589),
            "Springfield, Massachusetts": (42.1015, -72.5898),
            "Cheltenham, UK": (51.8994, -2.0783),
            "Lappeenranta, Finland": (61.0587, 28.1887),
            "Cangas, Spain": (42.2667, -8.7833),
            "Bilzen, Belgium": (50.8742, 5.5186),
            "Hong Kong": (22.3193, 114.1694),
            "Granby, Canada": (45.4000, -72.7333),
            "Bastia, France": (42.7028, 9.4497),
            "Rhenen, Netherlands": (51.9572, 5.5672),
            "Mumbai, India": (19.0760, 72.8777),
            "Soragna, Italy": (44.9333, 10.1167),
            "Virginia, United States": (37.4316, -78.6569),
            "Lapua, Finland": (62.9667, 23.0000),
            "California, US": (36.7783, -119.4179),
            "Avesta, Sweden": (60.1458, 16.1683),
            "Oak Park, IL": (41.8850, -87.7845),
            "Moorsele, Belgium": (50.8333, 3.0667),
            "Kuala Lumpur, Malaysia": (3.1390, 101.6869),
            "Westfield, Massachusetts": (42.1251, -72.7495),
            "Loimaa, Finland": (62.2550, 23.0550),
            "Vitoria Gasteiz, Spain": (42.8467, -2.6716),
            "West Swanzey, NH": (42.8723, -72.3203),
            "Derby, UK": (52.9225, -1.4746),
            "Freiberg, Germany": (50.9146, 13.3421),
            "Leon, Mexico": (21.1250, -101.6860),
            "Olten, Switzerland": (47.3500, 7.9000),
            "Yekaterinburg, Russia": (56.8389, 60.6057),
            "Pretoria, South Africa": (-25.7479, 28.2293),
            "San Diego, California": (32.7157, -117.1611),
            "Venray, Netherlands": (51.5253, 5.9750),
            "Uzhhorod, Ukraine": (48.6208, 22.2879),
            "Avignon, France": (43.9493, 4.8055),
            "Kungälv, Sweden": (57.8706, 11.9803),
            "Dunfermline, Scotland": (56.0719, -3.4393),
            "Tempe, AZ": (33.4255, -111.9400),
            "Heidenheim, Germany": (48.6761, 10.1522),
            "Riihimäki, Finland": (60.7394, 24.7728),
            "Wilmington, NC": (34.2257, -77.9447),
            "England, UK": (52.3555, -1.1743),
            "Fulda, Germany": (50.5558, 9.6808),
            "Pulawy, Poland": (51.4167, 21.9694),
            "Buena Park, CA": (33.8675, -117.9981),
            "Ossi, Italy": (40.7167, 8.6000),
            "Denton, Texas": (33.2148, -97.1331),
            "Larissa, Greece": (39.6390, 22.4191),
            "Bancroft, Canada": (45.0578, -77.8578),
            "Trelleborg, Sweden": (55.3756, 13.1567),
            "Biella, Italy": (45.5628, 8.0581),
            "Helsingborg, Sweden": (56.0465, 12.6945),
            "Falkenberg, Sweden": (56.9055, 12.4914),
            "Enschede, Netherlands": (52.2215, 6.8937),
            "Colorado Springs, CO": (38.8339, -104.8214),
            "Pisa, Italy": (43.7229, 10.4017),
            "Uruguay": (-32.5228, -55.7658),
            "Greensboro, NC": (36.0726, -79.7920),
            "Umag, Croatia": (45.4328, 13.5222),
            "Arvada, CO": (39.8028, -105.0875),
            "Hermosa Beach, CA": (33.8622, -118.3995),
            "Akershus, Norway": (60.0000, 11.0000),
            "Bethlehem, PA": (40.6259, -75.3705),
            "Coquimbo, Chile": (-29.9533, -71.3436),
            "North Muskegon, MI": (43.2550, -86.2684),
            "Jackson, MI": (42.2459, -84.4013),
            "Balingen, Germany": (48.2750, 8.8511),
            "Szeged, Hungary": (46.2530, 20.1414),
            "Bizkaia, Spain": (43.2630, -2.9350),
            "Mammoth Lakes, CA": (37.6485, -118.9721),
            "Secaucus, NJ": (40.7895, -74.0565),
            "Trinidad and Tobago": (10.6918, -61.2225),
            "Pontarlier, France": (46.9042, 6.3558),
            "Sudbury, Canada": (46.4917, -80.9930),
            "Kortrijk, Belgium": (50.8279, 3.2647),
            "Essex, UK": (51.7923, 0.5417),
            "Texas, US": (31.9686, -99.9018),
            "Halmstad, Sweden": (56.6745, 12.8576),
            "Tychy, Poland": (50.1357, 18.9650),
            "Cary, IL": (42.2120, -88.2384),
            "Troy, NY": (42.7284, -73.6918),
            "Florence, Italy": (43.7696, 11.2558),
            "Lismore, Australia": (-28.8142, 153.2789),
            "Kolkata, India": (22.5726, 88.3639),
            "Agen, France": (44.2033, 0.6164),
            "Bennekom, Netherlands": (51.9978, 5.6756),
            "Tijuana, Mexico": (32.5149, -117.0382),
            "Brașov, Romania": (45.6580, 25.6012),
            "Kaiserslautern, Germany": (49.4447, 7.7689),
            "Kansas City, KS": (39.1142, -94.6275),
            "Flensburg, Germany": (54.7836, 9.4321),
            "Clementon, NJ": (39.8115, -74.9832),
            "Apple Valley, CA": (34.5008, -117.1859),
            "Clermont Ferrand, France": (45.7772, 3.0870),
            "Hokkaido, Japan": (43.0642, 141.3469),
            "Mission Viejo, CA": (33.6000, -117.6720),
            "Tennessee, US": (35.5175, -86.5804),
            "Saale, Germany": (51.4969, 11.9697),
            "Drøbak, Norway": (59.6608, 10.6272),
            "Valenciennes, France": (50.3589, 3.5239),
            "Clarksville, TN": (36.5298, -87.3595),
            "Blumenau, Brazil": (-26.9194, -49.0661),
            "Sanok, Poland": (49.5556, 22.2056),
            "Ciudad Real, Spain": (38.9848, -3.9273),
            "Prague, Czech Republic": (50.0755, 14.4378),
            "Vilnius, Lithuania": (54.6872, 25.2797),
            "Kitee, Finland": (62.1000, 30.1333),
            "Bonn, Germany": (50.7374, 7.0982),
            "Cramlington, UK": (55.0861, -1.5878),
            "Lexington, NC": (35.8240, -80.2534),
            "Woking, UK": (51.3168, -0.5601),
            "Arizona, United States": (34.0489, -111.0937),
            "Rimini, Italy": (44.0678, 12.5695),
            "Essen, Germany": (51.4556, 7.0116),
            "Eisenberg, Germany": (50.9667, 11.9000),
            "Ludwigsburg, Germany": (48.8974, 9.1916),
            "Linz, Austria": (48.3069, 14.2858),
            "Cajamarca, Peru": (-7.1611, -78.5125),
            "Ferrara, Italy": (44.8381, 11.6198),
            "Skellefteå, Sweden": (64.7506, 20.9525),
            "Novi Sad, Serbia": (45.2671, 19.8335),
            "Venice, FL": (27.0998, -82.4543),
            "Jakobstad, Finland": (63.6747, 22.7028),
            "Kymenlaakso, Finland": (60.8667, 26.7000),
            "Cedarville, CA": (41.5301, -120.1730),
            "Hayward, CA": (37.6688, -122.0808),
            "Canton, OH": (40.7989, -81.3784),
            "Wheeling, WV": (40.0640, -80.7209),
            "Vantaa, Finland": (60.2934, 25.0378),
            "Aguascalientes, Mexico": (21.8853, -102.2916),
            "Cresskill, NJ": (40.9412, -73.9596),
            "Windsor, UK": (51.4791, -0.6095),
            "London, United Kingdom": (51.5074, -0.1278),
            "Gimbsheim, Germany": (49.7000, 8.3333),
            "Muncie, IN": (40.1934, -85.3863),
            "Busan, South Korea": (35.1796, 129.0756),
            "Lörrach, Germany": (47.6167, 7.6611),
            "Ostrobothnia, Finland": (63.1000, 21.6167),
            "Bello, Colombia": (6.3370, -75.5553),
            "Moberly, MO": (39.4183, -92.4382),
            "Senec, Slovakia": (48.2200, 17.4000),
            "Bucharest, Romania": (44.4268, 26.1025),
            "Topeka, KS": (39.0558, -95.6890),
            "Elkton, MD": (39.6068, -75.8333),
            "Lake Forest, CA": (33.6469, -117.6892),
            "Nummela, Finland": (60.3333, 24.3333),
            "Occitanie, France": (43.5928, 3.2583),
            "Varese, Italy": (45.8206, 8.8250),
            "Delitzsch, Germany": (51.5256, 12.3403),
            "İstanbul, Turkey": (41.0082, 28.9784),
            "Gulfport, MS": (30.3674, -89.0928),
            "Fresno, CA": (36.7378, -119.7871),
            "Pomona, CA": (34.0551, -117.7499),
            "Dánszentmiklós, Hungary": (47.0333, 19.5833),
            "Wilkes-Barre, PA": (41.2459, -75.8813),
            "Hudiksvall, Sweden": (61.7281, 17.1069),
            "Ogden, Utah": (41.2230, -111.9738),
            "Boyertown, PA": (40.3337, -75.6368),
            "Dordrecht, Netherlands": (51.8133, 4.6700),
            "Berkshire, UK": (51.4543, -1.0320),
            "Aix En Provence, France": (43.5297, 5.4474),
            "Volkhov, Russia": (59.9272, 32.3333),
            "Winston Salem, NC": (36.0999, -80.2442),
            "Zwickau, Germany": (50.7197, 12.4961),
            "Tomsk, Russia": (56.4977, 84.9744),
            "Yerevan, Armenia": (40.1792, 44.4991),
            "Charleston, WV": (38.3498, -81.6326),
            "North Savo, Finland": (63.0833, 27.6833),
            "Rosenheim, Germany": (47.8564, 12.1272),
            "Dalarna, Sweden": (60.6000, 15.0000),
            "Brooklyn, MI": (42.1059, -84.2483),
            "Zlin Region, Czechia": (49.2269, 17.6667),
            "Cape Girardeau, MO": (37.3059, -89.5181),
            "Medellín, Colombia": (6.2476, -75.5658),
            "Oxford Charter, MI": (42.8247, -83.2646),
            "Fasano, Italy": (40.8333, 17.3667),
            "Turnhout, Belgium": (51.3225, 4.9436),
            "Pieria, Greece": (40.3000, 22.5000),
            "Cham, Germany": (49.2231, 12.6619),
            "Shelton, WA": (47.2151, -123.0982),
            "Sherbrooke, Canada": (45.4042, -71.8929),
            "St. John'S, Canada": (47.5615, -52.7126),
            "Westminster, MD": (39.5751, -76.9958),
            "Surrey, UK": (51.3148, -0.5600),
            "Geneva, IL": (41.8876, -88.3054),
            "San Marcos, TX": (29.8833, -97.9414),
            "Antioch, CA": (38.0049, -121.8058),
            "Florida, MO": (39.4889, -91.7918),
            "Mount Sinai, NY": (40.9473, -73.0168),
            "Sicilia, Italy": (37.5999, 14.0154),
            "Viitasaari, Finland": (63.0833, 25.8500),
            "Rosario, Argentina": (-32.9442, -60.6505),
            "Alberta, Canada": (53.9333, -116.5765),
            "Middlefield, CT": (41.5123, -72.7162),
            "San Juan, Puerto Rico": (18.4655, -66.1057),
            "Bristol, PA": (40.1007, -74.8515),
            "KL, India": (28.7041, 77.1025),
            "Bedfordshire, UK": (52.0050, -0.4550),
            "Wevelgem, Belgium": (50.8000, 3.1833),
            "Peiting, Germany": (47.8000, 10.9167),
            "North Augusta, SC": (33.5018, -81.9651),
            "Grayslake, IL": (42.3414, -88.0418),
            # Phase 7: Final comprehensive location additions for 97-98% coverage
            # Canadian province abbreviations (high frequency)
            "Toronto, ON": (43.6532, -79.3832),
            "Calgary, AB": (51.0447, -114.0719),
            "Ottawa, ON": (45.4215, -75.6972),
            "Winnipeg, MB": (49.8951, -97.1384),
            "Montreal, QC": (45.5017, -73.5673),
            "Montréal, QC": (45.5017, -73.5673),
            "Québec City, QC": (46.8139, -71.2080),
            "Québec, QC": (46.8139, -71.2080),
            "Quebec City, QC": (46.8139, -71.2080),
            "Vancouver, BC": (49.2827, -123.1207),
            "Hamilton, ON": (43.2557, -79.8711),
            "Waterloo, ON": (43.4643, -80.5204),
            "Kitchener, ON": (43.4516, -80.4925),
            "London, ON": (42.9849, -81.2453),
            "Whitby, ON": (43.8975, -78.9429),
            "Cambridge, ON": (43.3616, -80.3144),
            "Oakville, ON": (43.4675, -79.6877),
            "Kingston, Ontario": (44.2312, -76.4860),
            "Longueuil, QC": (45.5312, -73.5182),
            "Sudbury, ON": (46.4917, -80.9930),
            "Saskatoon, SK": (52.1332, -106.6700),
            "Victoria, BC": (48.4284, -123.3656),
            "Red Deer, AB": (52.2681, -113.8111),
            "Barrie, Canada": (44.3894, -79.6903),
            "Lakefield, ON": (44.4333, -78.2667),
            "Regina, SK": (50.4452, -104.6189),
            "Kelowna, BC": (49.8880, -119.4960),
            "Nanaimo, BC": (49.1659, -123.9401),
            "Lethbridge, AB": (49.6942, -112.8328),
            "Edmonton, AB": (53.5461, -113.4938),
            "Scarborough, ON": (43.7764, -79.2318),
            "Mississauga, ON": (43.5890, -79.6441),
            "Brampton, ON": (43.7315, -79.7624),
            "Markham, ON": (43.8561, -79.3370),
            "Oshawa, ON": (43.8971, -78.8658),
            "Burlington, ON": (43.3255, -79.7990),
            # Swedish cities with special characters
            "Göteborg, Sweden": (57.7089, 11.9746),
            "Jönköping, Sweden": (57.7826, 14.1618),
            "Eskilstuna, Sweden": (59.3710, 16.5077),
            "Karlstad, Sweden": (59.3793, 13.5036),
            "Säffle, Sweden": (59.1333, 12.9333),
            "Skövde, Sweden": (58.3912, 13.8454),
            "Vansbro, Sweden": (60.5333, 14.2667),
            "Stenungsund, Sweden": (58.0708, 11.8236),
            "Enköping, Sweden": (59.6356, 17.0778),
            "Norrbotten, Sweden": (66.8309, 20.3987),
            "Gävle, Sweden": (60.6749, 17.1413),
            "Borås, Sweden": (57.7210, 12.9401),
            "Västerås, Sweden": (59.6099, 16.5448),
            "Örebro, Sweden": (59.2753, 15.2134),
            # Regional areas (centralized coordinates)
            "Bay Area, CA": (37.8000, -122.4000),
            "Twin Cities, MN": (44.9500, -93.1000),
            "Tampa Bay, FL": (27.9500, -82.5000),
            "Hampton Roads, VA": (36.8500, -76.3000),
            "Western MA, CT": (42.1000, -72.6000),
            "Tri-Cities, WA": (46.2396, -119.1314),
            "Quad Cities, IL": (41.5236, -90.5776),
            # Greek and special character locations
            "Αθήνα, Greece": (37.9838, 23.7275),
            # Common typos and variants
            "Detroid, MI": (42.3314, -83.0458),  # Detroit
            "Sao Paolo, Brazil": (-23.5505, -46.6333),  # São Paulo
            "Virgina, VA": (37.4316, -78.6569),  # Virginia
            "Minnasota": (46.7296, -94.6859),  # Minnesota
            "Pennsylvanian, PA": (41.2033, -77.1945),  # Pennsylvania
            # State/province abbreviations only
            "CA": (36.7783, -119.4179),  # California center
            "QC": (52.9399, -73.5491),  # Quebec center
            "NJ": (40.0583, -74.4057),  # New Jersey center
            "ON": (51.2538, -85.3232),  # Ontario center
            "AB": (53.9333, -116.5765),  # Alberta center
            "MB": (53.7609, -98.8139),  # Manitoba center
            "BC": (53.7267, -127.6476),  # British Columbia center
            # City-country corrections (UK/England/Scotland/Ireland)
            "Perth, Scotland": (56.3958, -3.4374),
            "Cork, UK": (51.8979, -8.4705),  # Actually Ireland
            "Hamilton, UK": (55.7782, -4.0309),  # Scotland
            "Dublin, UK": (53.3498, -6.2603),  # Actually Ireland
            "Manchester, England": (53.4808, -2.2426),
            "Liverpool, England": (53.4084, -2.9916),
            "Bristol, England": (51.4545, -2.5879),
            "Leeds, England": (53.8008, -1.5491),
            "Portsmouth, England": (50.8198, -1.0880),
            "Southampton, England": (50.9097, -1.4044),
            "Reading, England": (51.4543, -0.9781),
            "Bournemouth, England": (50.7192, -1.8808),
            "Blackpool, England": (53.8175, -3.0357),
            "Dundee, Scotland": (56.4620, -2.9707),
            "Aberdeen, Scotland": (57.1497, -2.0943),
            "Inverness, Scotland": (57.4778, -4.2247),
            "Limerick, Ireland": (52.6638, -8.6267),
            "Galway, Ireland": (53.2707, -9.0568),
            "Waterford, Ireland": (52.2593, -7.1101),
            # Multi-word city names
            "Ciudad de México, Mexico": (19.4326, -99.1332),
            "San José, CR": (9.9281, -84.0907),  # Costa Rica
            "San Salvador, El Salvador": (13.6929, -89.2182),
            "Sankt Petersburg, Russia": (59.9311, 30.3609),
            "Rio De Janeiro, Brazil": (-22.9068, -43.1729),
            "Buenos Aires, Argentina": (-34.6037, -58.3816),
            "São Paulo, Brazil": (-23.5505, -46.6333),
            # Additional missing US cities and variants
            "San Jose, California": (37.3382, -121.8863),
            "Los Angeles, California": (34.0522, -118.2437),
            "San Diego, California": (32.7157, -117.1611),
            "San Francisco, California": (37.7749, -122.4194),
            "Sacramento, California": (38.5816, -121.4944),
            "Fresno, California": (36.7378, -119.7871),
            "Long Beach, California": (33.7701, -118.1937),
            "Oakland, California": (37.8044, -122.2712),
            "Bakersfield, California": (35.3733, -119.0187),
            "Anaheim, California": (33.8366, -117.9143),
            "Santa Ana, California": (33.7455, -117.8677),
            "Riverside, California": (33.9533, -117.3962),
            "Stockton, California": (37.9577, -121.2908),
            "Irvine, California": (33.6846, -117.8265),
            "New York, New York": (40.7128, -74.0060),
            "Brooklyn, New York": (40.6782, -73.9442),
            "Queens, New York": (40.7282, -73.7949),
            "Bronx, New York": (40.8448, -73.8648),
            "Manhattan, New York": (40.7831, -73.9712),
            "Buffalo, New York": (42.8864, -78.8784),
            "Rochester, New York": (43.1566, -77.6088),
            "Syracuse, New York": (43.0481, -76.1474),
            "Albany, New York": (42.6526, -73.7562),
            "Chicago, Illinois": (41.8781, -87.6298),
            "Houston, Texas": (29.7604, -95.3698),
            "Philadelphia, Pennsylvania": (39.9526, -75.1652),
            "Phoenix, Arizona": (33.4484, -112.0740),
            "San Antonio, Texas": (29.4241, -98.4936),
            "Dallas, Texas": (32.7767, -96.7970),
            "Austin, Texas": (30.2672, -97.7431),
            "Jacksonville, Florida": (30.3322, -81.6557),
            "Fort Worth, Texas": (32.7555, -97.3308),
            "Columbus, Ohio": (39.9612, -82.9988),
            "Charlotte, North Carolina": (35.2271, -80.8431),
            "Indianapolis, Indiana": (39.7684, -86.1581),
            "Seattle, Washington": (47.6062, -122.3321),
            "Denver, Colorado": (39.7392, -104.9903),
            "El Paso, Texas": (31.7619, -106.4850),
            "Detroit, Michigan": (42.3314, -83.0458),
            "Nashville, Tennessee": (36.1627, -86.7816),
            "Memphis, Tennessee": (35.1495, -90.0490),
            "Portland, Oregon": (45.5152, -122.6784),
            "Oklahoma City, Oklahoma": (35.4676, -97.5164),
            "Las Vegas, Nevada": (36.1699, -115.1398),
            "Louisville, Kentucky": (38.2527, -85.7585),
            "Baltimore, Maryland": (39.2904, -76.6122),
            "Milwaukee, Wisconsin": (43.0389, -87.9065),
            "Albuquerque, New Mexico": (35.0844, -106.6504),
            "Tucson, Arizona": (32.2226, -110.9747),
            "Mesa, Arizona": (33.4152, -111.8315),
            # Additional European cities
            "Amsterdam, Netherlands": (52.3676, 4.9041),
            "Rotterdam, Netherlands": (51.9225, 4.47917),
            "The Hague, Netherlands": (52.0705, 4.3007),
            "Utrecht, Netherlands": (52.0907, 5.1214),
            "Eindhoven, Netherlands": (51.4416, 5.4697),
            "Tilburg, Netherlands": (51.5555, 5.0913),
            "Groningen, Netherlands": (53.2194, 6.5665),
            "Almere, Netherlands": (52.3508, 5.2647),
            "Breda, Netherlands": (51.5719, 4.7683),
            "Nijmegen, Netherlands": (51.8426, 5.8528),
            # Phase 8: Additional missing locations from latest error log
            # Canadian province full names
            "Waterloo, Ontario": (43.4643, -80.5204),
            "Vancouver, British Columbia": (49.2827, -123.1207),
            "Winnipeg, Manitoba": (49.8951, -97.1384),
            "Regina, Saskatchewan": (50.4452, -104.6189),
            "Jonquière, Quebec": (48.4161, -71.2489),
            "Montreal, Québec": (45.5017, -73.5673),
            "Québec, Quebec": (46.8139, -71.2080),
            "Sault Ste. Marie, ON": (46.5333, -84.3333),
            "Cambridge, Canada": (43.3616, -80.3144),
            "Whitehorse, YT": (60.7212, -135.0568),
            "Yarmouth, NS": (43.8374, -66.1175),
            "Brockville, Canada": (44.5903, -75.6838),
            "Kenora, Canada": (49.7667, -94.4897),
            "Toronto, CA": (43.6532, -79.3832),
            # US state abbreviations
            "LA": (30.9843, -91.9623),  # Louisiana center
            "TX": (31.9686, -99.9018),  # Texas center
            "FL": (27.6648, -81.5158),  # Florida center
            "MN": (46.7296, -94.6859),  # Minnesota center
            "NY": (42.1657, -74.9481),  # New York center
            "NC": (35.7596, -79.0193),  # North Carolina center
            "CT": (41.6032, -73.0877),  # Connecticut center
            "CO": (39.5501, -105.7821),  # Colorado center
            "AK": (64.2008, -149.4937),  # Alaska center
            # UK regions and variants
            "Scotland, UK": (56.4907, -4.2026),
            "Brighton, England": (50.8225, -0.1372),
            "Nottingham, England": (52.9548, -1.1581),
            "Kingston Upon Thames, England": (51.4123, -0.3006),
            "Rochester, England": (51.3879, 0.5040),
            "West Yorkshire, England": (53.7970, -1.5476),
            "Lancashire, England": (53.7632, -2.7044),
            "Staffordshire, England": (52.8804, -2.0441),
            "Milton Keynes, England": (52.0406, -0.7594),
            "Leighton Buzzard, England": (51.9166, -0.6620),
            "Wendover, England": (51.7611, -0.7396),
            "St. Ives, England": (52.3317, -0.0761),
            "Dover, England": (51.1279, 1.3134),
            "Ayelsbury, England": (51.8168, -0.8124),
            "Latchford, England": (53.3890, -2.5552),
            "Maryport, England": (54.7138, -3.4952),
            "Hampshire, UK": (51.0577, -1.3081),
            "Midlands, UK": (52.5690, -1.4746),
            "North Wales, UK": (53.2000, -3.8000),
            "Yorkshire, UK": (53.9590, -1.0815),
            "Derbyshire, UK": (53.1230, -1.5632),
            "Shropshire, UK": (52.7071, -2.7467),
            "Dorset, UK": (50.7489, -2.3447),
            "Lincoln, UK": (53.2307, -0.5406),
            "Newcastle Upon Tyne, UK": (54.9783, -1.6178),
            "Horsham, UK": (51.0629, -0.3260),
            "Hornsea, UK": (53.9113, -0.1672),
            "Betley, UK": (53.0433, -2.3667),
            "Torquay, UK": (50.4619, -3.5253),
            "Wickford, UK": (51.6114, 0.5239),
            "Stirling, UK": (56.1165, -3.9369),
            "Chesham, UK": (51.7055, -0.6111),
            "Londonderry, UK": (54.9966, -7.3086),
            "Wolverhampton, UK": (52.5862, -2.1285),
            "Dudley, UK": (52.5120, -2.0890),
            "Plymouth, UK": (50.3755, -4.1427),
            "Wrexham, UK": (53.0462, -2.9931),
            "Ipswich, UK": (52.0594, 1.1556),
            "Peterborough, UK": (52.5695, -0.2405),
            "Chichester, UK": (50.8367, -0.7792),
            "Poole, UK": (50.7150, -1.9872),
            "Bridgwater, UK": (51.1278, -2.9931),
            "Macclesfield, UK": (53.2603, -2.1256),
            "Stafford, UK": (52.8067, -2.1167),
            "Caerdydd, UK": (51.4816, -3.1791),  # Cardiff Welsh name
            # Australian state abbreviations
            "NSW, Australia": (-33.8688, 151.2093),  # New South Wales - Sydney
            "SA, Australia": (-34.9285, 138.6007),  # South Australia - Adelaide
            "Brisbane, Queensland, Australia": (-27.4698, 153.0251),
            "Aberdeen, Australia": (-32.1667, 151.2333),
            "Sydney, NW": (-33.8688, 151.2093),  # Typo for NSW
            "Norseman, Australia": (-32.2019, 121.7778),
            "Dunsborough, Australia": (-33.6144, 115.1033),
            "Tamworth, Australia": (-31.0927, 150.9298),
            # Additional European cities
            "Krakow, Poland": (50.0647, 19.9450),
            "Łódź, Poland": (51.7592, 19.4560),
            "Będzin, Poland": (50.3270, 19.1280),
            "Bielsko Biała, Poland": (49.8224, 19.0446),
            "Łomża, Poland": (53.1782, 22.0589),
            "Szczytno, Poland": (53.5625, 20.9897),
            "Bydgoszcz, Poland": (53.1235, 18.0084),
            "Toruń, Poland": (53.0138, 18.5984),
            "Piekary Slaskie, Poland": (50.3825, 18.9469),
            "Poznan, Poland": (52.4064, 16.9252),
            # Finland
            "Lemi, Finland": (61.0833, 27.8000),
            "Joensuu, Finland": (62.6010, 29.7636),
            "Rauma, Finland": (61.1272, 21.5113),
            "Sumiainen, Finland": (62.6667, 25.2333),
            # Swiss cities
            "Monthey, Switzerland": (46.2531, 6.9589),
            "Moutier, Switzerland": (47.2778, 7.3706),
            "Oekingen, Switzerland": (47.3077, 7.8846),
            "Sion, Switzerland": (46.2334, 7.3594),
            "Dulliken, Switzerland": (47.3542, 7.9075),
            "Muotathal, Switzerland": (46.9778, 8.7531),
            # Netherlands with special handling
            "Den Haag, Netherlands": (52.0705, 4.3007),
            "Rozenburg, Netherlands": (51.9042, 4.2470),
            "Waddinxveen, Netherlands": (52.0406, 4.6514),
            "Katwijk, Netherlands": (52.2042, 4.4181),
            "Roermond, Netherlands": (51.1942, 5.9875),
            "Boxtel, Netherlands": (51.5906, 5.3281),
            "Sint-Michielsgestel, Netherlands": (51.6417, 5.3514),
            "Amstelveen, Netherlands": (52.3008, 4.8631),
            "Beverwijk, Netherlands": (52.4833, 4.6569),
            "Maassluis, Netherlands": (51.9225, 4.2506),
            "Weert, Netherlands": (51.2514, 5.7069),
            "Herwijnen, Netherlands": (51.8317, 5.1403),
            "Rijsbergen, Netherlands": (51.5167, 4.7000),
            "ZH, Netherlands": (52.1601, 4.4970),  # Zuid-Holland
            # Spanish cities
            "Albacere, Spain": (38.9944, -1.8583),  # Albacete typo
            "Alicante, Spain": (38.3452, -0.4810),
            "Mataro, Spain": (41.5400, 2.4442),
            "Durango, Spain": (43.1703, -2.6308),
            "Granada, Spain": (37.1773, -3.5986),
            "Almería, Spain": (36.8381, -2.4597),
            "León, Spain": (42.5987, -5.5671),
            "Malaga, Spain": (36.7213, -4.4214),
            "El Mas De Flors, Spain": (41.5000, 1.0000),
            # Italian cities
            "Montecarlo, Italy": (43.8500, 10.6667),
            "Brecia, Italy": (45.5416, 10.2118),  # Brescia typo
            "Fabriano, Italy": (43.3358, 12.9047),
            "Lazio, Italy": (41.8719, 12.5674),
            "Bressanone, Italy": (46.7158, 11.6558),
            "Siena, Italy": (43.3188, 11.3308),
            "Antequera, Spain": (37.0194, -4.5597),
            "Cervia, Italy": (44.2619, 12.3478),
            "Camparada, Italy": (45.6833, 9.3500),
            "Beneveneto, Italy": (41.1297, 14.7824),  # Benevento typo
            "Villorba, Italy": (45.7333, 12.2333),
            "Bassano del Grappa, Italy": (45.7664, 11.7344),
            "Firenze, Italy": (43.7696, 11.2558),  # Florence Italian name
            "Sicily, Italy": (37.5999, 14.0154),
            "Benevento, Italy": (41.1297, 14.7824),
            "Arezzo, Italy": (43.4632, 11.8796),
            "Stresa, Italy": (45.8833, 8.5333),
            "Arcidosso, Italy": (42.8667, 11.5333),
            "Pistoia, Italy": (43.9333, 10.9167),
            "Lucca, Italy": (43.8376, 10.4950),
            "Piombino, Italy": (42.9267, 10.5256),
            "Sassari, Italy": (40.7259, 8.5594),
            "Rovigo, Italy": (45.0703, 11.7903),
            "Tradate, Italy": (45.7097, 8.9097),
            "Todi, Italy": (42.7833, 12.4056),
            "Sapri, Italy": (40.0731, 15.6289),
            "Arona, Italy": (45.7569, 8.5567),
            # German states and cities
            "BW, Germany": (48.6616, 9.3501),  # Baden-Württemberg
            "Bavaria, Germany": (48.7904, 11.4979),
            "Rheinland-Pfalz, Germany": (50.1188, 7.3089),
            "Sachsen, Germany": (51.1045, 13.2017),  # Saxony
            "Limburg, Germany": (50.3836, 8.0503),
            "Aachen, Germany": (50.7753, 6.0839),
            "Jena, Germany": (50.9272, 11.5892),
            "Tann, Germany": (50.6167, 9.9500),
            "Bingen, Germany": (49.9669, 7.8997),
            "Soest, Germany": (51.5739, 8.1061),
            "Neubrandenburg, Germany": (53.5575, 13.2611),
            "Regensburg, Germany": (49.0134, 12.1016),
            "Heidelberg, Germany": (49.3988, 8.6724),
            "Kronach, Germany": (50.2386, 11.3289),
            "Lahr, Germany": (48.3394, 7.8742),
            "Hasel, Germany": (47.6167, 7.7500),
            "Rostock, Germany": (54.0887, 12.1437),
            "Magdeburg, Germany": (52.1205, 11.6276),
            "Göttingen, Germany": (51.5413, 9.9158),
            "Düren, Germany": (50.8021, 6.4831),
            "Pirmasens, Germany": (49.2006, 7.6006),
            # French cities
            "Évreux, France": (49.0247, 1.1508),
            "Anglet, France": (43.4917, -1.5211),
            "Boulogne Sur Mer, France": (50.7264, 1.6139),
            "Annecy, France": (45.8992, 6.1294),
            "Clermont-Ferrand, France": (45.7772, 3.0870),
            "Évreux, France": (49.0247, 1.1508),
            "Colmar, France": (48.0778, 7.3584),
            "Rambouillet, France": (48.6442, 1.8297),
            "Pau, France": (43.2951, -0.3708),
            "Bourg En Bresse, France": (46.2052, 5.2256),
            "Claix, France": (45.1217, 5.6742),
            "Lorient, France": (47.7482, -3.3706),
            "Reims, France": (49.2583, 4.0317),
            "Meaux, France": (48.9606, 2.8879),
            "Pamiers, France": (43.1175, 1.6108),
            "Le Puy, France": (45.0433, 3.8847),
            "Normandy, France": (49.1829, -0.3707),
            "Lorraine, France": (48.6920, 6.1847),
            # Additional US cities
            "Fayetteville, AR": (36.0626, -94.1574),
            "Highland Heights, KY": (39.0331, -84.4538),
            "Aliso Viejo, CA": (33.5676, -117.7256),
            "Stanardsville, VA": (38.2987, -78.4386),
            "Palatine, IL": (42.1103, -88.0342),
            "Valley Stream, NY": (40.6643, -73.7085),
            "Bergenfield, NJ": (40.9276, -73.9974),
            "Plymouth Meeting, PA": (40.1101, -75.2746),
            "Redding, CA": (40.5865, -122.3917),
            "Lakeville, MA": (41.8473, -70.9478),
            "Southern California": (34.0522, -118.2437),
            "Cresskill, New Jersey": (40.9398, -73.9596),
            "Southern, NH": (42.8806, -71.3287),
            "Arizona, USA": (34.0489, -111.0937),
            "Maryland": (39.0458, -76.6413),
            "Minnesota": (46.7296, -94.6859),
            "Corvallis, OR": (44.5646, -123.2620),
            "Dana Point, CA": (33.4672, -117.6981),
            "Gadsden, AL": (34.0143, -86.0066),
            "West Palm Beach, FL": (26.7153, -80.0534),
            "Kingfisher, OK": (35.8606, -97.9317),
            "Idaho Falls, ID": (43.4916, -112.0339),
            "Watkinsville, GA": (33.8626, -83.4079),
            "Ellenville, NY": (41.7176, -74.3971),
            "Mansfield, NJ": (40.7893, -74.6938),
            "Greene, NY": (42.3295, -75.7702),
            "Covington, KY": (39.0836, -84.5085),
            "Rutherford, NJ": (40.8265, -74.1068),
            "Arlington Heights, IL": (42.0884, -88.0906),
            "Florence, AL": (34.7998, -87.6773),
            "Claremont, CA": (34.0967, -117.7198),
            "West Covina, CA": (34.0686, -117.9390),
            "Essex, MA": (42.6320, -70.7823),
            "Salinas, CA": (36.6777, -121.6555),
            "Flagstaff, AZ": (35.1983, -111.6513),
            "Sterling Heights, MI": (42.5803, -83.0302),
            "Green Bay, WI": (44.5133, -88.0133),
            "Elmhurst, IL": (41.8994, -87.9403),
            "Fall River, MA": (41.7015, -71.1550),
            "Louisiana, LA": (30.9843, -91.9623),
            "Camden, NJ": (39.9259, -75.1196),
            "Pensacola, FL": (30.4213, -87.2169),
            "Alexandria, VA": (38.8048, -77.0469),
            "Laguna Beach, CA": (33.5427, -117.7854),
            "Youngstown, OH": (41.0998, -80.6495),
            "Haworth, NJ": (40.9607, -73.9893),
            "Watertown, CT": (41.6059, -73.1179),
            "Los Osos, CA": (35.3122, -120.8324),
            "Union Beach, NJ": (40.4476, -74.1776),
            "Millerton, NY": (41.9531, -73.5090),
            "Plymouth Meeting, PA": (40.1101, -75.2746),
            "Lakeville, MA": (41.8473, -70.9478),
            "West Chester, PA": (39.9607, -75.6055),
            "Rapid City, SD": (44.0805, -103.2310),
            "Sheboygan, WI": (43.7508, -87.7145),
            "Camas, WA": (45.5871, -122.3995),
            "Elizabeth, NJ": (40.6640, -74.2107),
            "Mingo Junction, OH": (40.3220, -80.6098),
            "Poughkeepsie, NY": (41.7004, -73.9209),
            "Williamsburg, VA": (37.2707, -76.7075),
            "Everett, WA": (47.9790, -122.2021),
            "Mansfield, CT": (41.7710, -72.2301),
            "Plaistow, NH": (42.8376, -71.0923),
            "Statesboro, GA": (32.4488, -81.7831),
            "Tumwater, WA": (47.0073, -122.9093),
            "Kirksville, MO": (40.1948, -92.5832),
            "Macon, GA": (32.8407, -83.6324),
            "Algonquin, IL": (42.1655, -88.2942),
            "Encino, CA": (34.1519, -118.5315),
            "Livermore, CA": (37.6819, -121.7680),
            "Bothell, WA": (47.7623, -122.2054),
            "Placerville, CA": (38.7296, -120.7985),
            "Galveston, TX": (29.3013, -94.7977),
            "Westerly, RI": (41.3776, -71.8273),
            "Monterey, CA": (36.6002, -121.8947),
            "Mobile, AL": (30.6954, -88.0399),
            "Ojai, CA": (34.4480, -119.2429),
            "Nyack, NY": (41.0923, -73.9179),
            "Ridgewood, NJ": (40.9793, -74.1165),
            "Glen Rock, NJ": (40.9626, -74.1326),
            "Castleton, VT": (43.6106, -73.1784),
            "Hawaii, HI": (19.8968, -155.5828),
            "Princeville, HI": (22.2176, -159.4850),
            "Mahopac, NY": (41.3681, -73.7382),
            "Minooka, IL": (41.4489, -88.2609),
            "Potsdam, NY": (44.6695, -74.9815),
            "Dacula, GA": (33.9871, -83.8977),
            "Parma, NY": (43.2595, -77.7236),
            "Dilliner, PA": (39.7620, -79.8867),
            "Centreville, VA": (38.8404, -77.4291),
            "Asbury Park, NY": (40.2204, -74.0121),
            "Moorpark, CA": (34.2856, -118.8820),
            "Manassas, VA": (38.7509, -77.4753),
            "Allen, TX": (33.1032, -96.6706),
            "Annandale, VA": (38.8304, -77.1964),
            "Bayonne, NJ": (40.6687, -74.1143),
            "North East, MD": (39.5998, -75.9419),
            "Roy, WA": (47.0029, -122.5354),
            "South Orange, NJ": (40.7490, -74.2615),
            "Honolulu, HI": (21.3099, -157.8581),
            "Newark, DE": (39.6837, -75.7497),
            "Sandown, NH": (42.9287, -71.1856),
            "Bloomingdale, NJ": (41.0193, -74.3318),
            "Morristown, NJ": (40.7968, -74.4815),
            "State College, PA": (40.7934, -77.8600),
            "Bellevue, WA": (47.6101, -122.2015),
            "Brandon, FL": (27.9378, -82.2859),
            "Cherry Hill, NJ": (39.9348, -75.0307),
            "Red Bank, NJ": (40.3471, -74.0643),
            "Edwardsburg, MI": (41.7939, -86.0817),
            "Jackson, TN": (35.6145, -88.8139),
            "Hendersonville, NC": (35.3187, -82.4610),
            "Hillsborough, NC": (36.0754, -79.0992),
            "Paragould, AR": (36.0584, -90.4973),
            "Rogers, AR": (36.3320, -94.1185),
            "Minot, ND": (48.2330, -101.2963),
            "Denver, NH": (43.0373, -71.7412),
            "Montgomery, AL": (32.3668, -86.3000),
            "Olathe, KS": (38.8814, -94.8191),
            "Mesa, AZ": (33.4152, -111.8315),
            "West Hartford, CT": (41.7621, -72.7420),
            "Smithville, TN": (35.9606, -85.8141),
            "Buffalo, WY": (44.3483, -106.6989),
            "Pleasanton, CA": (37.6624, -121.8747),
            "Winfield, IL": (41.8764, -88.1562),
            # International additions
            "Philippines": (12.8797, 121.7740),
            "Manila, Philippines": (14.5995, 120.9842),
            "Bangalore, India": (12.9716, 2.7469),
            "Hyderabad, India": (17.3850, 78.4867),
            "DL, India": (28.7041, 77.1025),  # Delhi
            "KA, India": (15.3173, 75.7139),  # Karnataka
            "Al Kuwayt, Kuwait": (29.3759, 47.9774),
            "Dhaka, Bangladesh": (23.8103, 90.4125),
            "Lahore, Pakistan": (31.5204, 74.3587),
            "Karachi, Pakistan": (24.8607, 67.0011),
            "Pakistan": (30.3753, 69.3451),
            "Iran": (32.4279, 53.6880),
            "Puerto Rico": (18.2208, -66.5901),
            "Skopje, North Macedonia": (41.9973, 21.4280),
            "Natal, Brazil": (-5.7945, -35.2110),
            "Recife, Brazil": (-8.0476, -34.8770),
            "PE, Brazil": (-8.8137, -36.9541),  # Pernambuco
            "Valentín Alsina, Argentina": (-34.6722, -58.4114),
            "Entre Ríos, Argentina": (-31.7333, -60.5333),
            "Valencia, Venezuela": (10.1621, -68.0077),
            "Taichung City, Taiwan": (24.1477, 120.6736),
            "Kaohsiung, Taiwan": (22.6273, 120.3014),
            "Shanghai, China": (31.2304, 121.4737),
            "Dalian, China": (38.9140, 121.6147),
            "Yokohama, Japan": (35.4437, 139.6380),
            "Kobe, Japan": (34.6901, 135.1955),
            "Ōsaka, Japan": (34.6937, 135.5023),
            "Taito, Japan": (35.7120, 139.7796),
            "Puebla, Mexico": (19.0414, -98.2063),
            "México": (23.6345, -102.5528),
            "Quito, Ecuador": (-0.1807, -78.4678),
            "Cali, Colombia": (3.4516, -76.5320),
            "San Jose, Costa Rica": (9.9281, -84.0907),
            "Shah Alam, Malaysia": (3.0733, 101.5185),
            "Selangor, Malaysia": (3.0738, 101.5183),
            "Ulaanbaatar, Mongolia": (47.8864, 106.9057),
            "Alexandria, Egypt": (31.2001, 29.9187),
            "Andorra": (42.5063, 1.5218),
            "Bulgaria": (42.7339, 25.4858),
            "Bahrain": (26.0667, 50.5577),
            "Guatemala": (15.7835, -90.2308),
            # Ukrainian cities
            "Ужгород, Ukraine": (48.6167, 22.3000),  # Uzhhorod
            "Odessa, Ukraine": (46.4825, 30.7233),
            "Donblast, Ukraine": (48.0159, 37.8028),  # Donetsk oblast typo
            "Kiev, Ukraine": (50.4501, 30.5234),
            "Ternopil, Ukraine": (49.5535, 25.5948),
            "Ivano Frankivsk, Ukraine": (48.9226, 24.7111),
            "Ivano-Frankivsk, Ukraine": (48.9226, 24.7111),
            "Vinnytsia, Ukraine": (49.2331, 28.4682),
            "Cherkasy, Ukraine": (49.4285, 32.0615),
            # Russian cities
            "Kyshtym, Russia": (55.7167, 60.5500),
            "Krasnodar, Russia": (45.0428, 38.9769),
            "Kaliningrad, Russia": (54.7104, 20.4522),
            "Chelyabinsk, Russia": (55.1644, 61.4368),
            "Altai, Russia": (51.9581, 85.9603),
            "Ryazan, Russia": (54.6269, 39.6916),
            "Angarsk, Russia": (52.5408, 103.8886),
            "Novorossiysk, Russia": (44.7241, 37.7686),
            "Saratov, Russia": (51.5924, 46.0348),
            "Rostov, Russia": (47.2357, 39.7015),
            "St. Petersburg, Russia": (59.9311, 30.3609),
            # Norwegian cities
            "Telemark, Norway": (59.3800, 8.4600),
            "Farsund, Norway": (58.0955, 6.8035),
            "Mandal, Norway": (58.0297, 7.4553),
            "Asker, Norway": (59.8349, 10.4359),
            "Arendal, Norway": (58.4620, 8.7720),
            "Grimstad, Norway": (58.3403, 8.5934),
            "Hønefoss, Norway": (60.1681, 10.2569),
            "Gjøvik, Norway": (60.7957, 10.6915),
            "Ålesund, Norway": (62.4722, 6.1549),
            # Portuguese cities
            "Leiria, Portugal": (39.7436, -8.8071),
            "Paços de Ferreira, Portugal": (41.2769, -8.3769),
            "Évora, Portugal": (38.5714, -7.9094),
            "Bragança, Portugal": (41.8058, -6.7570),
            "Aveiro, Portugal": (40.6443, -8.6455),
            "Barcelos, Portugal": (41.5311, -8.6194),
            # Romanian cities
            "Constanța, Romania": (44.1598, 28.6348),
            "Timişoara, Romania": (45.7489, 21.2087),
            "Cluj, Romania": (46.7712, 23.6236),
            # Greek cities
            "Epirus, Greece": (39.5650, 20.8403),
            "Agria, Greece": (39.3500, 22.9833),
            "Attica, Greece": (38.0500, 23.8000),
            "Chania, Greece": (35.5138, 24.0180),
            "Piraeus, Greece": (37.9421, 23.6463),
            "Rhodes, Greece": (36.4341, 28.2176),
            # Hungarian cities
            "Debrecen, Hungary": (47.5316, 21.6273),
            "Miskolc, Hungary": (48.1035, 20.7784),
            "Győr, Hungary": (47.6875, 17.6504),
            "Páty, Hungary": (47.5214, 18.8603),
            # Czech cities
            "Olomouc, Czech Republic": (49.5938, 17.2509),
            "Pilsen, Czech Republic": (49.7384, 13.3736),
            "Tabor, Czech Republic": (49.4144, 14.6578),
            # Estonian cities
            "Tartu, Estonia": (58.3806, 26.7251),
            # Slovenian cities
            "Nova Gorica, Slovenia": (45.9564, 13.6480),
            "Jesenice, Slovenia": (46.4297, 14.0522),
            "Koper, Slovenia": (45.5481, 13.7301),
            # Belgian cities
            "Halen, Belgium": (50.9472, 5.1100),
            "Temse, Belgium": (51.1289, 4.2147),
            "Leopoldsburg, Belgium": (51.1169, 5.2564),
            "Zulte, Belgium": (50.9214, 3.4489),
            "Genk, Belgium": (50.9658, 5.5005),
            "Wevelgem, Belgium": (50.8000, 3.1833),
            # Austrian cities
            "Bruck An Der Mur, Austria": (47.4108, 15.2672),
            "Weiz, Austria": (47.2169, 15.6289),
            # Belarus
            "Grodno, Belarus": (53.6884, 23.8258),
            # Azerbaijan
            "Baku, Azerbaijan": (40.4093, 49.8671),
            # Armenia
            "Gyumri, Armenia": (40.7894, 43.8475),
            # Denmark
            "Esbjerg, Denmark": (55.4760, 8.4600),
            "Næstved, Denmark": (55.2300, 11.7611),
            # New Zealand
            "Whanganui, New Zealand": (-39.9299, 175.0485),
            "Waipu, New Zealand": (-35.9667, 174.4500),
            "Napier, New Zealand": (-39.4902, 176.9120),
            # Sweden additional
            "Boden, Sweden": (65.8253, 21.6886),
            "Vikingstad, Sweden": (58.4667, 15.0667),
            # Special locations
            "Multi-national": (51.1657, 10.4515),  # Center of Europe
            "Multinational": (51.1657, 10.4515),
            "In Space": (0.0, 0.0),  # Null Island
            "Usa": (37.0902, -95.7129),  # USA center
            "İstanbul, Turkey": (41.0082, 28.9784),
            "İstanbul, Türkiye": (41.0082, 28.9784),
            # Variants with leading spaces (data quality issues)
            " Rozenburg, Netherlands": (51.9042, 4.2470),
            " Rijsbergen, Netherlands": (51.5167, 4.7000),
            # Phase 9: Final missing locations from latest error log
            "Borgomanero, Italy": (45.7000, 8.4667),
            "Stoke-on-Trent, England": (53.0027, -2.1794),
            "Gmina Przeworsk, Poland": (50.0583, 22.4944),
            "Seville, Spain": (37.3891, -5.9845),
            "Norwich, England": (52.6309, 1.2974),
            "OK": (35.0078, -97.0929),  # Oklahoma center
            "PA": (41.2033, -77.1945),  # Pennsylvania center
            "Vancouver": (49.2827, -123.1207),  # Vancouver BC default
            "Berlin, VT": (44.2028, -72.5776),
            "Brno, Czech Republic": (49.1951, 16.6068),
            "Shreveport, LA": (32.5252, -93.7502),
            "Одесса, Ukraine": (46.4825, 30.7233),  # Odessa Cyrillic
            "Mâcon, France": (46.3067, 4.8328),
            "The Netherlands": (52.1326, 5.2913),
            "Carlisle, UK": (54.8951, -2.9382),
            "Silgo, Ireland": (54.2697, -8.4694),  # Sligo typo
            "Brampton, Ontario": (43.7315, -79.7624),
            "Ottawa, Ontario": (45.4215, -75.6972),
            "Birgmingham, England": (52.4862, -1.8904),  # Birmingham typo
            "Guildford, England": (51.2362, -0.5704),
            "Lehigh Valley, PA": (40.6084, -75.4902),
            "Olgiate Molgora, Italy": (45.7167, 9.4000),
            "MD": (39.0458, -76.6413),  # Maryland center
            "Visby, Sweden": (57.6348, 18.2948),
            "Astana, Kazakhstan": (51.1694, 71.4491),
            "Ústecký, Czech Republic": (50.6607, 13.8258),
            "Львов, Ukraine": (49.8397, 24.0297),  # Lviv Cyrillic
            "Lancashire, UK": (53.7632, -2.7044),
            "Kitchener, Ontario": (43.4516, -80.4925),
            "Cambridge, Ontario": (43.3616, -80.3144),
            "Blue Mountains, Australia": (-33.7000, 150.3000),
            "San Fernando Valley, CA": (34.2000, -118.4500),
            "St. Alberta, Alberta": (53.6306, -113.6258),  # St. Albert typo
            "Battlefield, MO": (37.1156, -93.3660),
            "PA / Norway / Greece": (40.0000, 20.0000),  # Multi-location placeholder
            "OR & AK": (57.0000, -135.0000),  # Oregon & Alaska midpoint
            "New Westminster, BC": (49.2069, -122.9110),
            "Holbrook, NY": (40.8123, -73.0776),
            "Cwmbran, Wales": (51.6544, -3.0175),
            "Zoppolla, Italy": (45.7833, 12.5667),
            "Philadelphia, NY": (44.1534, -75.7096),
            "Montevideo, Uruguay": (-34.9011, -56.1645),
            "Stockton, CA": (37.9577, -121.2908),
            "Pennsylvania, MN": (46.7296, -94.6859),  # Probably Minnesota typo
            "Wisconsin Rapids, WI": (44.3836, -89.8173),
            "Lafayette, IN": (40.4167, -86.8753),
            "Glen of the Downs, Ireland": (53.1167, -6.1000),
            "Bryn Mawr Skyway, WA": (47.4954, -122.2482),
            "Huntington, VW": (38.4192, -82.4452),  # WV typo
            "Edwinstowe, UK": (53.1950, -1.0650),
            "Glen Of The Downs, UK": (53.1167, -6.1000),  # Actually Ireland
            "Maryport, UK": (54.7138, -3.4952),
            "Port Orchard, WA": (47.5404, -122.6365),
        })
    
    def get_coordinates(self, location: str) -> Optional[Tuple[float, float]]:
        """Get lat/long coordinates for a location string."""
        if not location:
            return None
        
        # Try direct lookup
        if location in self._cache:
            return self._cache[location]
        
        # Try country extraction from "Country / Region" format
        parts = location.split("/")
        if parts:
            country = parts[0].strip()
            if country in self._cache:
                return self._cache[country]
        
        graphics_logger.debug(f"Location '{location}' not found in cache")
        return None
    
    def add_location(self, location: str, lat: float, lon: float):
        """Add a location to the cache."""
        self._cache[location] = (lat, lon)


class WorldMapView(BaseView):
    """World map visualization showing geographic distribution of albums."""
    
    selection_changed = pyqtSignal(set)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view_type = ViewType.MAP
        self.location_cache = LocationCache()
        self.albums_by_location: Dict[Tuple[float, float], List[Dict[str, Any]]] = {}
        
        # Setup UI
        self._setup_ui()
        
        graphics_logger.info("WorldMapView initialized")
    
    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Controls panel
        controls_layout = QHBoxLayout()
        
        # View mode selection
        view_label = QLabel("View Mode:")
        self.view_combo = QComboBox()
        self.view_combo.addItems(["Markers", "Clusters", "Heatmap"])
        self.view_combo.currentTextChanged.connect(self._on_view_mode_changed)
        controls_layout.addWidget(view_label)
        controls_layout.addWidget(self.view_combo)
        
        controls_layout.addSpacing(20)
        
        # Filter controls
        filter_label = QLabel("Genre Filter:")
        self.genre_filter = QComboBox()
        self.genre_filter.addItem("All Genres")
        self.genre_filter.currentTextChanged.connect(self._on_filter_changed)
        controls_layout.addWidget(filter_label)
        controls_layout.addWidget(self.genre_filter)
        
        controls_layout.addSpacing(20)
        
        # Year range filter
        year_label = QLabel("Year Range:")
        self.year_min = QSpinBox()
        self.year_min.setRange(1900, 2030)
        self.year_min.setValue(1960)
        self.year_min.setPrefix("From: ")
        self.year_min.valueChanged.connect(self._on_filter_changed)
        
        self.year_max = QSpinBox()
        self.year_max.setRange(1900, 2030)
        self.year_max.setValue(2030)
        self.year_max.setPrefix("To: ")
        self.year_max.valueChanged.connect(self._on_filter_changed)
        
        controls_layout.addWidget(self.year_min)
        controls_layout.addWidget(self.year_max)
        
        controls_layout.addStretch()
        
        # Statistics label
        self.stats_label = QLabel("Albums: 0 | Countries: 0")
        controls_layout.addWidget(self.stats_label)
        
        # Add controls with minimal stretch (0 = minimum space needed)
        layout.addLayout(controls_layout, 0)
        
        # Web view for map
        self.web_view = QWebEngineView()
        
        # Configure web view to allow loading CDN resources from local files
        settings = self.web_view.settings()
        settings.setAttribute(settings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(settings.WebAttribute.LocalContentCanAccessFileUrls, True)
        
        # Add web view with maximum stretch (100 = takes all available space)
        layout.addWidget(self.web_view, 100)
        
        # Initialize with empty map
        self._render_empty_map()
    
    def _render_empty_map(self):
        """Render an empty map centered on the world."""
        m = folium.Map(
            location=[20, 0],
            zoom_start=2,
            tiles='OpenStreetMap',
            width='100%',
            height='100%'
        )
        
        # Add a message
        folium.Marker(
            [20, 0],
            popup="<b>Album Explorer</b><br>Load data to see albums on the map",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)
        
        # Save and load
        self._save_and_load_map(m)
    
    def update_data(self, data: Dict[str, Any]):
        """Update the map with new data."""
        graphics_logger.info(f"WorldMapView.update_data called with data keys: {list(data.keys()) if data else 'None'}")
        
        super().update_data(data)
        
        # Handle both 'nodes' (from graph renderers) and 'rows' (from table renderer)
        albums_data = data.get('nodes') or data.get('rows')
        
        if not albums_data:
            graphics_logger.warning("No nodes or rows data provided to WorldMapView")
            return
        
        # Extract album data and geocode
        self._process_albums(albums_data)
        
        # Update genre filter options
        self._update_filter_options()
        
        # Render map
        self._render_map()
    
    def _process_albums(self, nodes: List[Dict[str, Any]]):
        """Process album data and geocode locations."""
        self.albums_by_location.clear()
        
        for node in nodes:
            # Handle both node-based structure (from renderers) and row-based structure (from table renderer)
            # Get location - try multiple field names
            location = (node.get('location') or 
                       node.get('country') or 
                       node.get('data', {}).get('location') or
                       node.get('data', {}).get('country'))
            
            if not location or str(location).lower() in ['', 'none', 'nan']:
                continue
            
            # Geocode
            coords = self.location_cache.get_coordinates(location)
            if not coords:
                graphics_logger.debug(f"Could not geocode location: {location}")
                continue
            
            # Add album to location group
            if coords not in self.albums_by_location:
                self.albums_by_location[coords] = []
            
            # Extract album info - handle both structures
            album_title = (node.get('album') or 
                          node.get('title') or 
                          node.get('label') or
                          node.get('data', {}).get('album') or
                          node.get('data', {}).get('title') or
                          'Unknown Album')
            
            artist = (node.get('artist') or 
                     node.get('data', {}).get('artist') or 
                     'Unknown Artist')
            
            year = node.get('year') or node.get('data', {}).get('year')
            
            # Handle genre - might be in tags or as a separate field
            genre = (node.get('genre') or 
                    node.get('data', {}).get('genre') or 
                    'Unknown')
            
            tags = node.get('tags', []) or node.get('data', {}).get('tags', [])
            
            self.albums_by_location[coords].append({
                'id': node.get('id', ''),
                'label': album_title,
                'artist': artist,
                'year': year,
                'genre': genre,
                'tags': tags,
                'location': location
            })
        
        graphics_logger.info(f"Processed {len(nodes)} albums into {len(self.albums_by_location)} locations")
    
    def _update_filter_options(self):
        """Update the genre filter dropdown based on available data."""
        genres = set()
        for albums in self.albums_by_location.values():
            for album in albums:
                genre = album.get('genre', 'Unknown')
                if genre:
                    genres.add(genre)
        
        current_genre = self.genre_filter.currentText()
        self.genre_filter.clear()
        self.genre_filter.addItem("All Genres")
        self.genre_filter.addItems(sorted(genres))
        
        # Restore selection if still valid
        index = self.genre_filter.findText(current_genre)
        if index >= 0:
            self.genre_filter.setCurrentIndex(index)
    
    def _render_map(self):
        """Render the map based on current view mode and filters."""
        view_mode = self.view_combo.currentText()
        
        # Create base map with enhanced styling
        m = folium.Map(
            location=[20, 0],
            zoom_start=2,
            tiles='CartoDB positron',  # Cleaner, lighter tiles
            width='100%',
            height='100%',
            zoom_control=True,
            scrollWheelZoom=True,
            dragging=True,
            prefer_canvas=True  # Better performance
        )
        
        # Add layer control for different map styles
        folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
        folium.TileLayer('CartoDB dark_matter', name='Dark Mode').add_to(m)
        folium.LayerControl().add_to(m)
        
        # Get filtered albums
        filtered_locations = self._get_filtered_locations()
        
        if view_mode == "Clusters":
            self._render_clustered_markers(m, filtered_locations)
        elif view_mode == "Heatmap":
            self._render_heatmap(m, filtered_locations)
        else:  # Markers
            self._render_markers(m, filtered_locations)
        
        # Update statistics
        total_albums = sum(len(albums) for albums in filtered_locations.values())
        self.stats_label.setText(f"Albums: {total_albums} | Countries: {len(filtered_locations)}")
        
        # Save and load
        self._save_and_load_map(m)
    
    def _get_filtered_locations(self) -> Dict[Tuple[float, float], List[Dict[str, Any]]]:
        """Get albums filtered by current filter settings."""
        genre_filter = self.genre_filter.currentText()
        year_min = self.year_min.value()
        year_max = self.year_max.value()
        
        filtered = {}
        
        for coords, albums in self.albums_by_location.items():
            filtered_albums = []
            
            for album in albums:
                # Genre filter
                if genre_filter != "All Genres":
                    if album.get('genre') != genre_filter:
                        continue
                
                # Year filter
                year = album.get('year')
                if year:
                    try:
                        year_int = int(year)
                        if year_int < year_min or year_int > year_max:
                            continue
                    except (ValueError, TypeError):
                        # Skip albums with invalid year data
                        continue
                
                filtered_albums.append(album)
            
            if filtered_albums:
                filtered[coords] = filtered_albums
        
        return filtered
    
    def _render_markers(self, m: folium.Map, locations: Dict[Tuple[float, float], List[Dict[str, Any]]]):
        """Render individual markers for each location."""
        for coords, albums in locations.items():
            lat, lon = coords
            
            # Create enhanced popup HTML with better styling
            popup_html = f"""
            <div style="font-family: Arial, sans-serif; min-width: 250px;">
                <h3 style="margin: 0 0 10px 0; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">
                    📍 {albums[0]['location']}
                </h3>
                <p style="margin: 5px 0; font-size: 14px; color: #7f8c8d;">
                    <strong>{len(albums)} album(s)</strong>
                </p>
                <div style="max-height: 300px; overflow-y: auto; margin-top: 10px;">
            """
            
            for i, album in enumerate(albums[:15], 1):  # Show up to 15 albums
                year_str = f" <span style='color: #95a5a6;'>({album['year']})</span>" if album.get('year') else ""
                genre_str = f" <span style='color: #e67e22; font-size: 11px;'>[{album['genre']}]</span>" if album.get('genre') and album['genre'] != 'Unknown' else ""
                
                popup_html += f"""
                <div style="margin: 8px 0; padding: 8px; background: #ecf0f1; border-radius: 4px;">
                    <div style="font-weight: bold; color: #2c3e50;">{i}. {album['artist']}</div>
                    <div style="font-size: 12px; color: #34495e; margin-top: 2px;">🎵 {album['label']}{year_str}{genre_str}</div>
                </div>
                """
            
            if len(albums) > 15:
                popup_html += f"<p style='text-align: center; color: #95a5a6; font-style: italic; margin-top: 10px;'>... and {len(albums) - 15} more albums</p>"
            
            popup_html += "</div></div>"
            
            # Determine marker color based on album count with more granular levels
            if len(albums) > 200:
                color = 'darkred'
            elif len(albums) > 100:
                color = 'red'
            elif len(albums) > 50:
                color = 'orange'
            elif len(albums) > 20:
                color = 'blue'
            elif len(albums) > 10:
                color = 'lightblue'
            else:
                color = 'green'
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"<b>{albums[0]['location']}</b><br>{len(albums)} albums",
                icon=folium.Icon(color=color, icon='music', prefix='fa')
            ).add_to(m)
    
    def _render_clustered_markers(self, m: folium.Map, locations: Dict[Tuple[float, float], List[Dict[str, Any]]]):
        """Render markers with clustering and enhanced visuals."""
        # Create marker cluster with custom options
        marker_cluster = MarkerCluster(
            name='Album Locations',
            overlay=True,
            control=True,
            show=True,
            options={
                'maxClusterRadius': 50,
                'spiderfyOnMaxZoom': True,
                'showCoverageOnHover': False,
                'zoomToBoundsOnClick': True
            }
        ).add_to(m)
        
        for coords, albums in locations.items():
            lat, lon = coords
            album_count = len(albums)
            
            # Create enhanced popup HTML
            popup_html = f"""
            <div style="font-family: Arial, sans-serif; min-width: 250px;">
                <h3 style="margin: 0 0 10px 0; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">
                    📍 {albums[0]['location']}
                </h3>
                <p style="margin: 5px 0; font-size: 14px; color: #7f8c8d;">
                    <strong>{album_count} album(s)</strong>
                </p>
                <div style="max-height: 300px; overflow-y: auto; margin-top: 10px;">
            """
            
            for i, album in enumerate(albums[:15], 1):
                year_str = f" <span style='color: #95a5a6;'>({album['year']})</span>" if album.get('year') else ""
                genre_str = f" <span style='color: #e67e22; font-size: 11px;'>[{album['genre']}]</span>" if album.get('genre') and album['genre'] != 'Unknown' else ""
                
                popup_html += f"""
                <div style="margin: 8px 0; padding: 8px; background: #ecf0f1; border-radius: 4px;">
                    <div style="font-weight: bold; color: #2c3e50;">{i}. {album['artist']}</div>
                    <div style="font-size: 12px; color: #34495e; margin-top: 2px;">🎵 {album['label']}{year_str}{genre_str}</div>
                </div>
                """
            
            if album_count > 15:
                popup_html += f"<p style='text-align: center; color: #95a5a6; font-style: italic; margin-top: 10px;'>... and {album_count - 15} more albums</p>"
            
            popup_html += "</div></div>"
            
            # Use CircleMarkers for better clustering visualization
            # Color and size based on album count
            if album_count > 100:
                color = '#c0392b'  # dark red
                radius = 12
            elif album_count > 50:
                color = '#e74c3c'  # red
                radius = 10
            elif album_count > 20:
                color = '#f39c12'  # orange
                radius = 8
            elif album_count > 10:
                color = '#3498db'  # blue
                radius = 7
            else:
                color = '#27ae60'  # green
                radius = 6
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"<b>{albums[0]['location']}</b><br>{album_count} albums",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=2
            ).add_to(marker_cluster)
    
    def _render_heatmap(self, m: folium.Map, locations: Dict[Tuple[float, float], List[Dict[str, Any]]]):
        """Render an enhanced heatmap of album density."""
        heat_data = []
        
        for coords, albums in locations.items():
            lat, lon = coords
            # Weight by number of albums at this location (with logarithmic scale for better visualization)
            album_count = len(albums)
            # Use log scale to prevent extreme hotspots from dominating
            import math
            weight = math.log(album_count + 1) * 2  # +1 to avoid log(0)
            heat_data.append([lat, lon, weight])
        
        if heat_data:
            HeatMap(
                heat_data,
                name='Album Density Heatmap',
                min_opacity=0.4,
                max_opacity=0.9,
                radius=20,
                blur=18,
                max_zoom=13,
                gradient={
                    0.0: '#2c3e50',   # dark blue
                    0.2: '#3498db',   # blue
                    0.4: '#1abc9c',   # teal
                    0.6: '#f1c40f',   # yellow
                    0.8: '#e67e22',   # orange
                    1.0: '#e74c3c'    # red
                }
            ).add_to(m)
    
    def _save_and_load_map(self, m: folium.Map):
        """Save map to temporary file and load in web view."""
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            suffix='.html',
            encoding='utf-8'
        )
        
        try:
            # Save map
            m.save(temp_file.name)
            temp_file.close()
            
            # Load in web view
            # The web settings configured in _setup_ui allow loading CDN resources
            file_url = QUrl.fromLocalFile(temp_file.name)
            self.web_view.setUrl(file_url)
            
            graphics_logger.debug(f"Map saved to {temp_file.name}")
            
        except Exception as e:
            graphics_logger.error(f"Error saving/loading map: {e}", exc_info=True)
    
    def _on_view_mode_changed(self, mode: str):
        """Handle view mode change."""
        graphics_logger.debug(f"View mode changed to: {mode}")
        self._render_map()
    
    def _on_filter_changed(self):
        """Handle filter change."""
        graphics_logger.debug("Filter changed, re-rendering map")
        self._render_map()
