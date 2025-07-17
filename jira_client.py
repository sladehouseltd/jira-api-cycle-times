#!/usr/bin/env python3
"""
JIRA API Client Script

This script finds JIRA issues that moved to Done status within a date range
and match specific delivery team and labels criteria.

Parameters:
- project_key: JIRA project prefix (e.g., "PROJ")
- delivery_team: Team name to search for (string)
- labels: Comma-separated list of labels to filter by (e.g., "bug,urgent,frontend")
- start_date: Start date for search (YYYY-MM-DD)
- end_date: End date for search (YYYY-MM-DD)
"""

import argparse
import sys
import json
import os
import getpass
from datetime import datetime, timedelta
from typing import List, Dict

try:
    import requests
    from requests.auth import HTTPBasicAuth
except ImportError:
    print("Error: 'requests' library not found. Install it with: pip install -r requirements.txt")
    sys.exit(1)


def load_env_file(env_file: str = ".env"):
    """Load environment variables from .env file if it exists."""
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value


def get_jira_credentials(args):
    """Get JIRA credentials from args, environment, or interactive prompts."""
    # Check command line arguments first
    jira_url = args.jira_url
    username = args.username
    password = args.password
    
    # Fall back to environment variables
    if not jira_url:
        jira_url = os.getenv('JIRA_URL')
    if not username:
        username = os.getenv('JIRA_USERNAME')
    if not password:
        password = os.getenv('JIRA_PASSWORD')
    
    # Interactive prompts for missing values
    if not jira_url:
        jira_url = input("JIRA URL (e.g., https://company.atlassian.net): ").strip()
    if not username:
        username = input("JIRA Username: ").strip()
    if not password:
        password = getpass.getpass("JIRA Password: ")
    
    return jira_url, username, password


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='JIRA API Client - Search for issues moved to Done in date range with team/label filters'
    )
    
    parser.add_argument(
        'project_key',
        type=str,
        help='JIRA project prefix (e.g., "PROJ")'
    )
    
    parser.add_argument(
        'delivery_team',
        type=str,
        help='Delivery team name to search for'
    )
    
    parser.add_argument(
        'labels',
        type=str,
        help='Comma-separated list of labels to filter by (e.g., "bug,urgent,frontend")'
    )
    
    parser.add_argument(
        'start_date',
        type=str,
        help='Start date for search (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        'end_date',
        type=str,
        help='End date for search (YYYY-MM-DD)'
    )
    
    # Optional JIRA configuration (will use environment variables if not provided)
    parser.add_argument(
        '--jira-url',
        type=str,
        default=os.getenv('JIRA_URL'),
        help='JIRA base URL (e.g., https://company.atlassian.net) [default: JIRA_URL env var]'
    )
    
    parser.add_argument(
        '--username',
        type=str,
        default=os.getenv('JIRA_USERNAME'),
        help='JIRA username/email [default: JIRA_USERNAME env var]'
    )
    
    parser.add_argument(
        '--password',
        type=str,
        default=os.getenv('JIRA_PASSWORD'),
        help='JIRA password [default: JIRA_PASSWORD env var]'
    )
    
    parser.add_argument(
        '--in-progress-statuses',
        type=str,
        default='In Progress,In Development,In Review,Active',
        help='Comma-separated list of statuses considered "In Progress" [default: In Progress,In Development,In Review,Active]'
    )
    
    parser.add_argument(
        '--done-statuses',
        type=str,
        default='Done,Closed,Resolved,Completed',
        help='Comma-separated list of statuses considered "Done" [default: Done,Closed,Resolved,Completed]'
    )
    
    return parser.parse_args()


def parse_labels(labels_string: str) -> List[str]:
    """Parse comma-separated labels string into a list."""
    if not labels_string.strip():
        return []
    
    # Split by comma and strip whitespace from each label (handles trailing spaces before commas)
    labels = [label.strip() for label in labels_string.split(',')]
    # Filter out empty labels
    return [label for label in labels if label]


def validate_date(date_string: str) -> datetime:
    """Validate and parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: {date_string}. Expected YYYY-MM-DD")


class JiraClient:
    """JIRA API client for updating issues."""
    
    def __init__(self, jira_url: str, username: str, password: str):
        """Initialize JIRA client with basic authentication."""
        self.jira_url = jira_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password)
        
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def get_issue(self, issue_key: str) -> dict:
        """Get JIRA issue details."""
        url = f"{self.jira_url}/rest/api/2/issue/{issue_key}"
        
        response = requests.get(url, auth=self.auth, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def search_issues_moved_to_done(self, project_key: str, start_date: str, end_date: str, 
                                   delivery_team: str = None, labels: List[str] = None) -> List[Dict]:
        """Search for issues that moved to Done status within the date range with optional filters."""
        url = f"{self.jira_url}/rest/api/2/search"
        
        # Base JQL query to find issues moved to Done in date range
        jql_parts = [
            f'project = "{project_key}"',
            f'status CHANGED TO ("Done", "Closed", "Resolved") DURING ("{start_date} 00:00", "{end_date} 23:59")'
        ]
        
        # Add label filters if provided
        if labels:
            for label in labels:
                jql_parts.append(f'labels = "{label}"')
        
        # Add delivery team filter (search in Delivery Team field)
        if delivery_team:
            jql_parts.append(f'"Delivery Team" ~ "{delivery_team}"')
        
        jql = ' AND '.join(jql_parts)
        
        print(f"   JQL Query: {jql}")
        
        params = {
            'jql': jql,
            'maxResults': 1000,  # Adjust as needed
            'fields': 'key,summary,status,labels,assignee,created,updated,description',
            'expand': 'changelog'  # Include status change history
        }
        
        response = requests.get(url, auth=self.auth, headers=self.headers, params=params)
        
        if response.status_code != 200:
            print(f"   Error response: {response.status_code}")
            print(f"   Error details: {response.text}")
        
        response.raise_for_status()
        
        result = response.json()
        return result.get('issues', [])
    
    def test_connection(self):
        """Test basic connection to JIRA."""
        url = f"{self.jira_url}/rest/api/2/myself"
        print(f"   Making request to: {url}")
        print(f"   Auth: {self.auth.username} : {'*' * len(self.auth.password)}")
        
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers, timeout=10)
            print(f"   Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"   Response body: {response.text[:500]}...")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.SSLError as e:
            print(f"   SSL Error: {e}")
            raise
        except requests.exceptions.ConnectionError as e:
            print(f"   Connection Error: {e}")
            raise
        except Exception as e:
            print(f"   Unexpected error: {e}")
            raise
    
    def calculate_cycle_time(self, issue: Dict, in_progress_statuses: List[str], done_statuses: List[str]) -> Dict:
        """Calculate cycle time from In Progress to Done status."""
        changelog = issue.get('changelog', {})
        histories = changelog.get('histories', [])
        
        in_progress_date = None
        done_date = None
        
        # Convert status lists to lowercase for comparison
        in_progress_lower = [status.lower().strip() for status in in_progress_statuses]
        done_lower = [status.lower().strip() for status in done_statuses]
        
        # Look through status changes to find In Progress and Done transitions
        for history in histories:
            created_date = datetime.strptime(history['created'][:19], '%Y-%m-%dT%H:%M:%S')
            
            for item in history.get('items', []):
                if item.get('field') == 'status':
                    to_status = item.get('toString', '').lower().strip()
                    
                    # Find when it moved to In Progress (or similar status)
                    if to_status in in_progress_lower:
                        in_progress_date = created_date
                    
                    # Find when it moved to Done (or similar status)
                    elif to_status in done_lower:
                        done_date = created_date
        
        # Calculate cycle time
        cycle_time_days = None
        if in_progress_date and done_date:
            cycle_time_delta = done_date - in_progress_date
            cycle_time_days = cycle_time_delta.days
        
        return {
            'in_progress_date': in_progress_date,
            'done_date': done_date,
            'cycle_time_days': cycle_time_days
        }


def main():
    """Main function."""
    try:
        # Load environment variables from .env file if it exists
        load_env_file()
        
        # Parse command line arguments
        args = parse_arguments()
        
        # Validate dates
        start_date_obj = validate_date(args.start_date)
        end_date_obj = validate_date(args.end_date)
        
        if start_date_obj > end_date_obj:
            raise ValueError("Start date must be before or equal to end date")
        
        # Parse labels and statuses
        labels_list = parse_labels(args.labels)
        in_progress_statuses = parse_labels(args.in_progress_statuses)
        done_statuses = parse_labels(args.done_statuses)
        
        # Display search criteria
        print(f"Project Key: {args.project_key}")
        print(f"Delivery Team Filter: {args.delivery_team}")
        print(f"Label Filters: {labels_list}")
        print(f"Date Range: {args.start_date} to {args.end_date}")
        print(f"In Progress Statuses: {in_progress_statuses}")
        print(f"Done Statuses: {done_statuses}")
        
        # Get JIRA credentials (from args, env, or prompts)
        jira_url, username, password = get_jira_credentials(args)
        
        if jira_url and username and password:
            print(f"\nConnecting to JIRA: {jira_url}")
            
            # Initialize JIRA client
            jira_client = JiraClient(jira_url, username, password)
            
            # Search for issues moved to Done in the date range with filters
            print(f"\n🔍 Searching for issues moved to Done with filters...")
            
            try:
                # Debug: Show what credentials are being used
                print(f"🔍 Debug info:")
                print(f"   URL: {jira_url}")
                print(f"   Username: {username}")
                print(f"   Password: {'*' * len(password)}" if password else "None")
                
                # Test basic connection first
                print("🔧 Testing connection...")
                user_info = jira_client.test_connection()
                print(f"✅ Connected as: {user_info.get('displayName', 'Unknown')}")
                
                issues = jira_client.search_issues_moved_to_done(
                    args.project_key, 
                    args.start_date, 
                    args.end_date,
                    args.delivery_team,
                    labels_list
                )
                
                if not issues:
                    print(f"✓ No issues found matching the criteria")
                    return
                
                print(f"✓ Found {len(issues)} issue(s) matching criteria:")
                
                total_cycle_time = 0
                valid_cycle_times = []
                
                for issue in issues:
                    issue_key = issue['key']
                    summary = issue['fields']['summary']
                    current_labels = issue['fields'].get('labels', [])
                    
                    # Calculate cycle time
                    cycle_info = jira_client.calculate_cycle_time(issue, in_progress_statuses, done_statuses)
                    
                    print(f"\n  📋 {issue_key}: {summary}")
                    print(f"      Labels: {current_labels}")
                    print(f"      Status: {issue['fields']['status']['name']}")
                    
                    # Display cycle time information
                    if cycle_info['cycle_time_days'] is not None:
                        print(f"      📅 In Progress: {cycle_info['in_progress_date'].strftime('%Y-%m-%d %H:%M')}")
                        print(f"      ✅ Done: {cycle_info['done_date'].strftime('%Y-%m-%d %H:%M')}")
                        print(f"      ⏱️  Cycle Time: {cycle_info['cycle_time_days']} days")
                        
                        valid_cycle_times.append(cycle_info['cycle_time_days'])
                        total_cycle_time += cycle_info['cycle_time_days']
                    else:
                        print(f"      ⚠️  Cycle time: Unable to calculate (missing status transitions)")
                
                # Display summary statistics
                if valid_cycle_times:
                    avg_cycle_time = total_cycle_time / len(valid_cycle_times)
                    min_cycle_time = min(valid_cycle_times)
                    max_cycle_time = max(valid_cycle_times)
                    
                    print(f"\n📊 CYCLE TIME SUMMARY:")
                    print(f"   Issues with cycle time data: {len(valid_cycle_times)}/{len(issues)}")
                    print(f"   Average cycle time: {avg_cycle_time:.1f} days")
                    print(f"   Min cycle time: {min_cycle_time} days")
                    print(f"   Max cycle time: {max_cycle_time} days")
                    print(f"   Total cycle time: {total_cycle_time} days")
                else:
                    print(f"\n⚠️  No cycle time data available for any issues")
                        
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    print("✗ Authentication failed. Check your username and token.")
                elif e.response.status_code == 400:
                    print("✗ Invalid search query. Check your project key and date format.")
                else:
                    print(f"✗ HTTP Error: {e}")
                sys.exit(1)
            except Exception as e:
                print(f"✗ Error searching for issues: {e}")
                sys.exit(1)
        else:
            print("\n💡 To search JIRA, provide:")
            print("   --jira-url https://your-company.atlassian.net")
            print("   --username your_jira_username")
            print("   --password your_password")
            print("\nFor now, just showing search criteria.")
        
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()