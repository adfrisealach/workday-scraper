# Implementation Diagrams and Details

## Sequence Diagram: User Flow

```mermaid
sequenceDiagram
    participant User
    participant TelegramBot
    participant DatabaseManager
    participant Database
    
    Note over User,TelegramBot: Scenario 1: User browses locations
    User->>TelegramBot: /jobs_by_location
    TelegramBot->>DatabaseManager: _get_jobs_by_location()
    DatabaseManager->>Database: Query locations and counts
    Database-->>DatabaseManager: Location stats
    DatabaseManager-->>TelegramBot: Country/state breakdown
    TelegramBot-->>User: Display locations with counts
    Note right of User: User sees location list with<br/>tip to use /jobs_at_location
    
    Note over User,TelegramBot: Scenario 2: User requests specific location jobs
    User->>TelegramBot: /jobs_at_location California
    TelegramBot->>DatabaseManager: get_jobs_by_specific_location("California")
    DatabaseManager->>Database: Query jobs matching location
    Database-->>DatabaseManager: Matching job records
    DatabaseManager-->>TelegramBot: Job listings
    TelegramBot-->>User: Display jobs grouped by title & company
    Note right of User: User sees job listings with<br/>title, company, count and links
```

## Component Interaction

```mermaid
graph TD
    User([User]) --> |1. Sends commands| TelegramBot
    TelegramBot --> |2. Processes commands| Handlers
    Handlers --> |3. Requests data| DatabaseManager
    DatabaseManager --> |4. Queries| Database[(SQLite Database)]
    Database --> |5. Returns results| DatabaseManager
    DatabaseManager --> |6. Formats data| Handlers
    Handlers --> |7. Sends response| TelegramBot
    TelegramBot --> |8. Displays results| User
    
    subgraph "New Components"
        style JobsAtLocationHandler fill:#f9f,stroke:#333,stroke-width:2px
        style GetJobsByLocation fill:#f9f,stroke:#333,stroke-width:2px
        JobsAtLocationHandler["/jobs_at_location Handler"]
        GetJobsByLocation["get_jobs_by_specific_location()"]
    end
    
    Handlers --> JobsAtLocationHandler
    JobsAtLocationHandler --> GetJobsByLocation
    GetJobsByLocation --> DatabaseManager
```

## Files to Modify

1. `workday_scraper/db_manager.py`
   - Add new method: `get_jobs_by_specific_location(location: str)`

2. `workday_scraper/telegram_bot.py`
   - Add new handler: `handle_jobs_at_location(update, context)`
   - Update `initialize()` to register new handler
   - Update `handle_help()` to include new command
   - Modify `handle_jobs_by_location()` to add usage hint

## Implementation Alternatives Considered

### Alternative 1: Add buttons to `/jobs_by_location` output
- **Pros**: Direct interaction without typing commands
- **Cons**: Too many buttons for many locations, clutters the UI

### Alternative 2: Implement fuzzy matching for location names
- **Pros**: More forgiving of typos and partial names
- **Cons**: Might return unexpected results, additional complexity

### Alternative 3: Add pagination to job results
- **Pros**: Handles large result sets better
- **Cons**: More complex UI, might be confusing for users

### Chosen Solution: New command with partial matching
- **Pros**: Clean UI, familiar command pattern, supports partial location names
- **Cons**: Requires typing a command (mitigated by copy-paste from location list)