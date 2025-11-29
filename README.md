# Jobly - Australian Job Market Scraper

A comprehensive tool for scraping and analyzing job postings from the Australian job market, with a focus on tech roles.

## Features

- **Web Scraping**: Automated scraping from major Australian job boards (Seek, Prosple, GradConnection)
- **LLM Analysis**: AI-powered job description analysis using OpenAI
- **Structured Data**: Extracts skills, tools, responsibilities, and more
- **Supabase Storage**: Cloud-based storage with deduplication
- **Scheduled Runs**: Automated daily scraping and processing
- **Analytics Ready**: Data structured for trend analysis
- **Docker Support**: Run individual or multiple scrapers using Docker Compose

## Project Structure

```
AUJobsScraper/
├── jobly/                  # Main package
│   ├── analyzers/         # LLM-based job analysis
│   ├── db/                # Database interactions
│   ├── scrapers/          # Web scraping modules
│   └── config.py          # Configuration management
├── scripts/               # Executable scripts
│   ├── run_scraper.py    # Run the web scraper
│   ├── run_processor.py  # Run job analysis
│   └── scheduler.py      # Scheduled automation
├── tests/                 # Test suite
└── pyproject.toml        # Project configuration
```

## Setup

### Prerequisites

- Python 3.10+
- Playwright (for web scraping)
- Supabase account
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/AUJobsScraper.git
   cd AUJobsScraper
   ```

2. **Install the package**
   ```bash
   pip install -e .
   ```

3. **Install Playwright browsers**
   ```bash
   playwright install chromium
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   # Supabase
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   
   # OpenAI
   OPENAI_API_KEY=your_openai_api_key
   
   # Optional: Override defaults
   SCRAPER_MAX_PAGES=5
   SCRAPER_DAYS_FROM_POSTED=7
   PROCESSOR_BATCH_SIZE=10
   MODEL_JOB_ANALYZER_MODEL=gpt-4o-mini
   ```

### Database Setup

1. Create a Supabase project
2. Run the schema from `jobly/db/schema.sql` to set up the `job_postings` table

## Usage

### Run the Scraper

Collect job postings from job boards. The scraper supports multiple platforms:

**Command-line usage:**

```bash
# Run Seek scraper (default)
python scripts/run_scraper.py

# Run specific scrapers
python scripts/run_scraper.py --scraper seek
python scripts/run_scraper.py --scraper prosple
python scripts/run_scraper.py --scraper gradconnection
```

**Available platforms:**
- `seek`: Seek.com.au
- `prosple`: Prosple (au.prosple.com)
- `gradconnection`: GradConnection (au.gradconnection.com)

### Run the Processor

Analyze job descriptions with LLM:

```bash
python scripts/run_processor.py
```

### Run the Scheduler

Automate daily scraping and processing:

```bash
python scripts/scheduler.py
```

Set `RUN_ON_STARTUP=true` in your environment to run immediately on start.

## Docker Deployment

Run scrapers and processor using Docker Compose. Each scraper platform runs as a separate service.

### Prerequisites

- Docker and Docker Compose installed
- `.env` file configured (same variables as above)

### Build and Run

**Build the Docker image**:
```bash
docker-compose build
```

**Run all scraper services** (all platforms + processor):
```bash
docker-compose up
```

**Run in detached mode** (background):
```bash
docker-compose up -d
```

### Managing Scraper Services

The following scraper services are available:
- `scraper-seek`: Seeks.com.au scraper
- `scraper-prosple`: Prosple scraper
- `scraper-gradconnection`: GradConnection scraper
- `processor`: Job analyzer/processor

**Run individual scrapers**:
```bash
# Run only Seek scraper
docker-compose up scraper-seek

# Run only Prosple scraper
docker-compose up scraper-prosple

# Run only GradConnection scraper
docker-compose up scraper-gradconnection

# Run only the processor
docker-compose up processor
```

**Run multiple specific services**:
```bash
# Run Seek and Prosple scrapers together
docker-compose up scraper-seek scraper-prosple

# Run all scrapers (no processor)
docker-compose up scraper-seek scraper-prosple scraper-gradconnection

# Run scrapers + processor
docker-compose up scraper-seek processor
```

**View logs**:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f scraper-seek
docker-compose logs -f scraper-prosple
docker-compose logs -f scraper-gradconnection
docker-compose logs -f processor
```

**Stop services**:
```bash
docker-compose down
```

**Restart services**:
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart scraper-seek
```

### Resource Management

The `docker-compose.yml` uses resource-efficient logging settings. You can add resource limits for each service if needed:
```yaml
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 512M
```

## Configuration

Configuration is managed via Pydantic Settings in `jobly/config.py`. You can override defaults using environment variables:

### Scraper Settings
- `SCRAPER_SEARCH_KEYWORDS`: Comma-separated job search terms
- `SCRAPER_MAX_PAGES`: Maximum pages to scrape per keyword (default: 5)
- `SCRAPER_DAYS_FROM_POSTED`: How many days back to search (default: 7)

### Processor Settings
- `PROCESSOR_BATCH_SIZE`: Number of jobs to process at once (default: 10)

### Model Settings
- `MODEL_JOB_ANALYZER_MODEL`: OpenAI model name (default: gpt-4o-mini)
- `MODEL_JOB_ANALYZER_TEMPERATURE`: LLM temperature (default: 0.0)

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black jobly/ scripts/ tests/
```

### Linting

```bash
ruff check jobly/ scripts/ tests/
```

## Architecture

### Scrapers
- **BaseScraper**: Abstract base class for all scrapers
- **SeekScraper**: Scrapes jobs from Seek.com.au
- **ProspleScraper**: Scrapes jobs from Prosple (au.prosple.com)
- **GradConnectionScraper**: Scrapes jobs from GradConnection (au.gradconnection.com)
- Extensible design for adding more job boards

### Database
- **BaseDatabase**: Common Supabase initialization
- **JobDatabase**: Job posting CRUD operations with smart deduplication

### Analyzers
- **JobAnalyzer**: Uses LangChain + OpenAI to extract structured data from job descriptions
- Extracts: technical skills, soft skills, tools, responsibilities, seniority, etc.

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.
