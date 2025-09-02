#!/usr/bin/env python3
"""
Clean test of Snowflake connection
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_clean():
    """Test clean Snowflake connection"""
    try:
        print("Testing clean Snowflake connection...")
        
        # Only import what we need
        import snowflake.connector
        
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
        
        print("Connection parameters loaded")
        
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
        print("✅ Clean connection test completed successfully!")
        
    except Exception as e:
        print(f"❌ Clean connection failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_clean()

