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
import csv
import io
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
    
    parser.add_argument(
        '--component-analysis',
        action='store_true',
        help='Show cycle time analysis broken down by component'
    )
    
    parser.add_argument(
        '--output-format',
        type=str,
        choices=['console', 'markdown', 'html', 'confluence', 'csv'],
        default='console',
        help='Output format: console (default), markdown, html, confluence (wiki markup), csv'
    )
    
    parser.add_argument(
        '--label-analysis',
        action='store_true',
        help='Show cycle time analysis broken down by label'
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
            'fields': 'key,summary,status,labels,assignee,created,updated,description,components',
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


def analyze_components(issues: List[Dict], jira_client, in_progress_statuses: List[str], done_statuses: List[str]) -> Dict:
    """Analyze cycle times by component."""
    component_data = {}
    
    for issue in issues:
        issue_key = issue['key']
        summary = issue['fields']['summary']
        components = issue['fields'].get('components', [])
        
        # Calculate cycle time for this issue
        cycle_info = jira_client.calculate_cycle_time(issue, in_progress_statuses, done_statuses)
        cycle_time = cycle_info['cycle_time_days']
        
        # If no cycle time data, skip this issue
        if cycle_time is None:
            continue
            
        # Extract component names
        component_names = [comp['name'] for comp in components] if components else ['No components']
        
        # Add this issue to each component it belongs to
        for component_name in component_names:
            if component_name not in component_data:
                component_data[component_name] = []
            
            component_data[component_name].append({
                'key': issue_key,
                'summary': summary,
                'cycle_time': cycle_time,
                'cycle_info': cycle_info
            })
    
    return component_data


def display_component_analysis(component_data: Dict):
    """Display component analysis with rankings."""
    if not component_data:
        print("\n🔧 COMPONENT ANALYSIS:")
        print("   No issues with cycle time data found.")
        return
    
    # Calculate statistics for each component
    component_stats = {}
    for component, tickets in component_data.items():
        if tickets:
            cycle_times = [ticket['cycle_time'] for ticket in tickets]
            component_stats[component] = {
                'count': len(tickets),
                'total': sum(cycle_times),
                'average': sum(cycle_times) / len(cycle_times),
                'min': min(cycle_times),
                'max': max(cycle_times),
                'tickets': tickets
            }
    
    # Display ranked summary first
    print("\n🏆 COMPONENT RANKING (by average cycle time):")
    sorted_components = sorted(component_stats.items(), key=lambda x: x[1]['average'], reverse=True)
    
    for i, (component, stats) in enumerate(sorted_components, 1):
        print(f"   {i}. {component}: {stats['average']:.1f} days avg ({stats['count']} tickets)")
    
    # Display detailed analysis
    print("\n🔧 COMPONENT ANALYSIS:")
    
    for component, stats in sorted_components:
        print(f"\n📦 {component} ({stats['count']} tickets):")
        
        # List individual tickets
        for ticket in stats['tickets']:
            cycle_info = ticket['cycle_info']
            if cycle_info['in_progress_date'] and cycle_info['done_date']:
                in_progress_str = cycle_info['in_progress_date'].strftime('%Y-%m-%d %H:%M')
                done_str = cycle_info['done_date'].strftime('%Y-%m-%d %H:%M')
                print(f"     📋 {ticket['key']}: {ticket['summary']}")
                print(f"         📅 In Progress: {in_progress_str}")
                print(f"         ✅ Done: {done_str}")
                print(f"         ⏱️  Cycle Time: {ticket['cycle_time']} days")
            else:
                print(f"     📋 {ticket['key']}: {ticket['summary']} - {ticket['cycle_time']} days")
        
        # Component statistics
        print(f"     📊 Summary: Avg: {stats['average']:.1f}d, Min: {stats['min']}d, Max: {stats['max']}d, Total: {stats['total']}d")


def format_markdown_summary(valid_cycle_times: List[int], total_cycle_time: int, issues_count: int) -> str:
    """Format overall cycle time summary in markdown."""
    if not valid_cycle_times:
        return "\n## 📊 CYCLE TIME SUMMARY\n\n⚠️ No cycle time data available for any issues\n"
    
    avg_cycle_time = total_cycle_time / len(valid_cycle_times)
    min_cycle_time = min(valid_cycle_times)
    max_cycle_time = max(valid_cycle_times)
    
    markdown = "\n## 📊 CYCLE TIME SUMMARY\n\n"
    markdown += f"- **Issues with cycle time data:** {len(valid_cycle_times)}/{issues_count}\n"
    markdown += f"- **Average cycle time:** {avg_cycle_time:.1f} days\n"
    markdown += f"- **Min cycle time:** {min_cycle_time} days\n"
    markdown += f"- **Max cycle time:** {max_cycle_time} days\n"
    markdown += f"- **Total cycle time:** {total_cycle_time} days\n"
    
    return markdown


def format_markdown_issues(issues: List[Dict], jira_client, in_progress_statuses: List[str], done_statuses: List[str]) -> str:
    """Format individual issues in markdown."""
    markdown = f"\n## 📋 ISSUES FOUND ({len(issues)} total)\n\n"
    
    for issue in issues:
        issue_key = issue['key']
        summary = issue['fields']['summary']
        current_labels = issue['fields'].get('labels', [])
        
        cycle_info = jira_client.calculate_cycle_time(issue, in_progress_statuses, done_statuses)
        
        markdown += f"### {issue_key}: {summary}\n\n"
        markdown += f"- **Labels:** {current_labels}\n"
        markdown += f"- **Status:** {issue['fields']['status']['name']}\n"
        
        if cycle_info['cycle_time_days'] is not None:
            in_progress_str = cycle_info['in_progress_date'].strftime('%Y-%m-%d %H:%M')
            done_str = cycle_info['done_date'].strftime('%Y-%m-%d %H:%M')
            markdown += f"- **In Progress:** {in_progress_str}\n"
            markdown += f"- **Done:** {done_str}\n"
            markdown += f"- **Cycle Time:** {cycle_info['cycle_time_days']} days\n"
        else:
            markdown += f"- **Cycle time:** Unable to calculate (missing status transitions)\n"
        
        markdown += "\n"
    
    return markdown


def format_markdown_component_analysis(component_data: Dict) -> str:
    """Format component analysis in markdown."""
    if not component_data:
        return "\n## 🔧 COMPONENT ANALYSIS\n\nNo issues with cycle time data found.\n"
    
    # Calculate statistics for each component
    component_stats = {}
    for component, tickets in component_data.items():
        if tickets:
            cycle_times = [ticket['cycle_time'] for ticket in tickets]
            component_stats[component] = {
                'count': len(tickets),
                'total': sum(cycle_times),
                'average': sum(cycle_times) / len(cycle_times),
                'min': min(cycle_times),
                'max': max(cycle_times),
                'tickets': tickets
            }
    
    markdown = "\n## 🏆 COMPONENT RANKING (by average cycle time)\n\n"
    sorted_components = sorted(component_stats.items(), key=lambda x: x[1]['average'], reverse=True)
    
    # Ranking table
    markdown += "| Rank | Component | Avg Days | Tickets |\n"
    markdown += "|------|-----------|----------|----------|\n"
    
    for i, (component, stats) in enumerate(sorted_components, 1):
        markdown += f"| {i} | {component} | {stats['average']:.1f} | {stats['count']} |\n"
    
    # Detailed analysis
    markdown += "\n## 🔧 COMPONENT ANALYSIS\n\n"
    
    for component, stats in sorted_components:
        markdown += f"### 📦 {component} ({stats['count']} tickets)\n\n"
        
        # Component summary
        markdown += f"**Summary:** Avg: {stats['average']:.1f}d, Min: {stats['min']}d, Max: {stats['max']}d, Total: {stats['total']}d\n\n"
        
        # Tickets table
        markdown += "| Ticket | Summary | In Progress | Done | Cycle Time |\n"
        markdown += "|--------|---------|-------------|------|------------|\n"
        
        for ticket in stats['tickets']:
            cycle_info = ticket['cycle_info']
            if cycle_info['in_progress_date'] and cycle_info['done_date']:
                in_progress_str = cycle_info['in_progress_date'].strftime('%Y-%m-%d')
                done_str = cycle_info['done_date'].strftime('%Y-%m-%d')
                markdown += f"| {ticket['key']} | {ticket['summary']} | {in_progress_str} | {done_str} | {ticket['cycle_time']} days |\n"
            else:
                markdown += f"| {ticket['key']} | {ticket['summary']} | - | - | {ticket['cycle_time']} days |\n"
        
        markdown += "\n"
    
    return markdown


def analyze_labels(issues: List[Dict], jira_client, in_progress_statuses: List[str], done_statuses: List[str]) -> Dict:
    """Analyze cycle times by label."""
    label_data = {}
    
    for issue in issues:
        issue_key = issue['key']
        summary = issue['fields']['summary']
        labels = issue['fields'].get('labels', [])
        
        # Calculate cycle time for this issue
        cycle_info = jira_client.calculate_cycle_time(issue, in_progress_statuses, done_statuses)
        cycle_time = cycle_info['cycle_time_days']
        
        # If no cycle time data, skip this issue
        if cycle_time is None:
            continue
            
        # Extract label names
        label_names = labels if labels else ['No labels']
        
        # Add this issue to each label it has
        for label_name in label_names:
            if label_name not in label_data:
                label_data[label_name] = []
            
            label_data[label_name].append({
                'key': issue_key,
                'summary': summary,
                'cycle_time': cycle_time,
                'cycle_info': cycle_info
            })
    
    return label_data


def display_label_analysis(label_data: Dict):
    """Display label analysis with rankings."""
    if not label_data:
        print("\n🏷️ LABEL ANALYSIS:")
        print("   No issues with cycle time data found.")
        return
    
    # Calculate statistics for each label
    label_stats = {}
    for label, tickets in label_data.items():
        if tickets:
            cycle_times = [ticket['cycle_time'] for ticket in tickets]
            label_stats[label] = {
                'count': len(tickets),
                'total': sum(cycle_times),
                'average': sum(cycle_times) / len(cycle_times),
                'min': min(cycle_times),
                'max': max(cycle_times),
                'tickets': tickets
            }
    
    # Display ranked summary first
    print("\n🏆 LABEL RANKING (by average cycle time):")
    sorted_labels = sorted(label_stats.items(), key=lambda x: x[1]['average'], reverse=True)
    
    for i, (label, stats) in enumerate(sorted_labels, 1):
        print(f"   {i}. {label}: {stats['average']:.1f} days avg ({stats['count']} tickets)")
    
    # Display detailed analysis
    print("\n🏷️ LABEL ANALYSIS:")
    
    for label, stats in sorted_labels:
        print(f"\n🏷️ {label} ({stats['count']} tickets):")
        
        # List individual tickets
        for ticket in stats['tickets']:
            cycle_info = ticket['cycle_info']
            if cycle_info['in_progress_date'] and cycle_info['done_date']:
                in_progress_str = cycle_info['in_progress_date'].strftime('%Y-%m-%d %H:%M')
                done_str = cycle_info['done_date'].strftime('%Y-%m-%d %H:%M')
                print(f"     📋 {ticket['key']}: {ticket['summary']}")
                print(f"         📅 In Progress: {in_progress_str}")
                print(f"         ✅ Done: {done_str}")
                print(f"         ⏱️  Cycle Time: {ticket['cycle_time']} days")
            else:
                print(f"     📋 {ticket['key']}: {ticket['summary']} - {ticket['cycle_time']} days")
        
        # Label statistics
        print(f"     📊 Summary: Avg: {stats['average']:.1f}d, Min: {stats['min']}d, Max: {stats['max']}d, Total: {stats['total']}d")


def format_markdown_label_analysis(label_data: Dict) -> str:
    """Format label analysis in markdown."""
    if not label_data:
        return "\n## 🏷️ LABEL ANALYSIS\n\nNo issues with cycle time data found.\n"
    
    # Calculate statistics for each label
    label_stats = {}
    for label, tickets in label_data.items():
        if tickets:
            cycle_times = [ticket['cycle_time'] for ticket in tickets]
            label_stats[label] = {
                'count': len(tickets),
                'total': sum(cycle_times),
                'average': sum(cycle_times) / len(cycle_times),
                'min': min(cycle_times),
                'max': max(cycle_times),
                'tickets': tickets
            }
    
    markdown = "\n## 🏆 LABEL RANKING (by average cycle time)\n\n"
    sorted_labels = sorted(label_stats.items(), key=lambda x: x[1]['average'], reverse=True)
    
    # Ranking table
    markdown += "| Rank | Label | Avg Days | Tickets |\n"
    markdown += "|------|-------|----------|----------|\n"
    
    for i, (label, stats) in enumerate(sorted_labels, 1):
        markdown += f"| {i} | {label} | {stats['average']:.1f} | {stats['count']} |\n"
    
    # Detailed analysis
    markdown += "\n## 🏷️ LABEL ANALYSIS\n\n"
    
    for label, stats in sorted_labels:
        markdown += f"### 🏷️ {label} ({stats['count']} tickets)\n\n"
        
        # Label summary
        markdown += f"**Summary:** Avg: {stats['average']:.1f}d, Min: {stats['min']}d, Max: {stats['max']}d, Total: {stats['total']}d\n\n"
        
        # Tickets table
        markdown += "| Ticket | Summary | In Progress | Done | Cycle Time |\n"
        markdown += "|--------|---------|-------------|------|------------|\n"
        
        for ticket in stats['tickets']:
            cycle_info = ticket['cycle_info']
            if cycle_info['in_progress_date'] and cycle_info['done_date']:
                in_progress_str = cycle_info['in_progress_date'].strftime('%Y-%m-%d')
                done_str = cycle_info['done_date'].strftime('%Y-%m-%d')
                markdown += f"| {ticket['key']} | {ticket['summary']} | {in_progress_str} | {done_str} | {ticket['cycle_time']} days |\n"
            else:
                markdown += f"| {ticket['key']} | {ticket['summary']} | - | - | {ticket['cycle_time']} days |\n"
        
        markdown += "\n"
    
    return markdown


def format_html_summary(valid_cycle_times: List[int], total_cycle_time: int, issues_count: int) -> str:
    """Format overall cycle time summary in HTML."""
    if not valid_cycle_times:
        return "\n<h2>📊 Cycle Time Summary</h2>\n<p><strong>⚠️ No cycle time data available for any issues</strong></p>\n"
    
    avg_cycle_time = total_cycle_time / len(valid_cycle_times)
    min_cycle_time = min(valid_cycle_times)
    max_cycle_time = max(valid_cycle_times)
    
    html = "\n<h2>📊 Cycle Time Summary</h2>\n<ul>\n"
    html += f"<li><strong>Issues with cycle time data:</strong> {len(valid_cycle_times)}/{issues_count}</li>\n"
    html += f"<li><strong>Average cycle time:</strong> {avg_cycle_time:.1f} days</li>\n"
    html += f"<li><strong>Min cycle time:</strong> {min_cycle_time} days</li>\n"
    html += f"<li><strong>Max cycle time:</strong> {max_cycle_time} days</li>\n"
    html += f"<li><strong>Total cycle time:</strong> {total_cycle_time} days</li>\n"
    html += "</ul>\n"
    
    return html


def format_html_issues(issues: List[Dict], jira_client, in_progress_statuses: List[str], done_statuses: List[str]) -> str:
    """Format individual issues in HTML."""
    html = f"\n<h2>📋 Issues Found ({len(issues)} total)</h2>\n"
    
    for issue in issues:
        issue_key = issue['key']
        summary = issue['fields']['summary']
        current_labels = issue['fields'].get('labels', [])
        
        cycle_info = jira_client.calculate_cycle_time(issue, in_progress_statuses, done_statuses)
        
        html += f"<h3>{issue_key}: {summary}</h3>\n<ul>\n"
        html += f"<li><strong>Labels:</strong> {', '.join(current_labels) if current_labels else 'None'}</li>\n"
        html += f"<li><strong>Status:</strong> {issue['fields']['status']['name']}</li>\n"
        
        if cycle_info['cycle_time_days'] is not None:
            in_progress_str = cycle_info['in_progress_date'].strftime('%Y-%m-%d %H:%M')
            done_str = cycle_info['done_date'].strftime('%Y-%m-%d %H:%M')
            html += f"<li><strong>In Progress:</strong> {in_progress_str}</li>\n"
            html += f"<li><strong>Done:</strong> {done_str}</li>\n"
            html += f"<li><strong>Cycle Time:</strong> {cycle_info['cycle_time_days']} days</li>\n"
        else:
            html += f"<li><strong>Cycle time:</strong> Unable to calculate (missing status transitions)</li>\n"
        
        html += "</ul>\n"
    
    return html


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
                    if args.output_format == 'markdown':
                        print("# JIRA Cycle Time Analysis\n\nNo issues found matching the criteria.")
                    elif args.output_format == 'html':
                        print("<!DOCTYPE html><html><head><title>JIRA Analysis</title></head><body>")
                        print("<h1>JIRA Cycle Time Analysis</h1><p>No issues found matching the criteria.</p></body></html>")
                    elif args.output_format == 'confluence':
                        print("h1. JIRA Cycle Time Analysis\n\nNo issues found matching the criteria.")
                    elif args.output_format == 'csv':
                        print("Issue Key,Summary,Status,Labels,In Progress Date,Done Date,Cycle Time (Days)")
                    else:
                        print(f"✓ No issues found matching the criteria")
                    return
                
                # Calculate cycle times for all issues
                total_cycle_time = 0
                valid_cycle_times = []
                
                for issue in issues:
                    cycle_info = jira_client.calculate_cycle_time(issue, in_progress_statuses, done_statuses)
                    if cycle_info['cycle_time_days'] is not None:
                        valid_cycle_times.append(cycle_info['cycle_time_days'])
                        total_cycle_time += cycle_info['cycle_time_days']
                
                # Generate output based on format
                if args.output_format == 'markdown':
                    # Markdown output with search criteria header
                    print("# JIRA Cycle Time Analysis")
                    print(f"\n## Search Criteria")
                    print(f"- **Project:** {args.project_key}")
                    print(f"- **Delivery Team:** {args.delivery_team}")
                    print(f"- **Labels:** {', '.join(labels_list)}")
                    print(f"- **Date Range:** {args.start_date} to {args.end_date}")
                    print(f"\n**Found {len(issues)} issue(s) matching criteria**")
                    
                    # Overall summary first
                    print(format_markdown_summary(valid_cycle_times, total_cycle_time, len(issues)))
                    
                    # Component analysis if requested
                    if args.component_analysis:
                        component_data = analyze_components(issues, jira_client, in_progress_statuses, done_statuses)
                        print(format_markdown_component_analysis(component_data))
                    
                    # Label analysis if requested
                    if args.label_analysis:
                        label_data = analyze_labels(issues, jira_client, in_progress_statuses, done_statuses)
                        print(format_markdown_label_analysis(label_data))
                    
                    # Issues details last
                    print(format_markdown_issues(issues, jira_client, in_progress_statuses, done_statuses))
                
                elif args.output_format == 'html':
                    # HTML output
                    print("<!DOCTYPE html>")
                    print("<html><head><title>JIRA Cycle Time Analysis</title></head><body>")
                    print("<h1>JIRA Cycle Time Analysis</h1>")
                    print(f"\n<h2>Search Criteria</h2>")
                    print(f"<ul>")
                    print(f"<li><strong>Project:</strong> {args.project_key}</li>")
                    print(f"<li><strong>Delivery Team:</strong> {args.delivery_team}</li>")
                    print(f"<li><strong>Labels:</strong> {', '.join(labels_list)}</li>")
                    print(f"<li><strong>Date Range:</strong> {args.start_date} to {args.end_date}</li>")
                    print(f"</ul>")
                    print(f"\n<p><strong>Found {len(issues)} issue(s) matching criteria</strong></p>")
                    
                    # Overall summary first
                    print(format_html_summary(valid_cycle_times, total_cycle_time, len(issues)))
                    
                    # Issues details
                    print(format_html_issues(issues, jira_client, in_progress_statuses, done_statuses))
                    
                    print("</body></html>")
                
                elif args.output_format == 'csv':
                    # CSV output
                    output = io.StringIO()
                    writer = csv.writer(output)
                    
                    # Write header
                    writer.writerow([
                        'Issue Key', 'Summary', 'Status', 'Labels', 
                        'In Progress Date', 'Done Date', 'Cycle Time (Days)'
                    ])
                    
                    # Write data rows
                    for issue in issues:
                        issue_key = issue['key']
                        summary = issue['fields']['summary']
                        status = issue['fields']['status']['name']
                        labels = ', '.join(issue['fields'].get('labels', []))
                        
                        cycle_info = jira_client.calculate_cycle_time(issue, in_progress_statuses, done_statuses)
                        
                        in_progress_date = cycle_info['in_progress_date'].strftime('%Y-%m-%d %H:%M') if cycle_info['in_progress_date'] else ''
                        done_date = cycle_info['done_date'].strftime('%Y-%m-%d %H:%M') if cycle_info['done_date'] else ''
                        cycle_time = cycle_info['cycle_time_days'] if cycle_info['cycle_time_days'] is not None else ''
                        
                        writer.writerow([issue_key, summary, status, labels, in_progress_date, done_date, cycle_time])
                    
                    print(output.getvalue())
                
                elif args.output_format == 'confluence':
                    # Confluence Wiki Markup output
                    print("h1. JIRA Cycle Time Analysis")
                    print(f"\nh2. Search Criteria")
                    print(f"* *Project:* {args.project_key}")
                    print(f"* *Delivery Team:* {args.delivery_team}")
                    print(f"* *Labels:* {', '.join(labels_list)}")
                    print(f"* *Date Range:* {args.start_date} to {args.end_date}")
                    print(f"\n*Found {len(issues)} issue(s) matching criteria*")
                    
                    # Overall summary
                    if valid_cycle_times:
                        avg_cycle_time = total_cycle_time / len(valid_cycle_times)
                        min_cycle_time = min(valid_cycle_times)
                        max_cycle_time = max(valid_cycle_times)
                        
                        print(f"\nh2. Cycle Time Summary")
                        print(f"* *Issues with cycle time data:* {len(valid_cycle_times)}/{len(issues)}")
                        print(f"* *Average cycle time:* {avg_cycle_time:.1f} days")
                        print(f"* *Min cycle time:* {min_cycle_time} days")
                        print(f"* *Max cycle time:* {max_cycle_time} days")
                        print(f"* *Total cycle time:* {total_cycle_time} days")
                    else:
                        print(f"\nh2. Cycle Time Summary")
                        print(f"*No cycle time data available for any issues*")
                    
                    # Issues details
                    print(f"\nh2. Issues Found ({len(issues)} total)")
                    
                    for issue in issues:
                        issue_key = issue['key']
                        summary = issue['fields']['summary']
                        current_labels = issue['fields'].get('labels', [])
                        
                        cycle_info = jira_client.calculate_cycle_time(issue, in_progress_statuses, done_statuses)
                        
                        print(f"\nh3. {issue_key}: {summary}")
                        print(f"* *Labels:* {', '.join(current_labels) if current_labels else 'None'}")
                        print(f"* *Status:* {issue['fields']['status']['name']}")
                        
                        if cycle_info['cycle_time_days'] is not None:
                            in_progress_str = cycle_info['in_progress_date'].strftime('%Y-%m-%d %H:%M')
                            done_str = cycle_info['done_date'].strftime('%Y-%m-%d %H:%M')
                            print(f"* *In Progress:* {in_progress_str}")
                            print(f"* *Done:* {done_str}")
                            print(f"* *Cycle Time:* {cycle_info['cycle_time_days']} days")
                        else:
                            print(f"* *Cycle time:* Unable to calculate (missing status transitions)")
                        
                else:
                    # Regular console output
                    print(f"✓ Found {len(issues)} issue(s) matching criteria:")
                    
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
                    
                    # Component analysis if requested
                    if args.component_analysis:
                        component_data = analyze_components(issues, jira_client, in_progress_statuses, done_statuses)
                        display_component_analysis(component_data)
                    
                    # Label analysis if requested
                    if args.label_analysis:
                        label_data = analyze_labels(issues, jira_client, in_progress_statuses, done_statuses)
                        display_label_analysis(label_data)
                        
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