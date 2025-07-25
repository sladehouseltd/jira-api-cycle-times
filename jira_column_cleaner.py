#!/usr/bin/env python3
"""
JIRA Column Cleaner Script

This script removes unwanted statuses from a board column, keeping only specified statuses.
Useful for cleaning up columns that have accumulated too many statuses over time.

Parameters:
- board_id: JIRA board ID (can be found in board URL)
- column_name: Name of the column to clean (e.g., "In Progress", "Development")
- keep_statuses: Comma-separated list of statuses to keep (e.g., "In Progress")
"""

import argparse
import sys
import json
import os
import getpass
from datetime import datetime
from typing import List, Dict, Optional

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
        description='JIRA Column Cleaner - Remove unwanted statuses from board columns'
    )
    
    parser.add_argument(
        'board_id',
        type=str,
        nargs='?',
        help='JIRA board ID (found in board URL, e.g., "123")'
    )
    
    parser.add_argument(
        'column_name',
        type=str,
        nargs='?',
        help='Name of the column to clean (e.g., "In Progress", "Development")'
    )
    
    parser.add_argument(
        'keep_statuses',
        type=str,
        nargs='?',
        help='Comma-separated list of statuses to keep in the column (e.g., "In Progress")'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making actual changes'
    )
    
    parser.add_argument(
        '--list-boards',
        action='store_true',
        help='List all boards to help find board ID'
    )
    
    parser.add_argument(
        '--show-config',
        action='store_true',
        help='Show current board configuration and exit'
    )
    
    parser.add_argument(
        '--find-status',
        type=str,
        help='Find status ID by name (e.g., "In Progress")'
    )
    
    parser.add_argument(
        '--list-column-statuses',
        type=str,
        help='List status names in the specified column (e.g., "In Progress")'
    )
    
    parser.add_argument(
        '--remove-count',
        type=int,
        help='Remove only the first N statuses (for testing, use with --dry-run first)'
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
    
    return parser.parse_args()


def parse_statuses(statuses_string: str) -> List[str]:
    """Parse comma-separated statuses string into a list."""
    if not statuses_string.strip():
        return []
    
    # Split by comma and strip whitespace from each status
    statuses = [status.strip() for status in statuses_string.split(',')]
    # Filter out empty statuses
    return [status for status in statuses if status]


class JiraClient:
    """JIRA API client for board configuration management."""
    
    def __init__(self, jira_url: str, username: str, password: str):
        """Initialize JIRA client with basic authentication."""
        self.jira_url = jira_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password)
        
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def test_connection(self):
        """Test basic connection to JIRA."""
        url = f"{self.jira_url}/rest/api/2/myself"
        print(f"🔧 Testing connection to: {self.jira_url}")
        
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.SSLError as e:
            print(f"❌ SSL Error: {e}")
            raise
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection Error: {e}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            raise
    
    def list_boards(self) -> List[Dict]:
        """List all boards accessible to the user."""
        all_boards = []
        start_at = 0
        max_results = 50
        
        while True:
            url = f"{self.jira_url}/rest/agile/1.0/board"
            params = {
                'startAt': start_at,
                'maxResults': max_results
            }
            
            response = requests.get(url, auth=self.auth, headers=self.headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            boards = result.get('values', [])
            all_boards.extend(boards)
            
            # Check if we've got all boards
            total = result.get('total', 0)
            if start_at + len(boards) >= total:
                break
                
            start_at += max_results
        
        return all_boards
    
    def get_board_configuration(self, board_id: str) -> Dict:
        """Get board configuration including columns and statuses."""
        url = f"{self.jira_url}/rest/agile/1.0/board/{board_id}/configuration"
        
        response = requests.get(url, auth=self.auth, headers=self.headers)
        
        if response.status_code == 404:
            raise Exception(f"Board {board_id} not found or not accessible")
        elif response.status_code == 403:
            raise Exception(f"No permission to access board {board_id} configuration")
        
        response.raise_for_status()
        return response.json()
    
    def get_status_info(self, status_id: str) -> Dict:
        """Get status information by ID."""
        url = f"{self.jira_url}/rest/api/2/status/{status_id}"
        
        response = requests.get(url, auth=self.auth, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            return {'id': status_id, 'name': f'Status_{status_id}', 'description': 'Unknown status'}
    
    def get_multiple_status_info(self, status_ids: List[str]) -> Dict:
        """Get status information for multiple IDs (with caching for performance)."""
        status_info = {}
        
        print(f"🔍 Fetching status names for {len(status_ids)} statuses...")
        
        # Batch requests to avoid too many individual calls
        for i, status_id in enumerate(status_ids):
            if i % 50 == 0:  # Progress indicator
                print(f"   Progress: {i+1}/{len(status_ids)}")
            
            status_info[status_id] = self.get_status_info(status_id)
        
        return status_info
    
    def search_statuses_by_name(self, search_name: str) -> List[Dict]:
        """Search for statuses by name."""
        url = f"{self.jira_url}/rest/api/2/status"
        
        response = requests.get(url, auth=self.auth, headers=self.headers)
        response.raise_for_status()
        
        all_statuses = response.json()
        
        # Find statuses that match the search term (case-insensitive)
        search_lower = search_name.lower()
        matching_statuses = []
        
        for status in all_statuses:
            status_name = status.get('name', '').lower()
            if search_lower in status_name:
                matching_statuses.append(status)
        
        return matching_statuses
    
    def update_board_configuration(self, board_id: str, config: Dict) -> bool:
        """Update board configuration."""
        url = f"{self.jira_url}/rest/agile/1.0/board/{board_id}/configuration"
        
        response = requests.put(url, auth=self.auth, headers=self.headers, json=config)
        
        if response.status_code == 200:
            print(f"✅ Board configuration updated successfully")
            return True
        else:
            print(f"❌ Failed to update board configuration - {response.status_code}: {response.text}")
            return False


def display_board_configuration(config: Dict, jira_client=None):
    """Display current board configuration in a readable format."""
    print(f"\n📋 Board Configuration:")
    print(f"   Name: {config.get('name', 'Unknown')}")
    print(f"   Type: {config.get('type', 'Unknown')}")
    
    columns = config.get('columnConfig', {}).get('columns', [])
    print(f"\n📊 Columns ({len(columns)}):")
    
    for i, column in enumerate(columns, 1):
        column_name = column.get('name', f'Column {i}')
        statuses = column.get('statuses', [])
        
        print(f"   {i}. 📁 {column_name}")
        print(f"      Statuses ({len(statuses)}):")
        
        if statuses and len(statuses) > 0:
            # Get status IDs
            status_ids = [status.get('id') for status in statuses if status.get('id')]
            
            if jira_client and len(status_ids) <= 20:  # Only fetch names for reasonable numbers
                try:
                    status_info = jira_client.get_multiple_status_info(status_ids)
                    status_names = [status_info.get(sid, {}).get('name', f'ID_{sid}') for sid in status_ids]
                    print(f"      Status names: {', '.join(status_names)}")
                except Exception as e:
                    print(f"      Status IDs: {', '.join(status_ids[:10])}{'...' if len(status_ids) > 10 else ''}")
                    print(f"      (Could not fetch names: {e})")
            else:
                print(f"      Status IDs: {', '.join(status_ids[:10])}{'...' if len(status_ids) > 10 else ''}")
                if len(status_ids) > 20:
                    print(f"      (Too many statuses to fetch names - {len(status_ids)} total)")
        else:
            print(f"      No statuses found")


def find_column_by_name(config: Dict, column_name: str) -> Optional[Dict]:
    """Find a column by name in the board configuration."""
    columns = config.get('columnConfig', {}).get('columns', [])
    
    for column in columns:
        if column.get('name', '').lower() == column_name.lower():
            return column
    
    return None


def clean_column_statuses(column: Dict, keep_identifiers: List[str], jira_client=None, remove_count: int = None) -> Dict:
    """Remove unwanted statuses from a column, keeping only specified ones (by ID or name)."""
    current_statuses = column.get('statuses', [])
    
    # If remove_count is specified, just remove the first N statuses
    if remove_count is not None:
        if remove_count >= len(current_statuses):
            raise Exception(f"Cannot remove {remove_count} statuses - column only has {len(current_statuses)} statuses")
        
        cleaned_statuses = current_statuses[remove_count:]
        removed_statuses = current_statuses[:remove_count]
        
        # Get info for removed statuses
        removed_status_info = []
        for status in removed_statuses:
            status_id = status.get('id')
            if jira_client:
                try:
                    status_info = jira_client.get_status_info(status_id)
                    removed_status_info.append(f"{status_info.get('name', f'ID_{status_id}')} (ID: {status_id})")
                except:
                    removed_status_info.append(f"ID_{status_id}")
            else:
                removed_status_info.append(f"ID_{status_id}")
        
        # Update the column
        new_column = column.copy()
        new_column['statuses'] = cleaned_statuses
        
        return new_column, removed_status_info
    
    # Original logic for keeping specific statuses
    # Convert keep_identifiers to both IDs and names for comparison
    keep_ids = []
    keep_names_lower = []
    
    for identifier in keep_identifiers:
        if identifier.isdigit():
            # It's a status ID
            keep_ids.append(identifier)
        else:
            # It's a status name
            keep_names_lower.append(identifier.lower())
    
    # If we have names but no jira_client, we can't resolve them
    if keep_names_lower and not jira_client:
        raise Exception("Cannot resolve status names without jira_client. Use status IDs instead.")
    
    # Filter statuses to keep only the ones we want
    cleaned_statuses = []
    removed_status_info = []
    
    for status in current_statuses:
        status_id = status.get('id')
        should_keep = False
        
        # Check if we should keep this status by ID
        if status_id in keep_ids:
            should_keep = True
        
        # Check if we should keep this status by name (if we have names to check)
        elif keep_names_lower and jira_client:
            try:
                status_info = jira_client.get_status_info(status_id)
                status_name = status_info.get('name', '').lower()
                if status_name in keep_names_lower:
                    should_keep = True
            except:
                pass  # If we can't get status info, skip name matching
        
        if should_keep:
            cleaned_statuses.append(status)
        else:
            # Try to get name for removed status (for reporting)
            if jira_client:
                try:
                    status_info = jira_client.get_status_info(status_id)
                    removed_status_info.append(f"{status_info.get('name', f'ID_{status_id}')} (ID: {status_id})")
                except:
                    removed_status_info.append(f"ID_{status_id}")
            else:
                removed_status_info.append(f"ID_{status_id}")
    
    # Update the column
    new_column = column.copy()
    new_column['statuses'] = cleaned_statuses
    
    return new_column, removed_status_info


def main():
    """Main function."""
    try:
        # Load environment variables from .env file if it exists
        load_env_file()
        
        # Parse command line arguments
        args = parse_arguments()
        
        # Get JIRA credentials
        jira_url, username, password = get_jira_credentials(args)
        
        if not (jira_url and username and password):
            print("❌ Error: Missing JIRA credentials")
            sys.exit(1)
        
        # Initialize JIRA client
        jira_client = JiraClient(jira_url, username, password)
        
        # Test connection
        user_info = jira_client.test_connection()
        print(f"✅ Connected as: {user_info.get('displayName', 'Unknown')}")
        
        # Handle find status option
        if args.find_status:
            print(f"\n🔍 Searching for statuses containing '{args.find_status}'...")
            matching_statuses = jira_client.search_statuses_by_name(args.find_status)
            
            if matching_statuses:
                print(f"\n📋 Found {len(matching_statuses)} matching status(es):")
                for status in matching_statuses:
                    status_id = status.get('id')
                    status_name = status.get('name')
                    description = status.get('description', 'No description')
                    print(f"   🏷️  ID: {status_id} | Name: '{status_name}' | Description: {description}")
                
                print(f"\n💡 To clean a column keeping only one status, use:")
                print(f"   python3 {sys.argv[0]} BOARD_ID COLUMN_NAME STATUS_ID")
                print(f"   Example: python3 {sys.argv[0]} 123 \"In Progress\" \"{matching_statuses[0].get('id')}\"")
            else:
                print(f"❌ No statuses found containing '{args.find_status}'")
            return
        
        # Handle list column statuses option
        if args.list_column_statuses:
            if not args.board_id:
                print("❌ Error: board_id is required for --list-column-statuses")
                print(f"Use: python3 {sys.argv[0]} BOARD_ID --list-column-statuses \"COLUMN_NAME\"")
                sys.exit(1)
            
            print(f"\n🔍 Getting configuration for board {args.board_id}...")
            config = jira_client.get_board_configuration(args.board_id)
            
            # Find the target column
            target_column = find_column_by_name(config, args.list_column_statuses)
            
            if not target_column:
                print(f"❌ Error: Column '{args.list_column_statuses}' not found")
                print("\nAvailable columns:")
                columns = config.get('columnConfig', {}).get('columns', [])
                for column in columns:
                    print(f"   📁 {column.get('name', 'Unknown')}")
                sys.exit(1)
            
            # Get current statuses in the column
            current_statuses = target_column.get('statuses', [])
            
            if not current_statuses:
                print(f"\n📁 Column '{args.list_column_statuses}' has no statuses")
                return
            
            print(f"\n📁 Statuses in '{args.list_column_statuses}' column ({len(current_statuses)} total):")
            
            # Get status IDs
            status_ids = [status.get('id') for status in current_statuses if status.get('id')]
            
            try:
                status_info = jira_client.get_multiple_status_info(status_ids)
                for status in current_statuses:
                    status_id = status.get('id')
                    status_name = status_info.get(status_id, {}).get('name', f'ID_{status_id}')
                    print(f"   📌 {status_name} (ID: {status_id})")
            except Exception as e:
                print(f"   Could not fetch status names: {e}")
                for status in current_statuses:
                    status_id = status.get('id')
                    print(f"   📌 ID: {status_id}")
            
            return
        
        # Handle list boards option
        if args.list_boards:
            print(f"\n🔍 Fetching all boards...")
            boards = jira_client.list_boards()
            
            print(f"\n📋 Available Boards ({len(boards)} total):")
            for board in boards:
                board_id = board.get('id')
                board_name = board.get('name')
                board_type = board.get('type')
                print(f"   🏈 {board_id}: {board_name} ({board_type})")
            
            print(f"\nUse the board ID in the command: python3 {sys.argv[0]} <BOARD_ID> <COLUMN_NAME> <KEEP_STATUSES>")
            return
        
        # Check required arguments for non-info commands
        if not args.board_id:
            print("❌ Error: board_id is required")
            print(f"Use --list-boards to find your board ID")
            sys.exit(1)
        
        # Get board configuration
        print(f"\n🔍 Getting configuration for board {args.board_id}...")
        config = jira_client.get_board_configuration(args.board_id)
        
        # Handle show config option
        if args.show_config:
            display_board_configuration(config, jira_client)
            return
        
        # Check required arguments for cleaning operations
        if not args.column_name:
            print("❌ Error: column_name is required")
            print(f"Use --show-config to see available columns")
            sys.exit(1)
        
        # Handle remove-count mode
        if args.remove_count:
            if args.keep_statuses:
                print("❌ Error: Cannot use both --remove-count and keep_statuses")
                print("Use either --remove-count N to remove first N statuses, or specify statuses to keep")
                sys.exit(1)
            keep_statuses = []  # Empty list for remove-count mode
        else:
            if not args.keep_statuses:
                print("❌ Error: keep_statuses is required (or use --remove-count)")
                print(f"Specify which statuses to keep in the column")
                sys.exit(1)
            
            # Parse keep statuses
            keep_statuses = parse_statuses(args.keep_statuses)
            
            if not keep_statuses:
                print("❌ Error: No statuses specified to keep")
                sys.exit(1)
        
        print(f"🎯 Target column: {args.column_name}")
        if args.remove_count:
            print(f"🗑️  Will remove first {args.remove_count} statuses")
        else:
            print(f"✅ Statuses to keep: {keep_statuses}")
        if args.dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
        
        # Find the target column
        target_column = find_column_by_name(config, args.column_name)
        
        if not target_column:
            print(f"❌ Error: Column '{args.column_name}' not found")
            print("\nAvailable columns:")
            columns = config.get('columnConfig', {}).get('columns', [])
            for column in columns:
                print(f"   📁 {column.get('name', 'Unknown')}")
            sys.exit(1)
        
        # Show current column status
        current_statuses = target_column.get('statuses', [])
        current_status_names = [status.get('name', 'Unknown') for status in current_statuses]
        
        print(f"\n📁 Current '{args.column_name}' column statuses:")
        for status_name in current_status_names:
            print(f"   📌 {status_name}")
        
        # Clean the column
        cleaned_column, removed_statuses = clean_column_statuses(target_column, keep_statuses, jira_client, args.remove_count)
        
        if not removed_statuses:
            print(f"\n✅ Column '{args.column_name}' is already clean - no unwanted statuses found!")
            return
        
        print(f"\n🗑️  Statuses to be removed:")
        for status_name in removed_statuses:
            print(f"   ❌ {status_name}")
        
        print(f"\n✅ Statuses that will remain:")
        remaining_statuses = [status.get('name', 'Unknown') for status in cleaned_column.get('statuses', [])]
        for status_name in remaining_statuses:
            print(f"   ✅ {status_name}")
        
        if args.dry_run:
            print(f"\n🔍 DRY RUN: Would remove {len(removed_statuses)} statuses from '{args.column_name}' column")
            print("   Run without --dry-run to make actual changes")
            return
        
        # Confirm with user
        print(f"\n⚠️  About to remove {len(removed_statuses)} statuses from '{args.column_name}' column")
        print("   This will update the board configuration permanently!")
        confirm = input("Continue? (y/N): ").strip().lower()
        
        if confirm != 'y':
            print("Operation cancelled")
            return
        
        # Update the configuration
        print(f"\n🔄 Updating board configuration...")
        
        # Find and replace the column in the full config
        columns = config.get('columnConfig', {}).get('columns', [])
        for i, column in enumerate(columns):
            if column.get('name', '').lower() == args.column_name.lower():
                columns[i] = cleaned_column
                break
        
        # Update the board
        if jira_client.update_board_configuration(args.board_id, config):
            print(f"\n🎉 Successfully cleaned '{args.column_name}' column!")
            print(f"   ✅ Kept: {', '.join(remaining_statuses)}")
            print(f"   ❌ Removed: {', '.join(removed_statuses)}")
        else:
            print(f"\n❌ Failed to update board configuration")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()