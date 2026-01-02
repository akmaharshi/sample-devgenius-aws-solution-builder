#!/bin/bash

# DevGenius Local Mode Setup Script
# This script helps you set up DevGenius for local development

echo "========================================="
echo "DevGenius Local Mode Setup"
echo "========================================="
echo ""

# Create local data directory
echo "Creating local data directory..."
mkdir -p local_data/{storage,conversations,sessions,feedback}
echo "✓ Created local_data directory"
echo ""

# Copy environment file if it doesn't exist
if [ ! -f .env.local ]; then
    echo "Creating .env.local file..."
    cp .env.local.example .env.local
    echo "✓ Created .env.local from example"
    echo ""
    echo "📝 Please edit .env.local to add your configuration:"
    echo "   - Add AWS credentials if you want to use Bedrock"
    echo "   - Or leave it as-is to run without Bedrock features"
    echo ""
else
    echo "ℹ️  .env.local already exists, skipping..."
    echo ""
fi

# Check if Docker is installed
if command -v docker &> /dev/null; then
    echo "✓ Docker is installed"

    # Check if Docker Compose is installed
    if command -v docker-compose &> /dev/null; then
        echo "✓ Docker Compose is installed"
        echo ""
        echo "========================================="
        echo "Setup Complete!"
        echo "========================================="
        echo ""
        echo "To start DevGenius in local mode, run:"
        echo "  docker-compose -f docker-compose.local.yml up"
        echo ""
        echo "Then access the application at:"
        echo "  http://localhost:8501"
        echo ""
    else
        echo "⚠️  Docker Compose is not installed"
        echo ""
        echo "Please install Docker Compose to use the automated setup"
        echo "Or run manually with Python (see README.md for instructions)"
        echo ""
    fi
else
    echo "⚠️  Docker is not installed"
    echo ""
    echo "To run without Docker, you'll need:"
    echo "  - Python 3.12 or later"
    echo "  - pip install -r chatbot/requirements.txt"
    echo ""
    echo "See README.md for detailed instructions"
    echo ""
fi

echo "For more information, see the README.md file."
echo ""
