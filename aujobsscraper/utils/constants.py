"""
Constants used across the scraping utilities.

This module contains constant definitions for Australian location mappings.
"""

# Comprehensive Australian city-to-state mapping (major cities and regional centers)
CITY_TO_STATE = {
    # New South Wales
    'sydney': 'NSW', 'newcastle': 'NSW', 'wollongong': 'NSW', 'central coast': 'NSW',
    'maitland': 'NSW', 'wagga wagga': 'NSW', 'albury': 'NSW', 'port macquarie': 'NSW',
    'tamworth': 'NSW', 'orange': 'NSW', 'dubbo': 'NSW', 'bathurst': 'NSW',
    'lismore': 'NSW', 'nowra': 'NSW', 'north sydney': 'NSW', 'parramatta': 'NSW',
    
    # Victoria
    'melbourne': 'VIC', 'geelong': 'VIC', 'ballarat': 'VIC', 'bendigo': 'VIC',
    'shepparton': 'VIC', 'mildura': 'VIC', 'warrnambool': 'VIC', 'wodonga': 'VIC',
    'traralgon': 'VIC', 'horsham': 'VIC',
    
    # Queensland
    'brisbane': 'QLD', 'gold coast': 'QLD', 'sunshine coast': 'QLD', 'townsville': 'QLD',
    'cairns': 'QLD', 'toowoomba': 'QLD', 'mackay': 'QLD', 'rockhampton': 'QLD',
    'bundaberg': 'QLD', 'hervey bay': 'QLD', 'gladstone': 'QLD', 'ipswich': 'QLD',
    
    # South Australia
    'adelaide': 'SA', 'mount gambier': 'SA', 'whyalla': 'SA', 'port lincoln': 'SA',
    'port augusta': 'SA', 'murray bridge': 'SA',
    
    # Western Australia
    'perth': 'WA', 'mandurah': 'WA', 'bunbury': 'WA', 'geraldton': 'WA',
    'albany': 'WA', 'kalgoorlie': 'WA', 'busselton': 'WA', 'rockingham': 'WA',
    
    # Tasmania
    'hobart': 'TAS', 'launceston': 'TAS', 'devonport': 'TAS', 'burnie': 'TAS',
    
    # Northern Territory
    'darwin': 'NT', 'alice springs': 'NT', 'palmerston': 'NT',
    
    # Australian Capital Territory
    'canberra': 'ACT',
}

# State/territory full names to filter out
STATE_NAMES = {
    'new south wales', 'nsw', 'victoria', 'vic', 'queensland', 'qld',
    'south australia', 'sa', 'western australia', 'wa', 'tasmania', 'tas',
    'northern territory', 'nt', 'australian capital territory', 'act', 'australia', 'au'
}

# Common non-city descriptors to filter out
NON_CITY_PATTERNS = [
    r'cbd and inner suburbs',
    r'inner suburbs',
    r'western suburbs',
    r'eastern suburbs',
    r'northern suburbs',
    r'southern suburbs',
    r'metro',
    r'metropolitan',
    r'region',
    r'area',
    r'greater\s+\w+',
]

# Australian state/territory abbreviations
AUSTRALIAN_STATES = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT']
