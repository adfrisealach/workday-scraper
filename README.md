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
- JSON and RSS file output
- Email notification
- Mode for all listings or only listings posted today
- Asynchronous processing for better performance
- Comprehensive logging system

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/adfrisealach/workday-scraper.git
   cd workday-scraper
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a config file in the `configs/` directory with your target companies:
   ```
   CompanyName,https://company.wd1.myworkdayjobs.com/en-US/External
   ```

## Usage

### Basic Usage

```bash
python -m workday_scraper -f <config_file>
```

Where `<config_file>` is the name of a file in the configs/ directory (e.g., autodesk.txt, alex.txt, etc.)

### Command-line Arguments

#### Required Arguments:
- `-f, --file`: Config file name in the configs/ directory

#### Email Notification Arguments (all three required if any are used):
- `-e, --email`: Email address to send notifications from
- `-pw, --password`: Password for the email account
- `-r, --recipients`: Comma-separated list of email recipients

#### Output Options:
- `-i, --initial`: Scrape all job listings, not just today's
- `-nj, --no-json`: Skip JSON output
- `-nr, --no-rss`: Skip RSS output

#### Performance Options:
- `-mw, --max-workers`: Maximum number of concurrent workers for parallel processing (default: 5)
- `-cs, --chunk-size`: Number of jobs to process in each chunk (default: 10)

#### Logging Options:
- `-l, --log-file`: Path to the log file (default: workday_scraper.log)
- `-ll, --log-level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: INFO)

### Examples

#### With Email Notification

```bash
python -m workday_scraper -f autodesk.txt -e your.email@gmail.com -pw your-password -r recipient@example.com
```

#### For All Job Listings (Not Just Today's)

```bash
python -m workday_scraper -f autodesk.txt -i
```

#### With Performance Options

```bash
python -m workday_scraper -f autodesk.txt -mw 10 -cs 20
```

#### With Logging Options

```bash
python -m workday_scraper -f autodesk.txt -l custom_log.log -ll DEBUG
```

## Output Files

The script generates the following output files in the current working directory:

- `job_postings.json`: Contains all scraped job information in JSON format
- `rss.xml`: Contains the same information in RSS format
- `job_ids.json`: Tracks which job IDs have been scraped to avoid duplicates

## Architecture

The Workday Scraper is built with a modular architecture that separates concerns and provides better control over the scraping process:

- **JSON-LD Extraction**: Uses structured data embedded in the pages for reliable and fast extraction
- **Asynchronous Processing**: Uses asyncio for efficient concurrent processing
- **Logging System**: Structured logging with context-aware information
- **Error Handling**: Comprehensive error handling with specific exception types and recovery strategies

## Supported Sites

Any standard Workday job posting site that includes JSON-LD structured data. The scraper automatically tries different URL formats to find the best one for each site.

## Features To Implement

- Support running multiple configs
- Add tests
- Add support for custom filters (e.g., by location, job type)
- Add support for continuous monitoring with a specified interval
