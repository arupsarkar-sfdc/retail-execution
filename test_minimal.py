#!/usr/bin/env python3
"""
Minimal test of SnowflakeManager
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_minimal():
    """Test minimal SnowflakeManager functionality"""
    try:
        print("Testing minimal SnowflakeManager...")
        
        # Import the class
        from pmi_retail.database.snowflake.connection import SnowflakeManager
        
        print("✅ Successfully imported SnowflakeManager")
        
        # Create instance
        sf = SnowflakeManager()
        print("✅ Successfully created SnowflakeManager instance")
        
        # Try to connect
        print("Attempting to connect...")
        result = sf.connect()
        print(f"Connect result: {result}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_minimal()
