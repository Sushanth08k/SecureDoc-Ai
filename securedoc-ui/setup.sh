#!/bin/bash

# Setup script for SecureDoc UI

echo "Setting up SecureDoc UI..."

# Change to the UI directory
cd "$(dirname "$0")"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is required but not installed. Please install Node.js and try again."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
npm install

# Start the development server
echo "Starting development server..."
echo "Open your browser and navigate to http://localhost:5173"
npm run dev
