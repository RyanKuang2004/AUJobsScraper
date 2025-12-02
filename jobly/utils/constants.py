"""
Constants used across the scraping utilities.

This module contains all constant definitions including:
- Stop words and noise terms
- Role suffixes for job title extraction
- Job role taxonomy for classification
- Australian location mappings
"""

# stop / noise words to strip early (including seniority terms)
STOP_WORDS = {
    "internship", "intern", "grad", "program", "graduate", "graduate program",
    "phd", "masters", "start", "2025", "2026", "2024", "2027", "full-time", "full time",
    "part-time", "part time", "remote", "on-site", "onsite", "temporary", "contract",
    # Seniority-related terms to remove
    "senior", "junior", "lead", "entry", "entry level", "level", "principal",
    "head", "staff", "trainee"
}

# Useful suffixes we want to detect (multi-word ones first)
ROLE_SUFFIXES = [
    "test automation engineer",
    "machine learning engineer",
    "software engineer",
    "electrical engineer",
    "civil engineer",
    "automation engineer",
    "test engineer",
    "data scientist",
    "data engineer",
    "software developer",
    "research scientist",
    "systems engineer",
    "hardware engineer",
    "design engineer",
    "engineer",
    "developer",
    "scientist",
    "analyst",
    "architect",
    "designer",
    "administrator",
    "specialist",
    "consultant",
    "technician",
    "coordinator",
    "manager",
]

# ensure longest-first matching
ROLE_SUFFIXES = sorted(ROLE_SUFFIXES, key=lambda s: -len(s))

# Job role taxonomy mapping standard roles to keywords
# IMPORTANT: Order matters! More specific roles are checked first to avoid misclassification.
# AI/ML and specialized roles appear before generic "Software Engineer" category.
ROLE_TAXONOMY = {
    # ========================================
    # AI & ML (HIGHEST PRIORITY - Most Specific)
    # ========================================
    "AI Engineer": [
        # Combined AI/ML terminology - should classify as AI Engineer per user requirement
        "ai/ml engineer", "ai ml engineer", "ai / ml", "ai/ml", "ai & ml",
        # AI-focused roles
        "ai engineer", "ai software engineer", "ai developer", "ai software developer", 
        "ai programmer", "artificial intelligence engineer",
        # Generative AI
        "generative ai", "genai engineer", "gen ai", "generative ai engineer",
        # AI Platform/Infrastructure
        "ai platform engineer", "ai devops", "ai infrastructure",
        # General AI
        "artificial intelligence",
    ],
    "Machine Learning Engineer": [
        "machine learning engineer", "ml engineer", "machine learning developer", "ml developer",
        "mlops engineer", "mlops", "deep learning engineer", "ml software engineer",
    ],
    "NLP Engineer": [
        "nlp engineer", "natural language processing", "conversational ai", 
        "prompt engineer", "llm engineer", "large language model",
    ],
    "Research Scientist": [
        "research scientist", "computer scientist", "applied scientist",
        "research fellow", "computational science", "research assistant",
    ],
    
    # ========================================
    # Data & Analytics (High Priority - Specific)
    # ========================================
    "Data Scientist": ["data scientist", "applied scientist", "spatial data scientist"],
    "Data Engineer": ["data engineer", "big data", "etl developer", "azure data engineer", "data pipeline"],
    "Data Analyst": ["data analyst", "reporting analyst", "insights analyst", "commercial analyst"],
    "Business Intelligence Analyst": ["business intelligence", "bi analyst", "bi developer", "power bi", "tableau", "analytics"],
    "Data Architect": ["data architect", "data modeler", "database architect"],
    "Database Administrator": ["database administrator", "database developer", "sql developer", "dba"],
    
    # ========================================
    # Software Development (Expanded - Medium-High Priority)
    # ========================================
    "Frontend Developer": [
        "frontend developer", "front-end developer", "front end developer",
        "ui developer", "ui engineer", "user interface developer",
        "react developer", "angular developer", "vue developer", "vue.js developer",
        "javascript developer", "typescript developer",
        "html/css developer", "web ui developer"
    ],
    "Backend Developer": [
        "backend developer", "back-end developer", "back end developer",
        "server-side developer", "api developer", "microservices developer",
        "node.js developer", "python developer", "java developer", 
        "c# developer", ".net developer", "go developer", "golang developer",
        "ruby developer", "php backend developer"
    ],
    "Full Stack Developer": [
        "full stack", "fullstack", "full-stack developer",
        "javascript full stack", "typescript full stack",
        "mern stack", "mean stack", "lamp stack"
    ],
    "Mobile Developer": [
        "mobile developer", "ios developer", "android developer", 
        "react native", "mobile app developer", "flutter developer",
        "swift developer", "kotlin developer", "mobile engineer"
    ],
    "Web Developer": [
        "web developer", "website developer", "web application developer",
        "php developer", "wordpress developer", "drupal developer",
        "website designer"
    ],
    "Game Developer": [
        "game developer", "game software engineer", "unity developer", 
        "game engineer", "unreal developer", "game programmer",
        "gameplay programmer"
    ],
    "Embedded Systems Engineer": [
        "embedded systems", "firmware engineer", "embedded software", 
        "embedded engineer", "iot developer", "iot engineer"
    ],
    
    # ========================================
    # Infrastructure, Cloud & DevOps (Medium-High Priority)
    # ========================================
    "DevOps Engineer": [
        "devops engineer", "site reliability engineer", "sre", 
        "ci/cd engineer", "devsecops", "devops specialist",
        "build engineer", "release engineer"
    ],
    "Cloud Engineer": [
        "cloud engineer", "azure engineer", "aws engineer", 
        "cloud architect", "solutions engineer", "gcp engineer",
        "cloud infrastructure engineer", "cloud solutions architect"
    ],
    "Platform Engineer": [
        "platform engineer", "infrastructure engineer", "systems engineer",
        "infrastructure architect"
    ],
    "Systems Administrator": [
        "systems administrator", "it support", "application support", 
        "service desk", "sysadmin", "system administrator",
        "it administrator", "network administrator"
    ],
    "Network Engineer": [
        "network engineer", "network architect", "network administrator",
        "network security engineer", "cisco engineer", "lan/wan engineer"
    ],
    
    # ========================================
    # Security (Medium Priority)
    # ========================================
    "Cyber Security Engineer": [
        "cyber security", "security analyst", "infosec", 
        "detection engineer", "security engineer", "cybersecurity",
        "information security", "security consultant", "penetration tester",
        "ethical hacker", "security operations"
    ],
    
    # ========================================
    # QA & Testing (Medium Priority - Expanded)
    # ========================================
    "QA Engineer": [
        "qa engineer", "quality assurance engineer", "quality engineer",
        "software tester", "manual tester", "functional tester"
    ],
    "Test Automation Engineer": [
        "test automation engineer", "automation engineer", "automation tester",
        "test automation", "selenium engineer", "automation qa",
        "sdet", "software development engineer in test",
        "automated testing engineer"
    ],
    "Performance Test Engineer": [
        "performance test engineer", "performance tester", 
        "load test engineer", "jmeter engineer"
    ],
    
    # ========================================
    # Specialized Engineering (Medium Priority)
    # ========================================
    "Blockchain Developer": [
        "blockchain developer", "blockchain engineer", "web3 developer",
        "smart contract developer", "solidity developer", "cryptocurrency developer"
    ],
    "Computer Vision Engineer": [
        "computer vision engineer", "computer vision", "image processing engineer",
        "opencv developer", "vision ai"
    ],
    "Robotics Engineer": [
        "robotics engineer", "robotics developer", "automation robotics",
        "ros developer", "robotic systems engineer"
    ],
    "Graphics Engineer": [
        "graphics engineer", "graphics programmer", "rendering engineer",
        "opengl developer", "directx developer", "shader programmer"
    ],
    
    # ========================================
    # Design & UX (Medium Priority)
    # ========================================
    "UX/UI Designer": [
        "ux designer", "ui designer", "ux/ui designer", "user experience designer",
        "product designer", "interaction designer", "visual designer",
        "user interface designer"
    ],
    "UX Researcher": [
        "ux researcher", "user researcher", "ux analyst",
        "usability researcher", "user experience researcher"
    ],
    
    # ========================================
    # Generic Software Engineering (LOWER Priority - Catch-all)
    # ========================================
    "Software Engineer": [
        "software engineer", "programmer", 
        "application engineer", "app engineer",
        "software development engineer"
    ],
    "Software Developer": [
        "software developer", "developer"
    ],
    
    # ========================================
    # Management & Strategy
    # ========================================
    "Engineering Manager": [
        "engineering manager", "head of engineering", "development manager", 
        "team lead", "cto", "chief technology officer", "vp engineering",
        "director of engineering"
    ],
    "Product Manager": [
        "product manager", "product owner", "digital product manager",
        "technical product manager", "product lead"
    ],
    "Project Manager": [
        "project manager", "technical project manager", "it project manager",
        "scrum master", "agile coach", "delivery manager"
    ],
    "Business Analyst": [
        "business analyst", "technical business analyst", "process analyst",
        "systems analyst", "requirements analyst"
    ],
    "Solutions Architect": [
        "solutions architect", "enterprise architect", "technical architect", 
        "solution architect", "software architect", "system architect"
    ],
    
    # ========================================
    # Specialized/Niche
    # ========================================
    "Quantitative Analyst": [
        "quantitative analyst", "quant", "actuary", "algorithmic trader",
        "quantitative developer", "quant developer"
    ],
    "GIS Analyst": [
        "gis analyst", "gis", "spatial analyst", "geospatial",
        "gis developer", "geospatial analyst"
    ],
    
    # ========================================
    # Executive & Leadership
    # ========================================
    "Executive Leadership": [
        "head of", "director of", "chief", "partner", 
        "vp", "vice president", "executive", "c-level"
    ],
    "Data Leadership": [
        "head of data", "manager data", "data manager", 
        "data lead", "master data", "mdm"
    ],
    "Technical Lead": [
        "tech lead", "technical lead", "lead developer", 
        "delivery lead", "initiative lead", "architecture lead"
    ],

    # ========================================
    # Academic & Education
    # ========================================
    "Lecturer": [
        "lecturer", "professor", "phd", "research fellow", 
        "faculty", "teaching staff", "academic", "tutor",
        "instructor", "educator"
    ],

    # ========================================
    # Health & Clinical Informatics
    # ========================================
    "Health Informatics": [
        "clinical coder", "clinical data", "emr", "casemix", 
        "health data", "medical coder", "cognitive rater",
        "health informatics", "clinical informatics"
    ],

    # ========================================
    # Data Governance, Compliance & Strategy
    # ========================================
    "Data Governance & Compliance": [
        "data governance", "data protection", "data integrity", 
        "privacy", "compliance", "audit", "risk", "policy",
        "data quality", "data steward"
    ],
    "Strategy & Transformation": [
        "digital transformation", "strategy", "roadmap", 
        "change manager", "business development",
        "transformation lead", "innovation manager"
    ],

    # ========================================
    # Consulting & Implementation
    # ========================================
    "Technical Consultant": [
        "consultant", "advisor", "implementation specialist", 
        "integration specialist", "solution specialist",
        "technical advisor", "it consultant"
    ],
    "Graduate Program": [
        "graduate", "cadet", "intern", "trainee", 
        "early career", "digital futures", "graduate program"
    ],
    
    # ========================================
    # Niche / Other Tech
    # ========================================
    "SEO & Digital Marketing": [
        "seo", "search engine optimization", "digital marketing", 
        "marketing technology", "martech", "growth hacker",
        "digital strategist"
    ],
    "Intelligence & Security": [
        "intelligence officer", "tspv", "security clearance", 
        "defense", "intelligence analyst"
    ],
}

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
