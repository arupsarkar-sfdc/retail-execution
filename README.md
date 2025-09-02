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

## 📁 Project Structure

Generated automatically with proper folder structure for:
- Database operations (Snowflake & MDM)
- AI agents (LangChain & Salesforce comparison)  
- Streamlit demo applications
- Tests and documentation

**Workshop Dates**: September 8-11, 2025
