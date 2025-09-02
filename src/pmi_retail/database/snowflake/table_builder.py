"""
Snowflake Table Builder for PMI Workshop
Creates and manages database schema for retail execution demo
"""

from typing import List, Dict, Any
from loguru import logger
import sys
from pathlib import Path

# Package imports are now handled by the package structure
from .connection import SnowflakeManager
from ...config import settings


class PMITableBuilder:
    """
    Builds and manages PMI workshop database schema
    """
    
    def __init__(self):
        self.sf = SnowflakeManager()
        
        # Table creation order (respects foreign key dependencies)
        self.table_order = [
            'DATA_QUALITY_RULES',
            'ACCOUNTS',
            'CONTACTS',
            'NOTES',
            'PRODUCTS', 
            'CAMPAIGNS',
            'TRANSACTIONS',
            'LOYALTY_MEMBERS'
        ]
        
        # SQL statements for table creation
        self.table_definitions = {
            'ACCOUNTS': """
                CREATE OR REPLACE TABLE ACCOUNTS (
                    ACCOUNT_ID VARCHAR(50) PRIMARY KEY,
                    ACCOUNT_NAME VARCHAR(200) NOT NULL,
                    PARENT_ACCOUNT_ID VARCHAR(50), -- For hierarchy support
                    ACCOUNT_TYPE VARCHAR(50), -- Chain, Independent, Franchise, etc.
                    SEGMENT VARCHAR(20), -- Premium/Standard/Basic
                    ADDRESS VARCHAR(500),
                    CITY VARCHAR(100),
                    STATE VARCHAR(50),
                    ZIP_CODE VARCHAR(20),
                    COUNTRY VARCHAR(50) DEFAULT 'USA',
                    PHONE VARCHAR(50),
                    EMAIL VARCHAR(200),
                    REGISTRATION_DATE DATE,
                    STATUS VARCHAR(20) DEFAULT 'Active',
                    HIERARCHY_LEVEL INTEGER DEFAULT 1, -- 1=Parent, 2=Child, 3=Grandchild
                    ANNUAL_REVENUE DECIMAL(15,2),
                    EMPLOYEE_COUNT INTEGER,
                    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                    UPDATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
                )
            """,
            
            'CONTACTS': """
                CREATE OR REPLACE TABLE CONTACTS (
                    CONTACT_ID VARCHAR(50) PRIMARY KEY,
                    FIRST_NAME VARCHAR(100) NOT NULL,
                    LAST_NAME VARCHAR(100) NOT NULL,
                    EMAIL VARCHAR(200),
                    PHONE VARCHAR(50),
                    MOBILE_PHONE VARCHAR(50),
                    CONTACT_TYPE VARCHAR(50) DEFAULT 'Consumer', -- Consumer, Business, etc.
                    ACCOUNT_ID VARCHAR(50), -- Optional: loosely coupled to accounts
                    JOB_TITLE VARCHAR(100),
                    DEPARTMENT VARCHAR(100),
                    ADDRESS_LINE1 VARCHAR(200),
                    ADDRESS_LINE2 VARCHAR(200),
                    CITY VARCHAR(100),
                    STATE VARCHAR(50),
                    ZIP_CODE VARCHAR(20),
                    COUNTRY VARCHAR(50) DEFAULT 'USA',
                    DATE_OF_BIRTH DATE,
                    GENDER VARCHAR(20),
                    PREFERRED_CONTACT_METHOD VARCHAR(20) DEFAULT 'Email', -- Email, Phone, SMS
                    MARKETING_OPT_IN BOOLEAN DEFAULT FALSE,
                    STATUS VARCHAR(20) DEFAULT 'Active',
                    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                    UPDATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                    FOREIGN KEY (ACCOUNT_ID) REFERENCES ACCOUNTS(ACCOUNT_ID)
                )
            """,
            
            'NOTES': """
                CREATE OR REPLACE TABLE NOTES (
                    NOTE_ID VARCHAR(50) PRIMARY KEY,
                    NOTE_TYPE VARCHAR(50) NOT NULL, -- Contact Note, Account Note, General Note
                    NOTE_CATEGORY VARCHAR(100), -- Customer Service, Sales, Support, General
                    NOTE_PRIORITY VARCHAR(20) DEFAULT 'Medium', -- Low, Medium, High, Critical
                    NOTE_STATUS VARCHAR(20) DEFAULT 'Active', -- Active, Resolved, Archived
                    SUBJECT VARCHAR(200),
                    NOTE_TEXT TEXT NOT NULL,
                    CONTACT_ID VARCHAR(50), -- Optional: link to specific contact
                    ACCOUNT_ID VARCHAR(50), -- Optional: link to specific account
                    ASSIGNED_TO VARCHAR(100), -- Who is responsible for this note
                    DUE_DATE DATE, -- When action is due
                    RESOLUTION_DATE DATE, -- When note was resolved
                    EFFECTIVE_START_DATE DATE NOT NULL, -- When note becomes effective
                    EFFECTIVE_END_DATE DATE, -- When note expires (NULL = no expiration)
                    IS_PRIVATE BOOLEAN DEFAULT FALSE, -- Private/internal notes
                    TAGS VARCHAR(500), -- Comma-separated tags for categorization
                    CREATED_BY VARCHAR(100) NOT NULL,
                    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                    UPDATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                    FOREIGN KEY (CONTACT_ID) REFERENCES CONTACTS(CONTACT_ID),
                    FOREIGN KEY (ACCOUNT_ID) REFERENCES ACCOUNTS(ACCOUNT_ID)
                )
            """,
            
            'PRODUCTS': """
                CREATE OR REPLACE TABLE PRODUCTS (
                    PRODUCT_ID VARCHAR(50) PRIMARY KEY,
                    PRODUCT_NAME VARCHAR(200) NOT NULL,
                    CATEGORY VARCHAR(100),
                    SUBCATEGORY VARCHAR(100),
                    BRAND VARCHAR(100),
                    UNIT_PRICE DECIMAL(10,2),
                    COST_PRICE DECIMAL(10,2),
                    LAUNCH_DATE DATE,
                    STATUS VARCHAR(20) DEFAULT 'Active',
                    PRODUCT_DESCRIPTION TEXT,
                    IS_NEW_PRODUCT BOOLEAN DEFAULT FALSE,
                    TARGET_SEGMENT VARCHAR(50), -- Premium/Standard/Basic
                    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                    UPDATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
                )
            """,
            
            'CAMPAIGNS': """
                CREATE OR REPLACE TABLE CAMPAIGNS (
                    CAMPAIGN_ID VARCHAR(50) PRIMARY KEY,
                    CAMPAIGN_NAME VARCHAR(200) NOT NULL,
                    CAMPAIGN_TYPE VARCHAR(50) NOT NULL, -- Email, Social, Print, In-Store, Digital
                    CAMPAIGN_CATEGORY VARCHAR(100), -- Promotional, Seasonal, Product Launch, Brand Awareness
                    DESCRIPTION TEXT,
                    START_DATE DATE NOT NULL,
                    END_DATE DATE NOT NULL,
                    BUDGET DECIMAL(12,2), -- Campaign budget
                    ACTUAL_SPEND DECIMAL(12,2), -- Actual amount spent
                    TARGET_SEGMENT VARCHAR(50), -- Premium/Standard/Basic
                    TARGET_ACCOUNTS VARCHAR(500), -- Comma-separated account IDs or 'ALL'
                    TARGET_PRODUCTS VARCHAR(500), -- Comma-separated product IDs or 'ALL'
                    DISCOUNT_PERCENTAGE DECIMAL(5,2), -- Percentage discount offered
                    STATUS VARCHAR(20) DEFAULT 'Active', -- Active, Paused, Completed, Cancelled
                    SUCCESS_METRICS TEXT, -- Campaign performance notes
                    CREATED_BY VARCHAR(100) NOT NULL,
                    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                    UPDATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
                )
            """,
            
            'TRANSACTIONS': """
                CREATE OR REPLACE TABLE TRANSACTIONS (
                    TRANSACTION_ID VARCHAR(50) PRIMARY KEY,
                    ACCOUNT_ID VARCHAR(50) NOT NULL,
                    CONTACT_ID VARCHAR(50), -- Optional: which consumer made the transaction
                    PRODUCT_ID VARCHAR(50) NOT NULL,
                    CAMPAIGN_ID VARCHAR(50), -- Optional: which campaign drove the transaction
                    TRANSACTION_DATE DATE NOT NULL,
                    QUANTITY INTEGER NOT NULL,
                    UNIT_PRICE DECIMAL(10,2) NOT NULL,
                    TOTAL_AMOUNT DECIMAL(12,2) NOT NULL,
                    DISCOUNT_AMOUNT DECIMAL(10,2) DEFAULT 0,
                    NET_AMOUNT DECIMAL(12,2),
                    SALES_REP VARCHAR(100),
                    ORDER_SOURCE VARCHAR(50), -- Online, Phone, In-Person, etc.
                    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                    FOREIGN KEY (ACCOUNT_ID) REFERENCES ACCOUNTS(ACCOUNT_ID),
                    FOREIGN KEY (CONTACT_ID) REFERENCES CONTACTS(CONTACT_ID),
                    FOREIGN KEY (PRODUCT_ID) REFERENCES PRODUCTS(PRODUCT_ID),
                    FOREIGN KEY (CAMPAIGN_ID) REFERENCES CAMPAIGNS(CAMPAIGN_ID)
                )
            """,
            
            'LOYALTY_MEMBERS': """
                CREATE OR REPLACE TABLE LOYALTY_MEMBERS (
                    MEMBER_ID VARCHAR(50) PRIMARY KEY,
                    ACCOUNT_ID VARCHAR(50) NOT NULL,
                    CONTACT_ID VARCHAR(50), -- Optional: which consumer is in the loyalty program
                    MEMBER_EMAIL VARCHAR(200),
                    MEMBER_PHONE VARCHAR(50),
                    LOYALTY_TIER VARCHAR(20), -- Bronze/Silver/Gold/Platinum
                    POINTS_BALANCE INTEGER DEFAULT 0,
                    LIFETIME_POINTS INTEGER DEFAULT 0,
                    JOIN_DATE DATE NOT NULL,
                    LAST_ACTIVITY_DATE DATE,
                    STATUS VARCHAR(20) DEFAULT 'Active',
                    PREFERRED_CONTACT VARCHAR(20) DEFAULT 'Email', -- Email/Phone/SMS
                    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                    FOREIGN KEY (ACCOUNT_ID) REFERENCES ACCOUNTS(ACCOUNT_ID),
                    FOREIGN KEY (CONTACT_ID) REFERENCES CONTACTS(CONTACT_ID)
                )
            """,
            
            'DATA_QUALITY_RULES': """
                CREATE OR REPLACE TABLE DATA_QUALITY_RULES (
                    RULE_ID VARCHAR(50) PRIMARY KEY,
                    RULE_NAME VARCHAR(200),
                    TABLE_NAME VARCHAR(100),
                    COLUMN_NAME VARCHAR(100),
                    RULE_TYPE VARCHAR(50), -- DUPLICATE, MISSING, FORMAT, RANGE
                    RULE_DEFINITION TEXT,
                    IS_ACTIVE BOOLEAN DEFAULT TRUE,
                    SEVERITY VARCHAR(20) DEFAULT 'Medium', -- Low/Medium/High/Critical
                    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
                )
            """
        }
        
        # Views and additional objects
        self.view_definitions = {
            'VW_ACCOUNT_HIERARCHY': """
                CREATE OR REPLACE VIEW VW_ACCOUNT_HIERARCHY AS
                WITH RECURSIVE account_hierarchy AS (
                    -- Base case: root accounts (no parent)
                    SELECT 
                        ACCOUNT_ID,
                        ACCOUNT_NAME,
                        PARENT_ACCOUNT_ID,
                        ACCOUNT_TYPE,
                        SEGMENT,
                        HIERARCHY_LEVEL,
                        ACCOUNT_ID as ROOT_ACCOUNT_ID,
                        ACCOUNT_NAME as ROOT_ACCOUNT_NAME,
                        ACCOUNT_ID as HIERARCHY_PATH
                    FROM ACCOUNTS 
                    WHERE PARENT_ACCOUNT_ID IS NULL
                    
                    UNION ALL
                    
                    -- Recursive case: child accounts
                    SELECT 
                        a.ACCOUNT_ID,
                        a.ACCOUNT_NAME,
                        a.PARENT_ACCOUNT_ID,
                        a.ACCOUNT_TYPE,
                        a.SEGMENT,
                        a.HIERARCHY_LEVEL,
                        ah.ROOT_ACCOUNT_ID,
                        ah.ROOT_ACCOUNT_NAME,
                        CONCAT(ah.HIERARCHY_PATH, ' > ', a.ACCOUNT_ID) as HIERARCHY_PATH
                    FROM ACCOUNTS a
                    INNER JOIN account_hierarchy ah ON a.PARENT_ACCOUNT_ID = ah.ACCOUNT_ID
                )
                SELECT * FROM account_hierarchy
            """,
            
            'VW_CONTACT_ACCOUNT_RELATIONSHIPS': """
                CREATE OR REPLACE VIEW VW_CONTACT_ACCOUNT_RELATIONSHIPS AS
                SELECT 
                    c.CONTACT_ID,
                    c.FIRST_NAME,
                    c.LAST_NAME,
                    c.EMAIL,
                    c.CONTACT_TYPE,
                    c.ACCOUNT_ID,
                    a.ACCOUNT_NAME,
                    a.ACCOUNT_TYPE,
                    a.SEGMENT,
                    CASE 
                        WHEN c.ACCOUNT_ID IS NOT NULL THEN 'Linked'
                        ELSE 'Independent'
                    END as RELATIONSHIP_STATUS,
                    c.CREATED_TIMESTAMP as CONTACT_CREATED,
                    a.REGISTRATION_DATE as ACCOUNT_REGISTERED
                FROM CONTACTS c
                LEFT JOIN ACCOUNTS a ON c.ACCOUNT_ID = a.ACCOUNT_ID
                ORDER BY c.LAST_NAME, c.FIRST_NAME
            """,
            
            'VW_NOTES_SUMMARY': """
                CREATE OR REPLACE VIEW VW_NOTES_SUMMARY AS
                SELECT 
                    n.NOTE_ID,
                    n.NOTE_TYPE,
                    n.NOTE_CATEGORY,
                    n.NOTE_PRIORITY,
                    n.NOTE_STATUS,
                    n.SUBJECT,
                    LEFT(n.NOTE_TEXT, 100) as NOTE_PREVIEW,
                    n.CONTACT_ID,
                    c.FIRST_NAME || ' ' || c.LAST_NAME as CONTACT_NAME,
                    n.ACCOUNT_ID,
                    a.ACCOUNT_NAME,
                    n.ASSIGNED_TO,
                    n.DUE_DATE,
                    n.EFFECTIVE_START_DATE,
                    n.EFFECTIVE_END_DATE,
                    n.IS_PRIVATE,
                    n.CREATED_BY,
                    n.CREATED_TIMESTAMP,
                    CASE 
                        WHEN n.EFFECTIVE_END_DATE IS NOT NULL AND n.EFFECTIVE_END_DATE < CURRENT_DATE() THEN 'Expired'
                        WHEN n.EFFECTIVE_START_DATE > CURRENT_DATE() THEN 'Future'
                        ELSE 'Active'
                    END as TIME_STATUS
                FROM NOTES n
                LEFT JOIN CONTACTS c ON n.CONTACT_ID = c.CONTACT_ID
                LEFT JOIN ACCOUNTS a ON n.ACCOUNT_ID = a.ACCOUNT_ID
                ORDER BY n.CREATED_TIMESTAMP DESC
            """,
            
            'VW_CAMPAIGN_PERFORMANCE': """
                CREATE OR REPLACE VIEW VW_CAMPAIGN_PERFORMANCE AS
                SELECT 
                    c.CAMPAIGN_ID,
                    c.CAMPAIGN_NAME,
                    c.CAMPAIGN_TYPE,
                    c.CAMPAIGN_CATEGORY,
                    c.START_DATE,
                    c.END_DATE,
                    c.BUDGET,
                    c.ACTUAL_SPEND,
                    c.STATUS,
                    c.TARGET_SEGMENT,
                    COUNT(t.TRANSACTION_ID) as TRANSACTIONS_GENERATED,
                    SUM(t.NET_AMOUNT) as TOTAL_REVENUE,
                    AVG(t.NET_AMOUNT) as AVG_TRANSACTION_VALUE,
                    CASE 
                        WHEN c.BUDGET > 0 THEN (SUM(t.NET_AMOUNT) / c.BUDGET) * 100
                        ELSE NULL
                    END as ROI_PERCENTAGE,
                    CASE 
                        WHEN c.ACTUAL_SPEND > 0 THEN (SUM(t.NET_AMOUNT) / c.ACTUAL_SPEND) * 100
                        ELSE NULL
                    END as ROAS_PERCENTAGE
                FROM CAMPAIGNS c
                LEFT JOIN TRANSACTIONS t ON c.CAMPAIGN_ID = t.CAMPAIGN_ID
                GROUP BY 
                    c.CAMPAIGN_ID, c.CAMPAIGN_NAME, c.CAMPAIGN_TYPE, c.CAMPAIGN_CATEGORY,
                    c.START_DATE, c.END_DATE, c.BUDGET, c.ACTUAL_SPEND, c.STATUS, c.TARGET_SEGMENT
                ORDER BY TOTAL_REVENUE DESC
            """
        }
        
        # Sample data quality rules
        self.sample_dq_rules = [
            {
                'RULE_ID': 'DQ001',
                'RULE_NAME': 'Duplicate Account Names',
                'TABLE_NAME': 'ACCOUNTS',
                'COLUMN_NAME': 'ACCOUNT_NAME',
                'RULE_TYPE': 'DUPLICATE',
                'RULE_DEFINITION': 'Identify accounts with same name but different IDs',
                'IS_ACTIVE': True,
                'SEVERITY': 'High'
            },
            {
                'RULE_ID': 'DQ002',
                'RULE_NAME': 'Missing Email Addresses',
                'TABLE_NAME': 'ACCOUNTS',
                'COLUMN_NAME': 'EMAIL',
                'RULE_TYPE': 'MISSING',
                'RULE_DEFINITION': 'Flag accounts without email addresses',
                'IS_ACTIVE': True,
                'SEVERITY': 'Medium'
            },
            {
                'RULE_ID': 'DQ003',
                'RULE_NAME': 'Invalid Phone Format',
                'TABLE_NAME': 'ACCOUNTS',
                'COLUMN_NAME': 'PHONE',
                'RULE_TYPE': 'FORMAT',
                'RULE_DEFINITION': 'Check phone number format consistency',
                'IS_ACTIVE': True,
                'SEVERITY': 'Low'
            },
            {
                'RULE_ID': 'DQ004',
                'RULE_NAME': 'Negative Transaction Amounts',
                'TABLE_NAME': 'TRANSACTIONS',
                'COLUMN_NAME': 'TOTAL_AMOUNT',
                'RULE_TYPE': 'RANGE',
                'RULE_DEFINITION': 'Flag transactions with negative amounts',
                'IS_ACTIVE': True,
                'SEVERITY': 'Critical'
            },
            {
                'RULE_ID': 'DQ005',
                'RULE_NAME': 'Future Transaction Dates',
                'TABLE_NAME': 'TRANSACTIONS',
                'COLUMN_NAME': 'TRANSACTION_DATE',
                'RULE_TYPE': 'RANGE',
                'RULE_DEFINITION': 'Flag transactions with future dates',
                'IS_ACTIVE': True,
                'SEVERITY': 'High'
            },
            {
                'RULE_ID': 'DQ006',
                'RULE_NAME': 'Duplicate Consumer Identification',
                'TABLE_NAME': 'CONTACTS',
                'COLUMN_NAME': 'FIRST_NAME,LAST_NAME,EMAIL',
                'RULE_TYPE': 'DUPLICATE',
                'RULE_DEFINITION': 'Identify potential duplicate consumers with same name and email',
                'IS_ACTIVE': True,
                'SEVERITY': 'High'
            },
            {
                'RULE_ID': 'DQ007',
                'RULE_NAME': 'Consumer Email Format Validation',
                'TABLE_NAME': 'CONTACTS',
                'COLUMN_NAME': 'EMAIL',
                'RULE_TYPE': 'FORMAT',
                'RULE_DEFINITION': 'Validate email format for consumer contacts',
                'IS_ACTIVE': True,
                'SEVERITY': 'Medium'
            },
            {
                'RULE_ID': 'DQ008',
                'RULE_NAME': 'Consumer Phone Format Validation',
                'TABLE_NAME': 'CONTACTS',
                'COLUMN_NAME': 'PHONE,MOBILE_PHONE',
                'RULE_TYPE': 'FORMAT',
                'RULE_DEFINITION': 'Validate phone number format consistency',
                'IS_ACTIVE': True,
                'SEVERITY': 'Medium'
            },
            {
                'RULE_ID': 'DQ009',
                'RULE_NAME': 'Consumer Age Validation',
                'TABLE_NAME': 'CONTACTS',
                'COLUMN_NAME': 'DATE_OF_BIRTH',
                'RULE_TYPE': 'RANGE',
                'RULE_DEFINITION': 'Flag consumers with invalid birth dates (future dates or too old)',
                'IS_ACTIVE': True,
                'SEVERITY': 'Low'
            },
            {
                'RULE_ID': 'DQ010',
                'RULE_NAME': 'Consumer-Transaction Linkage',
                'TABLE_NAME': 'TRANSACTIONS',
                'COLUMN_NAME': 'CONTACT_ID',
                'RULE_TYPE': 'REFERENCE',
                'RULE_DEFINITION': 'Ensure CONTACT_ID in transactions references valid contacts',
                'IS_ACTIVE': True,
                'SEVERITY': 'High'
            },
            {
                'RULE_ID': 'DQ011',
                'RULE_NAME': 'Note Time Validation',
                'TABLE_NAME': 'NOTES',
                'COLUMN_NAME': 'EFFECTIVE_START_DATE,EFFECTIVE_END_DATE',
                'RULE_TYPE': 'RANGE',
                'RULE_DEFINITION': 'Ensure effective start date is before end date, and both are valid dates',
                'IS_ACTIVE': True,
                'SEVERITY': 'Medium'
            },
            {
                'RULE_ID': 'DQ012',
                'RULE_NAME': 'Note Reference Validation',
                'TABLE_NAME': 'NOTES',
                'COLUMN_NAME': 'CONTACT_ID,ACCOUNT_ID',
                'RULE_TYPE': 'REFERENCE',
                'RULE_DEFINITION': 'Ensure at least one reference (CONTACT_ID or ACCOUNT_ID) is provided',
                'IS_ACTIVE': True,
                'SEVERITY': 'High'
            },
            {
                'RULE_ID': 'DQ013',
                'RULE_NAME': 'Note Due Date Validation',
                'TABLE_NAME': 'NOTES',
                'COLUMN_NAME': 'DUE_DATE',
                'RULE_TYPE': 'RANGE',
                'RULE_DEFINITION': 'Ensure due dates are not in the past for active notes',
                'IS_ACTIVE': True,
                'SEVERITY': 'Medium'
            },
            {
                'RULE_ID': 'DQ014',
                'RULE_NAME': 'Campaign Date Validation',
                'TABLE_NAME': 'CAMPAIGNS',
                'COLUMN_NAME': 'START_DATE,END_DATE',
                'RULE_TYPE': 'RANGE',
                'RULE_DEFINITION': 'Ensure campaign start date is before end date',
                'IS_ACTIVE': True,
                'SEVERITY': 'High'
            },
            {
                'RULE_ID': 'DQ015',
                'RULE_NAME': 'Campaign Budget Validation',
                'TABLE_NAME': 'CAMPAIGNS',
                'COLUMN_NAME': 'BUDGET,ACTUAL_SPEND',
                'RULE_TYPE': 'RANGE',
                'RULE_DEFINITION': 'Ensure actual spend does not exceed budget',
                'IS_ACTIVE': True,
                'SEVERITY': 'Medium'
            }
        ]
    
    def connect(self) -> bool:
        """Connect to Snowflake"""
        return self.sf.connect()
    
    def create_schema_if_not_exists(self) -> bool:
        """Create schema if it doesn't exist"""
        logger.info(f"Creating schema {settings.snowflake_database}.{settings.snowflake_schema}")
        
        try:
            # Execute each statement separately
            # Use database
            if not self.sf.execute_sql(f"USE DATABASE {settings.snowflake_database}"):
                logger.error("Failed to use database")
                return False
            
            # Create schema if not exists
            if not self.sf.execute_sql(f"CREATE SCHEMA IF NOT EXISTS {settings.snowflake_schema}"):
                logger.error("Failed to create schema")
                return False
            
            # Use schema
            if not self.sf.execute_sql(f"USE SCHEMA {settings.snowflake_schema}"):
                logger.error("Failed to use schema")
                return False
            
            logger.info(f"✅ Schema {settings.snowflake_database}.{settings.snowflake_schema} ready")
            return True
            
        except Exception as e:
            logger.error(f"Schema creation failed: {str(e)}")
            return False
    
    def drop_all_tables(self) -> bool:
        """Drop all PMI workshop tables (careful!)"""
        logger.warning("⚠️ Dropping all PMI workshop tables...")
        
        # Drop in reverse order to handle foreign keys
        success = True
        for table_name in reversed(self.table_order):
            drop_sql = f"DROP TABLE IF EXISTS {table_name} CASCADE"
            if not self.sf.execute_sql(drop_sql):
                success = False
                logger.error(f"Failed to drop table {table_name}")
            else:
                logger.info(f"Dropped table {table_name}")
        
        return success
    
    def create_all_tables(self, drop_existing: bool = False) -> bool:
        """
        Create all PMI workshop tables
        
        Args:
            drop_existing: If True, drop existing tables first
        """
        logger.info("🏗️ Starting table creation process...")
        
        try:
            # Create schema first
            if not self.create_schema_if_not_exists():
                logger.error("Failed to create/use schema")
                return False
            
            # Drop existing tables if requested
            if drop_existing:
                if not self.drop_all_tables():
                    logger.warning("Some tables failed to drop, continuing...")
            
            # Create tables in order
            for table_name in self.table_order:
                logger.info(f"Creating table: {table_name}")
                
                if not self.sf.execute_sql(self.table_definitions[table_name]):
                    logger.error(f"Failed to create table {table_name}")
                    return False
                
                logger.info(f"✅ Created table: {table_name}")
            
            # Add foreign key constraint for account hierarchy
            logger.info("Adding foreign key constraints...")
            fk_sql = """
            ALTER TABLE ACCOUNTS 
            ADD CONSTRAINT FK_ACCOUNTS_PARENT 
            FOREIGN KEY (PARENT_ACCOUNT_ID) REFERENCES ACCOUNTS(ACCOUNT_ID)
            """
            
            # This might fail if constraint already exists, that's OK
            self.sf.execute_sql(fk_sql)
            
            # Create views
            logger.info("Creating views...")
            for view_name, view_sql in self.view_definitions.items():
                if self.sf.execute_sql(view_sql):
                    logger.info(f"✅ Created view: {view_name}")
                else:
                    logger.error(f"Failed to create view {view_name}")
            
            # Add clustering keys for performance
            logger.info("Adding clustering keys...")
            clustering_sqls = [
                "ALTER TABLE TRANSACTIONS CLUSTER BY (TRANSACTION_DATE, ACCOUNT_ID)",
                "ALTER TABLE ACCOUNTS CLUSTER BY (SEGMENT, STATE)"
            ]
            
            for cluster_sql in clustering_sqls:
                self.sf.execute_sql(cluster_sql)  # These might fail, that's OK
            
            # Load sample data quality rules
            logger.info("Loading sample data quality rules...")
            self.load_sample_dq_rules()
            
            logger.info("🎉 All tables created successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Table creation failed: {str(e)}")
            return False
    
    def load_sample_dq_rules(self) -> bool:
        """Load sample data quality rules"""
        try:
            for rule in self.sample_dq_rules:
                columns = ', '.join(rule.keys())
                placeholders = ', '.join([f"'{v}'" if isinstance(v, str) else str(v) for v in rule.values()])
                
                sql = f"INSERT INTO DATA_QUALITY_RULES ({columns}) VALUES ({placeholders})"
                self.sf.execute_sql(sql)
            
            logger.info(f"✅ Loaded {len(self.sample_dq_rules)} data quality rules")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load sample DQ rules: {str(e)}")
            return False
    
    def verify_tables(self) -> Dict[str, Any]:
        """Verify all tables were created correctly"""
        logger.info("🔍 Verifying table creation...")
        
        results = {}
        
        # Check each table exists and get basic info
        for table_name in self.table_order:
            try:
                # Check if table exists
                info_query = f"""
                SELECT COUNT(*) as ROW_COUNT 
                FROM {table_name}
                """
                
                row_count_df = self.sf.execute_query(info_query)
                row_count = row_count_df.iloc[0]['ROW_COUNT'] if len(row_count_df) > 0 else 0
                
                # Get table structure
                desc_df = self.sf.get_table_info(table_name)
                column_count = len(desc_df) if desc_df is not None else 0
                
                results[table_name] = {
                    'exists': True,
                    'row_count': row_count,
                    'column_count': column_count
                }
                
                logger.info(f"✅ {table_name}: {column_count} columns, {row_count} rows")
                
            except Exception as e:
                results[table_name] = {
                    'exists': False,
                    'error': str(e)
                }
                logger.error(f"❌ {table_name}: {str(e)}")
        
        # Check views
        try:
            view_query = "SELECT COUNT(*) as ROW_COUNT FROM VW_ACCOUNT_HIERARCHY"
            view_df = self.sf.execute_query(view_query)
            results['VW_ACCOUNT_HIERARCHY'] = {
                'exists': True,
                'row_count': view_df.iloc[0]['ROW_COUNT'] if len(view_df) > 0 else 0
            }
        except Exception as e:
            results['VW_ACCOUNT_HIERARCHY'] = {
                'exists': False,
                'error': str(e)
            }
        
        return results
    
    def get_table_summary(self) -> None:
        """Print a summary of all tables"""
        print("\n" + "="*60)
        print("📊 PMI WORKSHOP DATABASE SUMMARY")
        print("="*60)
        
        verification_results = self.verify_tables()
        
        for table_name, info in verification_results.items():
            status = "✅" if info.get('exists', False) else "❌"
            if info.get('exists', False):
                print(f"{status} {table_name:<25} | Columns: {info.get('column_count', 0):>3} | Rows: {info.get('row_count', 0):>6}")
            else:
                print(f"{status} {table_name:<25} | ERROR: {info.get('error', 'Unknown')}")
        
        print("="*60)
    
    def close(self):
        """Close the Snowflake connection"""
        self.sf.close_connection()


def main():
    """Main function to create PMI workshop tables"""
    print("🏗️ PMI Workshop - Table Creation Script")
    print("="*50)
    
    builder = PMITableBuilder()
    
    try:
        # Connect to Snowflake
        if not builder.connect():
            print("❌ Failed to connect to Snowflake. Check your .env configuration.")
            return False
        
        print(f"✅ Connected to Snowflake: {settings.snowflake_database}.{settings.snowflake_schema}")
        
        # Create tables
        success = builder.create_all_tables(drop_existing=True)
        
        if success:
            # Show summary
            builder.get_table_summary()
            print("\n🎉 Database setup completed successfully!")
            print("\nNext steps:")
            print("1. Run data generation script to populate tables")
            print("2. Test AI agents with sample data")
            print("3. Start Streamlit demo applications")
            return True
        else:
            print("❌ Database setup failed. Check logs for details.")
            return False
            
    except Exception as e:
        logger.error(f"Setup script failed: {str(e)}")
        print(f"❌ Setup failed: {str(e)}")
        return False
        
    finally:
        builder.close()


if __name__ == "__main__":
    main()