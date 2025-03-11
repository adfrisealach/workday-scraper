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

#### Database Options:
- `-db, --db-file`: Path to the SQLite database file (default: workday_jobs.db)

#### Output Options:
- `-i, --initial`: Scrape all job listings, not just today's
- `-j, --json`: Output to JSON (default: disabled)
- `-rs, --rss`: Output to RSS (default: disabled)

#### Email Notification Arguments (all three required if any are used):
- `-e, --email`: Email address to send notifications from
- `-pw, --password`: Password for the email account
- `-r, --recipients`: Comma-separated list of email recipients

#### Performance Options:
- `-mw, --max-workers`: Maximum number of concurrent workers for parallel processing (default: 5)
- `-cs, --chunk-size`: Number of jobs to process in each chunk (default: 10)

#### Logging Options:
- `-l, --log-file`: Path to the log file (default: workday_scraper.log)
- `-ll, --log-level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: INFO)

### Examples

#### Basic Usage (Save to Database Only)

```bash
python -m workday_scraper -f autodesk.txt
```

#### With JSON and RSS Output

```bash
python -m workday_scraper -f autodesk.txt -j -rs
```

#### With Email Notification

```bash
python -m workday_scraper -f autodesk.txt -e your.email@gmail.com -pw your-password -r recipient@example.com
```

#### For All Job Listings (Not Just Today's)

```bash
python -m workday_scraper -f autodesk.txt -i
```

#### With Custom Database File

```bash
python -m workday_scraper -f autodesk.txt -db custom_jobs.db
```

#### With Performance Options

```bash
python -m workday_scraper -f autodesk.txt -mw 10 -cs 20
```

#### With Logging Options

```bash
python -m workday_scraper -f autodesk.txt -l custom_log.log -ll DEBUG
```

## Telegram Bot Integration

The Workday Scraper includes a Telegram bot that provides notifications when scrapes complete and allows you to interact with the scraped data through commands.

### Setup

1. Create a Telegram bot using [BotFather](https://t.me/BotFather) and get your bot token
2. Get your chat ID (you can use [@RawDataBot](https://t.me/RawDataBot) or [@userinfobot](https://t.me/userinfobot))
3. Set up environment variables using one of these methods:

   **Method 1:** Export variables directly (temporary, session only):
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token"
   export TELEGRAM_CHAT_ID="your_chat_id"
   ```
   
   **Method 2:** Create a .env file (persistent):
   ```bash
   # Copy the sample file
   cp .env.sample .env
   
   # Edit the file with your values
   nano .env
   ```
   
   **Method 3:** Run the setup script which will guide you through the process:
   ```bash
   ./setup_environment.sh
   ```

### Running the Bot

You can run the Telegram bot in two ways:

1. **Standalone mode** - The bot runs independently and is always available for queries:
   ```bash
   ./run_telegram_bot.py
   ```
   
   Options:
   - `-db, --db-file`: Path to the SQLite database file (default: workday_jobs.db)
   - `-l, --log-file`: Path to the log file (default: telegram_bot.log)
   - `-ll, --log-level`: Logging level (default: INFO)

2. **Integrated mode** - The bot is automatically started when running a scrape job (if environment variables are set):
   ```bash
   python -m workday_scraper -f autodesk.txt
   ```

### Bot Commands

The Telegram bot supports the following commands:

- `/start` - Get started with the bot
- `/help` - Show available commands
- `/jobs_by_location` - Get job count by Country and State
- `/top_job_titles` - Get top 10 job titles with posting counts
- `/search_jobs <keyword>` - Search for jobs with title containing a keyword and see locations sorted by posting date
  - Example: `/search_jobs data analyst`
- `/run_scrape <config_file> [options]` - Manually trigger the scraper
  - Example: `/run_scrape autodesk.txt -i`
- `/list_configs` - List available config files
- `/scrape_status` - Check status of running scrape jobs

The `/search_jobs` command is particularly useful as it shows job postings sorted by recency (most recent first), with each listing showing how many days ago it was posted when that information is available.

### Notifications

When a scrape job completes, the bot will automatically send two types of notifications:

1. **Summary Notification:**
   - Number of new jobs found
   - Breakdown by company
   - Top locations
   - Suggestions for commands to explore the data

2. **Detailed Job Listings:**
   - A comprehensive list of all new jobs found
   - Each listing shows the job title and location
   - For large numbers of jobs, listings will be split across multiple messages

## Output Files

The script generates the following output files:

- `workday_jobs.db`: SQLite database containing all scraped job information (default)
- `job_postings.json`: Contains scraped job information in JSON format (optional)
- `rss.xml`: Contains the same information in RSS format (optional)
- `job_ids.json`: Tracks which job IDs have been scraped to avoid duplicates (for backward compatibility)

## CSV Export Utility

The scraper includes a CSV export utility to export job data from the database to CSV format for data analysis.

### Usage

```bash
python export_to_csv.py [options]
```

### Command-line Arguments

- `-db, --db-file`: Path to the SQLite database file (default: workday_jobs.db)
- `-o, --output`: Path to the output CSV file (default: job_export.csv)
- `-c, --company`: Filter by company name
- `-sd, --start-date`: Filter by start date (YYYY-MM-DD)
- `-ed, --end-date`: Filter by end date (YYYY-MM-DD)

### Examples

#### Export All Jobs

```bash
python export_to_csv.py
```

#### Export Jobs for a Specific Company

```bash
python export_to_csv.py -c "CompanyName"
```

#### Export Jobs for a Date Range

```bash
python export_to_csv.py -sd 2023-01-01 -ed 2023-12-31
```

#### Export to a Custom File

```bash
python export_to_csv.py -o custom_export.csv
```

## Jupyter Notebook Integration

The scraper includes a sample Jupyter notebook (`job_data_analysis.ipynb`) that demonstrates how to load job data from the SQLite database and perform data analysis using pandas, matplotlib, and seaborn.

To use the notebook:

1. Make sure you have installed the required dependencies:
   ```bash
   pip install jupyter pandas matplotlib seaborn wordcloud
   ```

2. Start Jupyter Notebook:
   ```bash
   jupyter notebook
   ```

3. Open the `job_data_analysis.ipynb` notebook and run the cells to analyze your job data.

## Architecture

The Workday Scraper is built with a modular architecture that separates concerns and provides better control over the scraping process:

- **JSON-LD Extraction**: Uses structured data embedded in the pages for reliable and fast extraction
- **Database Storage**: Uses SQLite for efficient and portable data storage
- **Asynchronous Processing**: Uses asyncio for efficient concurrent processing
- **Logging System**: Structured logging with context-aware information
- **Error Handling**: Comprehensive error handling with specific exception types and recovery strategies
- **Data Analysis**: Integrated tools for exporting and analyzing job data

## Supported Sites

Any standard Workday job posting site that includes JSON-LD structured data. The scraper automatically tries different URL formats to find the best one for each site.

## Repository Organization

### Archive Directory

The repository includes an `archive` directory that contains files that are no longer actively used but are preserved for reference:

- `location_transformation.py`: Jupyter notebook-style code with location parsing snippets, replaced by the more comprehensive `location_field_parsing.py` module
- `simple_test.py`: Basic environment and setup test script, superseded by the more comprehensive `test_telegram_bot.py`

## Features To Implement

- Support running multiple configs
- Add tests
- Add support for custom filters (e.g., by location, job type)
- Add support for continuous monitoring with a specified interval
