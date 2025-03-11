# Implementation Plan: `/jobs_at_location` Command

## Overview
Add a new command that allows users to view job listings for a specific location without cluttering the UI with buttons.

## Detailed Steps

### 1. Database Layer: Add a new method to `DatabaseManager`

```python
def get_jobs_by_specific_location(self, location: str) -> List[Dict[str, Any]]:
    """Get all jobs for a specific location.
    
    Args:
        location (str): The location to filter by. Partial matching is supported.
        
    Returns:
        list: A list of job dictionaries for the specified location.
    """
    try:
        # Use LIKE for partial matching, making it more user-friendly
        search_term = f"%{location}%"
        
        self.cursor.execute("""
            SELECT j.*, c.name as company_name, c.url as company_url
            FROM jobs j
            JOIN companies c ON j.company_id = c.id
            WHERE j.location LIKE ?
            ORDER BY j.created_at DESC
        """, (search_term,))
        
        results = self.cursor.fetchall()
        
        # Convert rows to dictionaries
        jobs = []
        for row in results:
            job = dict(row)
            job['company'] = job.pop('company_name')
            jobs.append(job)
        
        return jobs
    except Exception as e:
        logger.error(f"Error getting jobs for location '{location}': {str(e)}")
        return []
```

### 2. Command Handler: Add a new handler in `TelegramBot`

```python
async def handle_jobs_at_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /jobs_at_location command.
    
    Args:
        update (Update): The update object.
        context (ContextTypes.DEFAULT_TYPE): The context object.
    """
    if not context.args:
        await update.message.reply_text(
            "Please provide a location.\n"
            "Example: `/jobs_at_location California`\n"
            "Example: `/jobs_at_location United States - California`\n"
            "Use `/jobs_by_location` to see available locations."
        )
        return
    
    location = " ".join(context.args)
    await update.message.reply_text(f"Fetching jobs for location: {location}...")
    
    try:
        jobs = self.db_manager.get_jobs_by_specific_location(location)
        
        if not jobs:
            await update.message.reply_text(f"No jobs found for location: {location}")
            return
        
        # Format the message
        message = f"📍 *Jobs in {location}*\n\n"
        
        # Group jobs by title and company
        jobs_by_title_and_company = {}
        for job in jobs:
            title = job.get('title', 'Unknown Title')
            company = job.get('company', 'Unknown Company')
            
            key = (title, company)
            if key not in jobs_by_title_and_company:
                jobs_by_title_and_company[key] = {
                    'count': 0,
                    'url': job.get('url', '')  # Store one URL for reference
                }
            
            jobs_by_title_and_company[key]['count'] += 1
        
        # Add each job with company and URL
        for (title, company), details in sorted(jobs_by_title_and_company.items()):
            count = details['count']
            url = details['url']
            
            count_text = f"{count} positions" if count > 1 else "1 position"
            message += f"• *{title}* - {company} ({count_text})\n"
            if url:
                message += f"  [View Job]({url})\n"
            
            message += "\n"
        
        # Add total count
        unique_companies = len(set(company for (_, company), _ in jobs_by_title_and_company.items()))
        message += f"*Total*: {len(jobs)} jobs from {unique_companies} companies matching '{location}'"
        
        # Send the message
        await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Error handling jobs_at_location command: {str(e)}")
        await update.message.reply_text(f"Error fetching jobs: {str(e)}")
```

### 3. Register Command: Add to initialization in `TelegramBot.initialize()`

```python
# Add command handlers
self.application.add_handler(CommandHandler("start", self.handle_start))
self.application.add_handler(CommandHandler("help", self.handle_help))
self.application.add_handler(CommandHandler("jobs_by_location", self.handle_jobs_by_location))
self.application.add_handler(CommandHandler("jobs_at_location", self.handle_jobs_at_location))  # Add new handler
# ... [rest of the handlers]
```

### 4. Update Help Text: Modify the `handle_help` method

```python
message = (
    "🤖 *Workday Scraper Bot Commands*\n\n"
    "*/jobs_by_location* - Get job count by Country and State\n"
    "*/jobs_at_location* `<location>` - Get detailed job listings for a specific location\n"
    "   Example: `/jobs_at_location California`\n"
    # ... [rest of the help text]
)
```

### 5. Enhance `/jobs_by_location` Output: Add a hint at the end

In the `handle_jobs_by_location` method, after preparing the main message:

```python
# Add total only if we have jobs to show
if location_stats:
    total_jobs = sum(sum(states.values()) for states in location_stats.values())
    message += f"*Total*: {total_jobs} jobs"
    
    # Add hint about the new command
    message += "\n\n💡 *Tip:* Use `/jobs_at_location <location>` to see detailed job listings for a specific location."
```

## Benefits of This Approach

1. **User-Friendly**: Supports partial matching of location names making it easier for users
2. **Clear Output**: Organizes jobs by title and company with counts
3. **Direct Links**: Provides job URLs when available
4. **Discoverability**: Clear hints in help text and existing command output
5. **Clean UI**: Avoids cluttering the chat with numerous buttons
6. **Efficient Implementation**: Minimal changes to the existing codebase