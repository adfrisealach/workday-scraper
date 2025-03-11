# Data Transformation for Location Field

## Location Field Parsing

Let's transform the location field into separate columns for better analysis. The location field typically follows the structure "Region - Country - State - City", but sometimes there are multiple states in the same country for the same listing.

```python
# First, let's examine some examples of the location field
print("Sample location values:")
df['location'].sample(10).tolist()
```

```python
import re

# Function to parse location into components
def parse_location(location):
    if not isinstance(location, str) or not location.strip():
        return {'region': None, 'country': None, 'state': None, 'city': None}
    
    # Split by delimiter (typically ' - ' or ', ')
    parts = re.split(r'\s*-\s*|\\s*,\\s*', location)
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

# Apply the function to create new columns
location_components = df['location'].apply(parse_location).apply(pd.Series)
df = pd.concat([df, location_components], axis=1)

# Display the first few rows with the new columns
df[['location', 'region', 'country', 'state', 'city']].head()
```

## Handling Multiple States in the Same Country

Sometimes job listings have multiple states in the same country. Let's identify and handle these cases.

```python
# Function to identify and extract multiple states
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

# Apply the function to extract multiple states
df['states_list'] = df['state'].apply(extract_multiple_states)
df['multiple_states'] = df['states_list'].apply(lambda x: len(x) > 1)
df['states_count'] = df['states_list'].apply(len)

# Display jobs with multiple states
multi_state_jobs = df[df['multiple_states']]
print(f"Number of jobs with multiple states: {len(multi_state_jobs)}")
if len(multi_state_jobs) > 0:
    multi_state_jobs[['title', 'company', 'location', 'state', 'states_list']].head()
```

```python
# Create an exploded view for jobs with multiple states
# This will create a separate row for each state in a multi-state job
if len(multi_state_jobs) > 0:
    exploded_df = df[df['multiple_states']].explode('states_list').copy()
    exploded_df['state'] = exploded_df['states_list']
    print(f"Original multi-state jobs: {len(multi_state_jobs)}")
    print(f"Exploded rows: {len(exploded_df)}")
    exploded_df[['title', 'company', 'location', 'state']].head()
```

## Visualizing Location Data

Now that we have parsed the location data, let's create some visualizations to better understand the distribution of jobs by region, country, and state.

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
```

```python
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
```

```python
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

```python
# Heatmap of Region vs Country
if df['region'].notna().any() and df['country'].notna().any():
    region_country = pd.crosstab(df['region'], df['country'])
    plt.figure(figsize=(14, 8))
    sns.heatmap(region_country, annot=True, cmap='YlGnBu', fmt='d')
    plt.title('Number of Job Listings by Region and Country')
    plt.tight_layout()
    plt.show()
```

## Geographic Analysis for Multi-State Jobs

If we have jobs with multiple states, let's analyze them separately.

```python
# Analysis of multi-state jobs
if len(multi_state_jobs) > 0:
    # Count of jobs by number of states
    state_count_dist = multi_state_jobs['states_count'].value_counts().sort_index()
    plt.figure(figsize=(10, 6))
    state_count_dist.plot(kind='bar')
    plt.title('Distribution of Multi-State Jobs by Number of States')
    plt.xlabel('Number of States')
    plt.ylabel('Number of Job Listings')
    plt.tight_layout()
    plt.show()
    
    # Most common state combinations
    if len(exploded_df) > 0:
        state_combinations = multi_state_jobs['state'].value_counts().head(10)
        plt.figure(figsize=(12, 6))
        state_combinations.plot(kind='bar')
        plt.title('Top 10 State Combinations in Multi-State Jobs')
        plt.xlabel('State Combination')
        plt.ylabel('Number of Job Listings')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.show()