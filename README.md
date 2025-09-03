# PMI Retail Workshop - Snowflake MDM & AI Agents

A comprehensive workshop demonstrating retail execution capabilities through Master Data Management (MDM) in Snowflake and AI agents using LangChain.

## 🚀 Quick Start

1. **Setup completed by script** ✅
2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```
3. **Sync dependencies:**
   ```bash
   uv sync
   ```
4. **Start development:**
   ```bash
   source .venv/bin/activate
   # Ready to code!
   ```

## 🛠️ Available Commands

### Database Setup & Management
- **`uv run pmi-setup test-connection`** - Test Snowflake connection
- **`uv run pmi-setup init-database [--drop]`** - Initialize database tables (use `--drop` to recreate)
- **`uv run pmi-setup load-sample-data [--scale small|medium|large]`** - Load sample data
- **`uv run pmi-setup test-queries`** - Run test queries to validate setup
- **`uv run pmi-setup status`** - Check current setup status

### AI Applications
- **`uv run streamlit run src/app.py --server.headless true --server.port 8501`** - Launch integrated AI dashboard
  - 📄 PDF Document Chat with AI
  - 📊 AI-Powered Account Summary Generation
  - 🔍 Advanced Analytics and Insights

### Data Scale Options
- **small**: 30 accounts, 20 products, 3 months history
- **medium**: 100 accounts, 50 products, 6 months history  
- **large**: 500 accounts, 200 products, 12 months history

## 📊 Database Schema

### Core Tables
- **ACCOUNTS** - Retail account hierarchy (Chain → Regional → Store)
- **CONTACTS** - Consumer contacts (loosely coupled to accounts)
- **NOTES** - Time-bound notes linked to contacts and accounts
- **PRODUCTS** - Product catalog with categories and pricing
- **CAMPAIGNS** - Marketing campaigns and promotions
- **TRANSACTIONS** - Sales transactions linked to accounts, contacts, and campaigns
- **LOYALTY_MEMBERS** - Loyalty program members
- **DATA_QUALITY_RULES** - Data quality validation rules

### Key Features
- **Account Hierarchy**: Multi-level retail organization structure
- **Contact Management**: Consumer contacts with optional account relationships
- **Data Quality**: Built-in validation rules for data integrity
- **Sample Data**: Realistic retail data generation for testing
- **AI-Powered Analytics**: OpenAI GPT-4 integration for intelligent insights
- **Identity Resolution**: Advanced fuzzy matching for account and contact deduplication

## 🤖 AI Features

### Account Summary Generation
- **AI-Powered Analysis**: Uses OpenAI GPT-4 for comprehensive account insights
- **Data Aggregation**: Combines data from ACCOUNTS, CONTACTS, NOTES, TRANSACTIONS, and CAMPAIGNS tables
- **Intelligent Insights**: Generates executive summaries, business insights, and actionable recommendations
- **Risk Assessment**: Identifies potential risks and opportunities
- **Export Options**: JSON and Markdown export functionality

### PDF Document Chat
- **Document Processing**: Upload and process PDF documents with LangChain
- **Vector Search**: FAISS-based semantic search for relevant content
- **Conversational AI**: Chat with document content using OpenAI models
- **Source Attribution**: Shows relevant document sections for each response

### Requirements
- **OpenAI API Key**: Required for AI functionality
- **Snowflake Connection**: Required for account summary generation
- **Internet Connection**: For API calls to OpenAI

## 📁 Project Structure

Generated automatically with proper folder structure for:
- Database operations (Snowflake & MDM)
- AI agents (LangChain & OpenAI integration)  
- Streamlit demo applications
- Tests and documentation

**Workshop Dates**: September 8-11, 2025
