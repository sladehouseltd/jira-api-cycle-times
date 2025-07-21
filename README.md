# JIRA API Client

A Python script that searches for JIRA issues moved to "Done" status within a date range, filtered by delivery team and labels, and calculates cycle time metrics.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   The script uses `requests` library with `HTTPBasicAuth` for authentication.

2. **Configure JIRA credentials:**
   
   **Option A: Interactive prompts (Most Secure)**
   - Run the script without credentials
   - You'll be prompted for URL, username, and password
   - Password input is masked for security
   
   **Option B: Environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```
   
   **Option C: Environment variables**
   ```bash
   export JIRA_URL="https://your-company.atlassian.net"
   export JIRA_USERNAME="your_jira_username"
   export JIRA_PASSWORD="your_password"
   ```

3. **Authentication:**
   - Uses basic authentication with JIRA username and password
   - No API tokens required
   - Ensure your JIRA username is correct (may be different from your email)
   - Interactive prompts provide the most secure credential handling
   - Includes timeout and error handling for corporate network compatibility

## Usage

### Basic usage (with interactive prompts):
```bash
python3 jira_client.py PROJ "Frontend Team" "bug,urgent,frontend" 2024-01-01 2024-01-31
# You'll be prompted for JIRA URL, username, and password
```

### With .env file:
```bash
# Set up .env file first, then run:
python3 jira_client.py PROJ "Frontend Team" "bug,urgent,frontend" 2024-01-01 2024-01-31
```

### With command line credentials:
```bash
python3 jira_client.py PROJ "Frontend Team" "bug,urgent,frontend" 2024-01-01 2024-01-31 \
  --jira-url https://company.atlassian.net \
  --username your_jira_username \
  --password your_password
```

### With component analysis:
```bash
python3 jira_client.py PROJ "Frontend Team" "bug,urgent,frontend" 2024-01-01 2024-01-31 --component-analysis
```

### With different output formats:
```bash
# HTML output (best for Confluence - paste into source editor)
python3 jira_client.py PROJ "Frontend Team" "bug,urgent,frontend" 2024-01-01 2024-01-31 --output-format html

# Confluence wiki markup (native Confluence format)
python3 jira_client.py PROJ "Frontend Team" "bug,urgent,frontend" 2024-01-01 2024-01-31 --output-format confluence

# CSV format (import as tables)
python3 jira_client.py PROJ "Frontend Team" "bug,urgent,frontend" 2024-01-01 2024-01-31 --output-format csv

# Markdown format
python3 jira_client.py PROJ "Frontend Team" "bug,urgent,frontend" 2024-01-01 2024-01-31 --output-format markdown
```

### With component analysis:
```bash
python3 jira_client.py PROJ "Frontend Team" "bug,urgent,frontend" 2024-01-01 2024-01-31 --component-analysis --output-format html
```


## Parameters

- `project_key`: JIRA project prefix (e.g., "PROJ")
- `delivery_team`: Team name to filter by (searches in "Delivery Team" field)
- `labels`: Comma-separated labels to filter by (e.g., "bug,urgent,frontend")
- `start_date`: Start date for search (YYYY-MM-DD)
- `end_date`: End date for search (YYYY-MM-DD)

## Optional Arguments

- `--output-format`: Choose output format:
  - `console` (default) - Terminal output with colors and emojis
  - `markdown` - Markdown format with tables
  - `html` - HTML format (recommended for Confluence)
  - `confluence` - Confluence wiki markup (native format)
  - `csv` - CSV format for spreadsheets or table imports
- `--component-analysis`: Show cycle time breakdown by JIRA component
- `--label-analysis`: Show cycle time breakdown by labels
- `--in-progress-statuses`: Comma-separated list of "In Progress" statuses
- `--done-statuses`: Comma-separated list of "Done" statuses

## Security Notes

- **Never commit your `.env` file** - it's already in `.gitignore`
- Uses basic authentication with username and password
- The `.env.example` file shows the format but contains no real credentials
- Environment variables override `.env` file values
- Command line arguments override both environment and `.env` values

## Examples

```bash
# Find issues completed in December 2024 and tag them
python3 jira_client.py MYPROJ "Backend Team" "database,performance,critical" 2024-12-01 2024-12-31

# Search for specific team and labels
python3 jira_client.py TICKET "DevOps Team" "infrastructure,aws" 2024-01-15 2024-01-20

# Search specific week and override URL
python3 jira_client.py DEV "QA Team" "testing,automation" 2024-01-01 2024-01-07 \
  --jira-url https://dev-jira.company.com

# Find issues completed yesterday
python3 jira_client.py PROJ "Daily Team" "completed,sprint" 2024-01-15 2024-01-15
```

## How it works

The script searches for issues in the specified project that had their status changed to "Done", "Closed", or "Resolved" within the given date range, and filters by:

1. **Labels**: Must have ALL specified labels
2. **Delivery Team**: Searches for team name in "Delivery Team" field
3. **Cycle Time**: Calculates days between "In Progress" and "Done" status transitions

## Features

- **Issue Search**: Find completed issues by project, team, and labels
- **Cycle Time Calculation**: Automatic calculation of days from In Progress to Done
- **Status Tracking**: Shows exact dates when issues moved to In Progress and Done
- **Summary Statistics**: Average, min, max cycle times across all found issues
- **Flexible Status Mapping**: Recognizes various status names (In Progress, In Development, etc.)
- **Component Analysis**: Break down cycle times by JIRA component with rankings
- **Label Analysis**: Break down cycle times by labels
- **Multiple Output Formats**: 
  - **Console**: Rich terminal output with colors and emojis
  - **HTML**: Direct paste into Confluence source editor
  - **Confluence**: Native wiki markup format
  - **Markdown**: Standard markdown with tables
  - **CSV**: Spreadsheet-compatible format for data analysis

## JQL Query

The script builds JIRA Query Language (JQL) like this:
```
project = "PROJ" AND 
status CHANGED TO ("Done", "Closed", "Resolved") DURING ("2024-01-01", "2024-01-31") AND
labels = "bug" AND 
labels = "urgent" AND 
"Delivery Team" ~ "Frontend Team"
```

## Sample Output

### Regular Console Output
```
📋 PROJ-123: Fix login bug
     Labels: ['bug', 'urgent']
     Status: Done
     📅 In Progress: 2024-01-15 09:30
     ✅ Done: 2024-01-18 14:20
     ⏱️  Cycle Time: 3 days

📊 CYCLE TIME SUMMARY:
   Issues with cycle time data: 5/5
   Average cycle time: 4.2 days
   Min cycle time: 1 days
   Max cycle time: 8 days
   Total cycle time: 21 days

🏆 COMPONENT RANKING (by average cycle time):
   1. backend-service: 5.5 days avg (3 tickets)
   2. frontend-ui: 3.2 days avg (2 tickets)

🔧 COMPONENT ANALYSIS:
📦 backend-service (3 tickets):
     📋 PROJ-123: Fix login bug - 5 days
     📊 Summary: Avg: 5.5d, Min: 3d, Max: 8d, Total: 16d
```

### Markdown Output (for Confluence)
```markdown
# JIRA Cycle Time Analysis

## Search Criteria
- **Project:** PROJ
- **Delivery Team:** Frontend Team  
- **Labels:** bug, urgent
- **Date Range:** 2024-01-01 to 2024-01-31

## 📊 CYCLE TIME SUMMARY
- **Average cycle time:** 4.2 days
- **Min cycle time:** 1 days
- **Max cycle time:** 8 days

## 🏆 COMPONENT RANKING
| Rank | Component | Avg Days | Tickets |
|------|-----------|----------|---------|
| 1 | backend-service | 5.5 | 3 |
| 2 | frontend-ui | 3.2 | 2 |
```