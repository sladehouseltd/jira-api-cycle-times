#!/bin/bash
# Setup script for JIRA API client

echo "🚀 Setting up JIRA API client..."

# Check if we're in the right directory
if [ ! -f "jira_client.py" ]; then
    echo "❌ Error: jira_client.py not found. Run this script from the jira_api directory."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📥 Installing requirements..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo "📝 Please edit .env with your JIRA credentials:"
    echo "   - JIRA_URL"
    echo "   - JIRA_USERNAME" 
    echo "   - JIRA_TOKEN"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To use the script:"
echo "1. Edit .env with your JIRA credentials"
echo "2. Run: source venv/bin/activate"
echo "3. Run: python jira_client.py --help"
echo ""
echo "Example usage:"
echo "python jira_client.py PROJ \"Your Team\" \"bug,feature\" 2024-01-01 2024-01-31"