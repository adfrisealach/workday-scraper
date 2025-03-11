"""
Location Field Parsing for Workday Scraper

This module provides functions to parse the location field from Workday job listings
into separate components (region, country, state, city) and handle cases with multiple states.

To use in the main Jupyter notebook, copy and paste the following code after loading the data:

```python
# Import required libraries if not already imported
import re

# Add the location parsing functions
def parse_location(location):
    if not isinstance(location, str) or not location.strip():
        return {'region': None, 'country': None, 'state': None, 'city': None}
    
    # Split by delimiter (typically ' - ' or ', ')
    parts = re.split(r'\s*-\s*|\s*,\s*', location)
    parts = [p.strip() for p in parts if p.strip()]
    
    result = {
        'region': None,
        'country': None,
        'state': None,
        'city': None
    }
    
    # Assign parts based on position and length
    if len(parts) >= 4:  # Region - Country - State - City
        result['region'] = parts[0]
        result['country'] = parts[1]
        result['state'] = parts[2]
        result['city'] = parts[3]
    elif len(parts) == 3:  # Country - State - City or Region - Country - State
        # Heuristic: if the third part looks like a city, use Country-State-City pattern
        if any(city_indicator in parts[2].lower() for city_indicator in ['city', 'town', 'village', 'metro']):
            result['country'] = parts[0]
            result['state'] = parts[1]
            result['city'] = parts[2]
        else:  # Assume Region-Country-State pattern
            result['region'] = parts[0]
            result['country'] = parts[1]
            result['state'] = parts[2]
    elif len(parts) == 2:  # Country - State or State - City
        # Heuristic: if the second part is shorter, likely Country-State
        if len(parts[1]) < len(parts[0]):
            result['country'] = parts[0]
            result['state'] = parts[1]
        else:  # Assume State-City
            result['state'] = parts[0]
            result['city'] = parts[1]
    elif len(parts) == 1:  # Just one location component
        # Try to determine if it's a country, state, or city
        # This is a simplistic approach - in a real scenario, you might use a location database
        if parts[0].lower() in ['usa', 'us', 'united states', 'canada', 'uk', 'australia', 'germany', 'france', 'japan', 'china']:
            result['country'] = parts[0]
        else:
            result['state'] = parts[0]  # Default to state if we can't determine
    
    return result

def extract_multiple_states(state_field):
    if not isinstance(state_field, str) or not state_field.strip():
        return []
    
    # Common patterns for multiple states
    # 1. Separated by 'or': "CA or NY"
    # 2. Separated by '/': "CA/NY"
    # 3. Separated by '&': "CA & NY"
    # 4. Separated by comma: "CA, NY"
    # 5. Separated by 'and': "CA and NY"
    
    # Replace common separators with a standard one
    standardized = re.sub(r'\s+or\s+|\s*/\s*|\s*&\s*|\s+and\s+', ', ', state_field)
    
    # Split by comma and clean up
    states = [s.strip() for s in standardized.split(',') if s.strip()]
    
    return states

# Apply the functions to your DataFrame
location_components = df['location'].apply(parse_location).apply(pd.Series)
df = pd.concat([df, location_components], axis=1)

# Extract multiple states
df['states_list'] = df['state'].apply(extract_multiple_states)
df['multiple_states'] = df['states_list'].apply(lambda x: len(x) > 1)
df['states_count'] = df['states_list'].apply(len)

# Display the results
print("Sample of parsed location data:")
df[['location', 'region', 'country', 'state', 'city']].head()

# Check for multiple states
multi_state_jobs = df[df['multiple_states']]
print(f"Number of jobs with multiple states: {len(multi_state_jobs)}")
if len(multi_state_jobs) > 0:
    print("Sample of jobs with multiple states:")
    multi_state_jobs[['title', 'company', 'location', 'state', 'states_list']].head()

# Create an exploded view for multi-state jobs if needed
if len(multi_state_jobs) > 0:
    exploded_df = df[df['multiple_states']].explode('states_list').copy()
    exploded_df['state'] = exploded_df['states_list']
    print(f"Original multi-state jobs: {len(multi_state_jobs)}")
    print(f"Exploded rows: {len(exploded_df)}")
```

You can then add visualizations for the parsed location data:

```python
# Jobs by Region
if df['region'].notna().any():
    region_counts = df['region'].value_counts()
    plt.figure(figsize=(12, 6))
    region_counts.plot(kind='bar')
    plt.title('Number of Job Listings by Region')
    plt.xlabel('Region')
    plt.ylabel('Number of Job Listings')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

# Jobs by Country
if df['country'].notna().any():
    country_counts = df['country'].value_counts()
    plt.figure(figsize=(12, 6))
    country_counts.plot(kind='bar')
    plt.title('Number of Job Listings by Country')
    plt.xlabel('Country')
    plt.ylabel('Number of Job Listings')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

# Jobs by State (Top 15)
if df['state'].notna().any():
    state_counts = df['state'].value_counts().head(15)
    plt.figure(figsize=(12, 6))
    state_counts.plot(kind='bar')
    plt.title('Top 15 States by Number of Job Listings')
    plt.xlabel('State')
    plt.ylabel('Number of Job Listings')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()
```
"""

import re
import pandas as pd

def parse_location(location):
    """
    Parse a location string into components (region, country, state, city).
    
    Args:
        location (str): Location string, typically in format "Region - Country - State - City"
        
    Returns:
        dict: Dictionary with keys 'region', 'country', 'state', 'city'
    """
    if not isinstance(location, str) or not location.strip():
        return {'region': None, 'country': None, 'state': None, 'city': None}
    
    # Split by delimiter (typically ' - ' or ', ')
    parts = re.split(r'\s*-\s*|\s*,\s*', location)
    parts = [p.strip() for p in parts if p.strip()]
    
    result = {
        'region': None,
        'country': None,
        'state': None,
        'city': None
    }
    
    # Assign parts based on position and length
    if len(parts) >= 4:  # Region - Country - State - City
        result['region'] = parts[0]
        result['country'] = parts[1]
        result['state'] = parts[2]
        result['city'] = parts[3]
    elif len(parts) == 3:  # Country - State - City or Region - Country - State
        # Heuristic: if the third part looks like a city, use Country-State-City pattern
        if any(city_indicator in parts[2].lower() for city_indicator in ['city', 'town', 'village', 'metro']):
            result['country'] = parts[0]
            result['state'] = parts[1]
            result['city'] = parts[2]
        else:  # Assume Region-Country-State pattern
            result['region'] = parts[0]
            result['country'] = parts[1]
            result['state'] = parts[2]
    elif len(parts) == 2:  # Country - State or State - City
        # Heuristic: if the second part is shorter, likely Country-State
        if len(parts[1]) < len(parts[0]):
            result['country'] = parts[0]
            result['state'] = parts[1]
        else:  # Assume State-City
            result['state'] = parts[0]
            result['city'] = parts[1]
    elif len(parts) == 1:  # Just one location component
        # Try to determine if it's a country, state, or city
        # This is a simplistic approach - in a real scenario, you might use a location database
        if parts[0].lower() in ['usa', 'us', 'united states', 'canada', 'uk', 'australia', 'germany', 'france', 'japan', 'china']:
            result['country'] = parts[0]
        else:
            result['state'] = parts[0]  # Default to state if we can't determine
    
    return result

def extract_multiple_states(state_field):
    """
    Extract multiple states from a state field.
    
    Args:
        state_field (str): State field that may contain multiple states
        
    Returns:
        list: List of individual states
    """
    if not isinstance(state_field, str) or not state_field.strip():
        return []
    
    # Common patterns for multiple states
    # 1. Separated by 'or': "CA or NY"
    # 2. Separated by '/': "CA/NY"
    # 3. Separated by '&': "CA & NY"
    # 4. Separated by comma: "CA, NY"
    # 5. Separated by 'and': "CA and NY"
    
    # Replace common separators with a standard one
    standardized = re.sub(r'\s+or\s+|\s*/\s*|\s*&\s*|\s+and\s+', ', ', state_field)
    
    # Split by comma and clean up
    states = [s.strip() for s in standardized.split(',') if s.strip()]
    
    return states

def apply_location_parsing(df):
    """
    Apply location parsing to a DataFrame.
    
    Args:
        df (pandas.DataFrame): DataFrame with a 'location' column
        
    Returns:
        pandas.DataFrame: DataFrame with added location component columns
    """
    # Apply the function to create new columns
    location_components = df['location'].apply(parse_location).apply(pd.Series)
    df = pd.concat([df, location_components], axis=1)
    
    # Extract multiple states
    df['states_list'] = df['state'].apply(extract_multiple_states)
    df['multiple_states'] = df['states_list'].apply(lambda x: len(x) > 1)
    df['states_count'] = df['states_list'].apply(len)
    
    return df

def create_exploded_view(df):
    """
    Create an exploded view for multi-state jobs.
    
    Args:
        df (pandas.DataFrame): DataFrame with 'multiple_states' and 'states_list' columns
        
    Returns:
        pandas.DataFrame: Exploded DataFrame with one row per state for multi-state jobs
    """
    multi_state_jobs = df[df['multiple_states']]
    
    if len(multi_state_jobs) > 0:
        exploded_df = multi_state_jobs.explode('states_list').copy()
        exploded_df['state'] = exploded_df['states_list']
        return exploded_df
    
    return None