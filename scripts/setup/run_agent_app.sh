#!/bin/bash
echo "🚀 Starting PDF Chat QA Application with OpenAI..."

# Check if .env file exists and has API key
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it with your OpenAI API key."
    exit 1
fi

if grep -q "your_openai_api_key_here" .env; then
    echo "❌ Please set your actual OpenAI API key in .env file"
    echo "Edit .env and replace 'your_openai_api_key_here' with your actual API key"
    exit 1
fi

uv run streamlit run src/app.py --server.runOnSave true
