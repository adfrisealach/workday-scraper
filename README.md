# Workday Scraper

<p align="left">
<img src="https://img.shields.io/github/languages/top/christopherlam888/workday-scraper.svg" >
<a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

A robust web scraper to get the latest job postings from Workday sites using JSON-LD extraction for significantly improved performance.

## Features

- **10-20x faster** than traditional scraping methods using JSON-LD extraction
- No browser dependencies required (no Selenium, no ChromeDriver)
- Scrape listings from any standard Workday job posting site
- Custom site list in text config file
- SQLite database storage for job data
- Optional JSON and RSS file output
- CSV export utility for data analysis
- Jupyter notebook integration for advanced analysis
- Email notification
- Telegram bot notification and commands
- Mode for all listings or only listings posted today
- Asynchronous processing for better performance
- Comprehensive logging system

## Setup

1. Clone the repository:
```bash
git clone https://github.com/adfrisealach/workday-scraper.git
cd workday-scraper
```

2. Create and activate a virtual environment:
```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a config file in the `configs/` directory (e.g., `configs/companies.txt`) with your target companies:
```
CompanyName,https://company.wd1.myworkdayjobs.com/en-US/External
```

## Basic Usage

1. Run the scraper:
```bash
python -m workday_scraper -f companies.txt
```

2. For email notifications, add email parameters:
```bash
python -m workday_scraper -f companies.txt -e your.email@gmail.com -pw your-password -r recipient@example.com
```

3. To export data to CSV:
```bash
python scripts/export_to_csv.py -o jobs.csv
```

## Project Structure

```
workday-scraper/
├── analysis/                 # Data analysis tools
├── config/                  # Environment configuration
├── configs/                 # Scraper configuration files
├── data/                   # Data storage
├── docker/                 # Docker configuration
├── docs/                   # Documentation
├── logs/                   # Log files
├── scripts/                # Utility scripts
└── workday_scraper/        # Main package
```

For detailed documentation:
- [Docker Setup](docs/DOCKER.md)
- [Implementation Details](docs/IMPLEMENTATION.md)
- [Deployment Guide](docs/PORTAINER-DEPLOYMENT.md)

## Optional Features

### Telegram Bot Setup

1. Create a bot via [BotFather](https://t.me/BotFather)
2. Get your chat ID using [@RawDataBot](https://t.me/RawDataBot)
3. Configure environment:
```bash
cp config/.env.sample .env
# Edit .env with your bot token and chat ID
```

### Data Analysis

The project includes a Jupyter notebook for analyzing job data:
```bash
pip install jupyter pandas matplotlib seaborn wordcloud
jupyter notebook analysis/job_data_analysis.ipynb
```

## Docker Support

For containerized deployment, see [Docker Setup Guide](docs/DOCKER.md) and [Portainer Deployment Guide](docs/PORTAINER-DEPLOYMENT.md).
