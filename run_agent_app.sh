#!/bin/bash

# Run Agent App - PDF Chat QA with OpenAI, FAISS, and LangChain
echo "🚀 Starting PDF Chat QA Application..."

# Check if we're in the right directory
if [ ! -f "src/app.py" ]; then
    echo "❌ Error: src/app.py not found. Please run this script from the project root."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Please create one with your OpenAI API key."
    echo "   Example .env content:"
    echo "   OPENAI_API_KEY=your_api_key_here"
fi

# Run the Streamlit app
echo "📚 Launching Streamlit PDF Chat QA..."
echo "🌐 The app will open in your browser at http://localhost:8501"
echo "📱 You can also access it on your mobile device at your local IP"
echo ""
echo "💡 Tips:"
echo "   - Set your OpenAI API key in the sidebar"
echo "   - Upload a PDF to start chatting"
echo "   - Use the Advanced tab to test connections"
echo ""

# Run with UV
uv run streamlit run src/app.py --server.port 8501 --server.address 0.0.0.0
