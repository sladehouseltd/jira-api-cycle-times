# JIRA API Client

A collection of Python scripts for JIRA API operations:

1. **jira_client.py** - Searches for JIRA issues moved to "Done" status within a date range, filtered by delivery team and labels, and calculates cycle time metrics.
2. **jira_column_cleaner.py** - Manages JIRA board column configurations, removing unwanted statuses from columns.

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

### Analyzing ALL issues by component or label (without label filtering):
```bash
# Group ALL issues by their components (use empty string "" for labels parameter)
python3 jira_client.py PROJ "Frontend Team" "" 2024-01-01 2024-01-31 --component-analysis

# Group ALL issues by their labels (discovers and groups by ALL labels found)
python3 jira_client.py PROJ "Frontend Team" "" 2024-01-01 2024-01-31 --label-analysis

# Show both component AND label breakdowns for all issues
python3 jira_client.py PROJ "Frontend Team" "" 2024-01-01 2024-01-31 --component-analysis --label-analysis

# With markdown output (great for Confluence)
python3 jira_client.py PROJ "Frontend Team" "" 2024-01-01 2024-01-31 --label-analysis --output-format markdown
```

### Filtering by specific labels with analysis:
```bash
# Filter by specific labels AND show component breakdown
python3 jira_client.py PROJ "Frontend Team" "bug,urgent" 2024-01-01 2024-01-31 --component-analysis

# Filter by specific labels AND show label breakdown
python3 jira_client.py PROJ "Frontend Team" "bug,urgent" 2024-01-01 2024-01-31 --label-analysis
```

### With different output formats:
```bash
# HTML output (best for Confluence - paste into source editor)
python3 jira_client.py PROJ "Frontend Team" "" 2024-01-01 2024-01-31 --label-analysis --output-format html

# Confluence wiki markup (native Confluence format)
python3 jira_client.py PROJ "Frontend Team" "" 2024-01-01 2024-01-31 --component-analysis --output-format confluence

# CSV format (import as tables)
python3 jira_client.py PROJ "Frontend Team" "" 2024-01-01 2024-01-31 --output-format csv

# Markdown format with both analyses
python3 jira_client.py PROJ "Frontend Team" "" 2024-01-01 2024-01-31 --component-analysis --label-analysis --output-format markdown
```

### Saving output to a file:
```bash
# Save markdown output to a file
python3 jira_client.py PROJ "Team Name" "" 2024-01-01 2024-01-31 --label-analysis --output-format markdown > output.md

# Save component analysis to a markdown file
python3 jira_client.py PROJ "Team Name" "" 2024-01-01 2024-01-31 --component-analysis --output-format markdown > components_report.md

# Save both analyses to a file
python3 jira_client.py PROJ "Team Name" "" 2024-01-01 2024-01-31 --component-analysis --label-analysis --output-format markdown > full_report.md

# Save HTML output to a file (for Confluence)
python3 jira_client.py PROJ "Team Name" "" 2024-01-01 2024-01-31 --label-analysis --output-format html > confluence_report.html

# Save CSV output to a file (for spreadsheets)
python3 jira_client.py PROJ "Team Name" "" 2024-01-01 2024-01-31 --output-format csv > issues.csv
```


## Parameters

- `project_key`: JIRA project prefix (e.g., "PROJ")
- `delivery_team`: Team name to filter by (searches in "Delivery Team" field)
- `labels`: Comma-separated labels to filter by (e.g., "bug,urgent,frontend")
  - **Use `""` (empty string) to NOT filter by labels** - this allows you to analyze ALL issues
- `start_date`: Start date for search (YYYY-MM-DD)
- `end_date`: End date for search (YYYY-MM-DD)

## Optional Arguments

- `--output-format`: Choose output format:
  - `console` (default) - Terminal output with colors and emojis
  - `markdown` - Markdown format with tables
  - `html` - HTML format (recommended for Confluence)
  - `confluence` - Confluence wiki markup (native format)
  - `csv` - CSV format for spreadsheets or table imports
- `--component-analysis`: Show cycle time breakdown by JIRA component (available in all output formats)
  - Groups issues by their JIRA components
  - Shows ranking of components by average cycle time
  - Works with or without label filtering
- `--label-analysis`: Show cycle time breakdown by labels (available in all output formats)
  - Automatically discovers and groups by ALL labels found in matching issues
  - Shows ranking of labels by average cycle time
  - **Pro tip:** Use with `""` for labels parameter to analyze ALL issues across ALL labels
- `--in-progress-statuses`: Comma-separated list of "In Progress" statuses
- `--done-statuses`: Comma-separated list of "Done" statuses

## Toggling Between Component and Label Analysis

You can toggle between different analysis modes by including/excluding the flags:

| What you want | Command |
|---------------|---------|
| **Basic cycle times only** | `python3 jira_client.py PROJ "Team" "" 2024-01-01 2024-01-31` |
| **Component analysis only** | `python3 jira_client.py PROJ "Team" "" 2024-01-01 2024-01-31 --component-analysis` |
| **Label analysis only** | `python3 jira_client.py PROJ "Team" "" 2024-01-01 2024-01-31 --label-analysis` |
| **Both analyses** | `python3 jira_client.py PROJ "Team" "" 2024-01-01 2024-01-31 --component-analysis --label-analysis` |

## Security Notes

- **Never commit your `.env` file** - it's already in `.gitignore`
- Uses basic authentication with username and password
- The `.env.example` file shows the format but contains no real credentials
- Environment variables override `.env` file values
- Command line arguments override both environment and `.env` values

## Examples

```bash
# Analyze ALL issues completed in December 2024, grouped by labels
python3 jira_client.py MYPROJ "Backend Team" "" 2024-12-01 2024-12-31 --label-analysis

# Analyze ALL issues completed in December 2024, grouped by components
python3 jira_client.py MYPROJ "Backend Team" "" 2024-12-01 2024-12-31 --component-analysis

# Find issues with specific labels only (no grouping analysis)
python3 jira_client.py TICKET "DevOps Team" "infrastructure,aws" 2024-01-15 2024-01-20

# Analyze specific labeled issues grouped by component
python3 jira_client.py DEV "QA Team" "testing,automation" 2024-01-01 2024-01-07 --component-analysis

# Full analysis - all issues grouped by BOTH components and labels in markdown format
python3 jira_client.py PROJ "Daily Team" "" 2024-01-01 2024-01-31 --component-analysis --label-analysis --output-format markdown
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
- **Label Analysis**: Break down cycle times by labels with rankings
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

🏆 COMPONENT RANKING (by average cycle time):
   1. backend-service: 5.5 days avg (3 tickets)
   2. frontend-ui: 3.2 days avg (2 tickets)

🔧 COMPONENT ANALYSIS:
📦 backend-service (3 tickets):
     📋 PROJ-123: Fix login bug - 5 days
     📊 Summary: Avg: 5.5d, Min: 3d, Max: 8d

🏆 LABEL RANKING (by average cycle time):
   1. urgent: 6.5 days avg (2 tickets)
   2. bug: 3.5 days avg (4 tickets)

🏷️ LABEL ANALYSIS:
🏷️ urgent (2 tickets):
     📋 PROJ-125: Critical security fix - 8 days
     📋 PROJ-126: Production outage - 5 days
     📊 Summary: Avg: 6.5d, Min: 5d, Max: 8d

🏷️ bug (4 tickets):
     📋 PROJ-123: Fix login bug - 5 days
     📋 PROJ-124: Button not working - 2 days
     📊 Summary: Avg: 3.5d, Min: 2d, Max: 5d
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

## 🏷️ LABEL RANKING
| Rank | Label | Avg Days | Tickets |
|------|-------|----------|---------|
| 1 | urgent | 6.5 | 2 |
| 2 | bug | 3.5 | 4 |
```

---

# JIRA Column Cleaner

Clean up JIRA board columns by removing unwanted statuses. Useful for boards that have accumulated too many statuses over time.

## Usage

### List all boards
```bash
python3 jira_column_cleaner.py --list-boards
```

### Show board configuration
```bash
python3 jira_column_cleaner.py BOARD_ID --show-config
```

### List statuses in a specific column
```bash
python3 jira_column_cleaner.py BOARD_ID --list-column-statuses "In Progress"
```

### Find status by name
```bash
python3 jira_column_cleaner.py --find-status "In Progress"
```

### Clean column (keep specific statuses)
```bash
# Dry run first (recommended)
python3 jira_column_cleaner.py BOARD_ID "In Progress" "In Progress,In Review" --dry-run

# Actually clean the column
python3 jira_column_cleaner.py BOARD_ID "In Progress" "In Progress,In Review"
```

### Remove specific number of statuses (for testing)
```bash
# Dry run - remove first 10 statuses
python3 jira_column_cleaner.py BOARD_ID "In Progress" --remove-count 10 --dry-run

# Actually remove first 10 statuses
python3 jira_column_cleaner.py BOARD_ID "In Progress" --remove-count 10
```

## Parameters

- `board_id`: JIRA board ID (found in board URL)
- `column_name`: Name of the column to clean (e.g. "In Progress", "Development")
- `keep_statuses`: Comma-separated list of statuses to keep (when not using --remove-count)

## Options

- `--dry-run`: Show what would be changed without making actual changes
- `--list-boards`: List all accessible boards
- `--show-config`: Show current board configuration
- `--list-column-statuses "COLUMN"`: List status names in specified column
- `--find-status "STATUS"`: Find status ID by name
- `--remove-count N`: Remove only the first N statuses (useful for incremental cleanup)

## Authentication

Uses the same authentication as jira_client.py (environment variables, .env file, or interactive prompts).

## Important Notes

- **Requires JIRA admin or board admin permissions** to modify board configurations
- **Safe operation**: Removing statuses from columns doesn't affect existing tickets - they just become "unmapped" from the board view
- **Always use --dry-run first** to see what will be changed
- Tickets with removed statuses remain accessible via JQL and issue views
- **405 Method Not Allowed** error usually means insufficient permissions

## Examples

```bash
# Find your board
python3 jira_column_cleaner.py --list-boards

# See what's in the "In Progress" column
python3 jira_column_cleaner.py 123 --list-column-statuses "In Progress"

# Test removing 5 statuses
python3 jira_column_cleaner.py 123 "In Progress" --remove-count 5 --dry-run

# Keep only "In Progress" and "Code Review" statuses
python3 jira_column_cleaner.py 123 "In Progress" "In Progress,Code Review" --dry-run
```