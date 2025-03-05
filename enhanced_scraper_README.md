# Enhanced Workday Scraper

This is an enhanced version of the Workday Scraper that provides better debugging capabilities, more detailed logging, and improved reliability. It's designed to help diagnose and fix issues with scraping specific Workday sites.

## Features

- **Robust Element Selection**: Tries multiple selectors to find job elements
- **Detailed Logging**: Provides comprehensive logging of what it's doing
- **Debug Mode**: Special mode that tries different selectors and saves detailed information
- **Visible Browser Option**: Run Chrome in visible mode for better debugging
- **Adaptive Rate Limiting**: Prevents overwhelming servers and getting blocked
- **Efficient Session Management**: Reuses browser sessions for better performance
- **Controlled Parallel Processing**: Processes jobs in chunks to avoid overwhelming servers
- **Comprehensive Error Handling**: Better recovery from errors with specific strategies

## Usage

### Basic Usage

```bash
python workday_scraper_enhanced.py -f <config_file>
```

Replace `<config_file>` with the name of your config file in the `configs/` directory (e.g., `autodesk.txt`).

### Debug Mode

```bash
python workday_scraper_enhanced.py -f <config_file> -d
```

The `-d` or `--debug` flag enables debug mode, which:
- Tries different XPath selectors to find job elements
- Saves the HTML of pages for inspection
- Provides more detailed logging

### Visible Browser Mode

```bash
python workday_scraper_enhanced.py -f <config_file> -nh
```

The `-nh` or `--no-headless` flag runs Chrome in visible mode (not headless), which can help with debugging.

### Performance Options

```bash
python workday_scraper_enhanced.py -f <config_file> -ms 5 -mw 10 -cs 20
```

Where:
- `-ms` or `--max-sessions`: Maximum number of concurrent browser sessions (default: 3)
- `-mw` or `--max-workers`: Maximum number of concurrent workers for parallel processing (default: 5)
- `-cs` or `--chunk-size`: Number of jobs to process in each chunk (default: 10)

### Logging Options

```bash
python workday_scraper_enhanced.py -f <config_file> -l custom_log.log -ll DEBUG
```

Where:
- `-l` or `--log-file`: Path to the log file (default: workday_scraper_enhanced.log)
- `-ll` or `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: DEBUG)

## How It Works

The enhanced scraper uses a modular architecture with several key components:

1. **Element Selector**: Tries multiple selectors with fallbacks to find elements on the page
2. **Session Manager**: Efficiently manages browser sessions for better performance
3. **Rate Limiter**: Adaptively adjusts delay between requests based on success/failure patterns
4. **Parallel Processor**: Controls parallel processing with chunking to avoid overwhelming servers
5. **Error Handler**: Provides comprehensive error handling with specific recovery strategies
6. **Logger**: Structured logging with context-aware information

In debug mode, it will:
1. Try different XPath selectors for job elements
2. Save the HTML of pages for inspection
3. Provide detailed information about what it finds
4. Try to find job details within elements
5. Try to find the next page button

## Troubleshooting

If the enhanced scraper still fails to find job elements, check the saved HTML files (e.g., `autodesk_debug_page.html`) to see what the page actually contains. You can open these files in a browser to inspect them.

You might need to:

1. Update the selectors in the `element_selection.py` file to match the actual HTML structure
2. Try a different URL with more specific filters
3. Check if the site requires authentication or has anti-scraping measures

## Dependencies

The enhanced scraper requires the same dependencies as the main Workday Scraper:
- selenium
- tqdm
- webdriver-manager (optional but recommended)

## Integrating with Main Script

Once you've identified the working configuration and selectors, you can update the selectors in the `element_selection.py` file to make them work with the specific Workday site.