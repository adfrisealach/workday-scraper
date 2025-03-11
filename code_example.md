# Code Implementation Example

## 1. Database Method Addition (in `db_manager.py`)

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

## 2. Command Handler (in `telegram_bot.py`)

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

## 3. Command Registration (in `telegram_bot.py`, `initialize` method)

```python
# Add command handlers
self.application.add_handler(CommandHandler("start", self.handle_start))
self.application.add_handler(CommandHandler("help", self.handle_help))
self.application.add_handler(CommandHandler("jobs_by_location", self.handle_jobs_by_location))
self.application.add_handler(CommandHandler("jobs_at_location", self.handle_jobs_at_location))  # Add this line
# ... rest of handlers
```

## 4. Help Text (in `telegram_bot.py`, `handle_help` method)

```python
message = (
    "🤖 *Workday Scraper Bot Commands*\n\n"
    "*/jobs_by_location* - Get job count by Country and State\n"
    "*/jobs_at_location* `<location>` - Get detailed job listings for a specific location\n"
    "   Example: `/jobs_at_location California`\n"
    "*/top_job_titles* - Get top 10 job titles with posting counts\n"
    # ... rest of help text
)
```

## 5. Adding Tip (in `handle_jobs_by_location` method)

```python
# Add total only if we have jobs to show
if location_stats:
    total_jobs = sum(sum(states.values()) for states in location_stats.values())
    message += f"*Total*: {total_jobs} jobs"
    
    # Add hint about the new command
    message += "\n\n💡 *Tip:* Use `/jobs_at_location <location>` to see detailed job listings for a specific location."
```

## Example User Interaction

### User Input:
```
/jobs_by_location
```

### Bot Response:
```
📊 Jobs by Location

United States (534)
• California (203)
• New York (87)
• Texas (65)
• Washington (42)
• Massachusetts (32)
• Other states...

Canada (156)
• Ontario (87)
• British Columbia (42)
• Quebec (27)

United Kingdom (98)
• England (76)
• Scotland (22)

Total: 788 jobs

💡 Tip: Use /jobs_at_location <location> to see detailed job listings for a specific location.
```

### User Input:
```
/jobs_at_location California
```

### Bot Response:
```
📍 Jobs in California

• Software Engineer - Autodesk (12 positions)
  [View Job](https://autodesk.com/careers/software-engineer-123)

• Data Scientist - Salesforce (5 positions)
  [View Job](https://salesforce.com/careers/data-scientist-456)

• UX Designer - Adobe (3 positions)
  [View Job](https://adobe.com/careers/ux-designer-789)

• Product Manager - Google (2 positions)
  [View Job](https://google.com/careers/product-manager-234)

Total: 22 jobs from 4 companies matching 'California'