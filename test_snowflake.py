#!/usr/bin/env python3
"""
Simple Snowflake connection test
"""

import os
import snowflake.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    """Test basic Snowflake connection"""
    try:
        print("Testing Snowflake connection...")
        
        # Get connection parameters
        connection_params = {
            'user': os.getenv('SNOWFLAKE_USER'),
            'password': os.getenv('SNOWFLAKE_PASSWORD'),
            'account': os.getenv('SNOWFLAKE_ACCOUNT'),
            'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE'),
            'database': os.getenv('SNOWFLAKE_DATABASE'),
            'schema': os.getenv('SNOWFLAKE_SCHEMA'),
            'role': os.getenv('SNOWFLAKE_ROLE')
        }
        
        print(f"Account: {connection_params['account']}")
        print(f"User: {connection_params['user']}")
        print(f"Database: {connection_params['database']}")
        print(f"Schema: {connection_params['schema']}")
        print(f"Warehouse: {connection_params['warehouse']}")
        
        # Remove empty parameters
        connection_params = {k: v for k, v in connection_params.items() if v}
        
        print("Attempting to connect...")
        conn = snowflake.connector.connect(**connection_params)
        
        print("✅ Connected successfully!")
        
        # Test a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_VERSION() as VERSION, CURRENT_USER() as USER")
        result = cursor.fetchone()
        
        print(f"Version: {result[0]}")
        print(f"User: {result[1]}")
        
        cursor.close()
        conn.close()
        print("✅ Connection test completed successfully!")
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    test_connection()

