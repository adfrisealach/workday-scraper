# Workday Scraper

<p align="left">
<img src="https://img.shields.io/github/languages/top/christopherlam888/workday-scraper.svg" >
<a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

A robust web scraper to get the latest job postings from Workday sites.

## Features

- Scrape listings from any standard Workday job posting site
- Custom site list in text config file
- JSON and RSS file output
- Email notification
- Mode for all listings or only listings posted today
- Enhanced error handling and debugging capabilities
- Automatic ChromeDriver management
- Adaptive rate limiting to avoid overwhelming servers
- Efficient session management for better performance
- Controlled parallel processing with chunking
- Comprehensive logging system

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/christopherlam888/workday-scraper.git
   cd workday-scraper
   ```

2. Run the setup script to install dependencies:
   ```bash
   ./setup_environment.sh
   ```
   
   Or manually install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install webdriver-manager
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

### With Email Notification

```bash
python -m workday_scraper -f <config_file> -e your.email@gmail.com -pw your-password -r recipient@example.com
```

### For All Job Listings (Not Just Today's)

```bash
python -m workday_scraper -f <config_file> -i
```

### With Performance Options

```bash
python -m workday_scraper -f <config_file> -ms 5 -mw 10 -cs 20
```

Where:
- `-ms` or `--max-sessions`: Maximum number of concurrent browser sessions (default: 3)
- `-mw` or `--max-workers`: Maximum number of concurrent workers for parallel processing (default: 5)
- `-cs` or `--chunk-size`: Number of jobs to process in each chunk (default: 10)

### With Logging Options

```bash
python -m workday_scraper -f <config_file> -l custom_log.log -ll DEBUG
```

Where:
- `-l` or `--log-file`: Path to the log file (default: workday_scraper.log)
- `-ll` or `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: INFO)

## Enhanced Debugging

If you encounter issues with specific Workday sites, use the enhanced debugging scraper:

```bash
python workday_scraper_enhanced.py -f <config_file> -d
```

The `-d` or `--debug` flag enables debug mode with more verbose output and tries different selectors to find job elements.

You can also run the browser in visible mode (not headless) for better debugging:

```bash
python workday_scraper_enhanced.py -f <config_file> -nh
```

## Architecture

The Workday Scraper is built with a modular architecture that separates concerns and provides better control over the scraping process:

- **Logging System**: Structured logging with context-aware information
- **Error Handling**: Comprehensive error handling with specific exception types and recovery strategies
- **Element Selection**: Robust element selection with multiple fallback selectors
- **Rate Limiting**: Adaptive rate limiting to avoid overwhelming servers
- **Session Management**: Efficient session management for better performance
- **Parallel Processing**: Controlled parallel processing with chunking

## Supported Sites

Any standard Workday job posting site. If you encounter a site that doesn't work, please use the enhanced debugging scraper to diagnose the issue.

## Features To Implement

- Support running multiple configs
- Add tests
- Add support for custom filters (e.g., by location, job type)
- Add support for continuous monitoring with a specified interval
