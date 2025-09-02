"""
Snowflake Connection Manager for PMI Workshop
Handles all Snowflake database connections and operations
"""

import snowflake.connector
import pandas as pd
from typing import Optional, List, Dict, Any, Union
from contextlib import contextmanager
from loguru import logger
import sys
from pathlib import Path

from ...config import settings


class SnowflakeManager:
    """
    Manages Snowflake connections and operations for PMI Workshop
    
    Features:
    - Automatic connection management
    - Query execution with error handling
    - DataFrame integration
    - Transaction support
    - Connection pooling ready
    """
    
    def __init__(self):
        self.connection: Optional[snowflake.connector.SnowflakeConnection] = None
        self.cursor: Optional[snowflake.connector.cursor.SnowflakeCursor] = None
        self._connected = False
        
        # Configure logging
        logger.add("logs/snowflake.log", rotation="10 MB", level="INFO")
    
    def connect(self) -> bool:
        """
        Establish connection to Snowflake using settings from config
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info("Attempting to connect to Snowflake...")
            
            connection_params = {
                'user': settings.snowflake_user,
                'password': settings.snowflake_password,
                'account': settings.snowflake_account,
                'warehouse': settings.snowflake_warehouse,
                'database': settings.snowflake_database,
                'schema': settings.snowflake_schema,
                'role': settings.snowflake_role
            }
            
            # Remove empty parameters
            connection_params = {k: v for k, v in connection_params.items() if v}
            
            self.connection = snowflake.connector.connect(**connection_params)
            self.cursor = self.connection.cursor()
            self._connected = True
            
            # Test connection with a simple query
            test_result = self.execute_query("SELECT CURRENT_VERSION()", return_df=False)
            logger.info(f"✅ Connected to Snowflake successfully. Version: {test_result[0][0] if test_result else 'Unknown'}")
            
            # Log connection details (without sensitive info)
            logger.info(f"Connected to: {settings.snowflake_database}.{settings.snowflake_schema}")
            logger.info(f"Using warehouse: {settings.snowflake_warehouse}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Snowflake: {str(e)}")
            self._connected = False
            return False
    
    def is_connected(self) -> bool:
        """Check if connection is active"""
        return self._connected and self.connection is not None
    
    def execute_query(self, query: str, params: Optional[Dict] = None, 
                     return_df: bool = True) -> Union[pd.DataFrame, List[tuple], None]:
        """
        Execute a SELECT query and return results
        
        Args:
            query: SQL query string
            params: Query parameters (for prepared statements)
            return_df: If True, return pandas DataFrame; if False, return raw results
            
        Returns:
            DataFrame, list of tuples, or None if error
        """
        if not self.is_connected():
            logger.error("Not connected to Snowflake")
            return None
        
        try:
            logger.debug(f"Executing query: {query[:100]}..." if len(query) > 100 else f"Executing query: {query}")
            
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            if return_df:
                # Get column names
                columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
                
                # Fetch all results
                results = self.cursor.fetchall()
                
                # Return as DataFrame
                df = pd.DataFrame(results, columns=columns)
                logger.info(f"Query executed successfully. Returned {len(df)} rows.")
                return df
            else:
                results = self.cursor.fetchall()
                logger.info(f"Query executed successfully. Returned {len(results)} rows.")
                return results
                
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            logger.error(f"Failed query: {query}")
            return None
    
    def execute_sql(self, sql: str, params: Optional[Dict] = None) -> bool:
        """
        Execute SQL commands (CREATE, INSERT, UPDATE, DELETE, etc.)
        
        Args:
            sql: SQL command string
            params: Query parameters
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to Snowflake")
            return False
        
        try:
            logger.debug(f"Executing SQL: {sql[:100]}..." if len(sql) > 100 else f"Executing SQL: {sql}")
            
            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)
            
            # Get number of affected rows if available
            rowcount = getattr(self.cursor, 'rowcount', 0)
            logger.info(f"✅ SQL executed successfully. Affected rows: {rowcount}")
            return True
            
        except Exception as e:
            logger.error(f"❌ SQL execution failed: {str(e)}")
            logger.error(f"Failed SQL: {sql}")
            return False
    
    def execute_many(self, sql: str, data: List[Dict]) -> bool:
        """
        Execute SQL with multiple parameter sets (batch insert/update)
        
        Args:
            sql: SQL command with parameter placeholders
            data: List of parameter dictionaries
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to Snowflake")
            return False
        
        try:
            logger.info(f"Executing batch SQL with {len(data)} parameter sets...")
            self.cursor.executemany(sql, data)
            
            rowcount = getattr(self.cursor, 'rowcount', len(data))
            logger.info(f"✅ Batch SQL executed successfully. Affected rows: {rowcount}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Batch SQL execution failed: {str(e)}")
            return False
    
    def load_dataframe(self, df: pd.DataFrame, table_name: str, 
                      if_exists: str = 'append', method: str = 'multi') -> bool:
        """
        Load pandas DataFrame to Snowflake table
        
        Args:
            df: DataFrame to load
            table_name: Target table name
            if_exists: What to do if table exists ('fail', 'replace', 'append')
            method: Load method ('multi' for batch insert)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to Snowflake")
            return False
        
        try:
            logger.info(f"Loading DataFrame to table {table_name}. Shape: {df.shape}")
            
            # Note: Direct pandas to_sql with Snowflake requires sqlalchemy
            # For now, we'll use INSERT statements
            
            if if_exists == 'replace' and self.table_exists(table_name):
                self.execute_sql(f"TRUNCATE TABLE {table_name}")
            
            # Convert DataFrame to INSERT statements
            success = self._insert_dataframe_batch(df, table_name)
            
            if success:
                logger.info(f"✅ DataFrame loaded successfully to {table_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ DataFrame load failed: {str(e)}")
            return False
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        query = f"""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = '{settings.snowflake_schema}' 
        AND TABLE_NAME = '{table_name.upper()}'
        """
        result = self.execute_query(query, return_df=False)
        return result[0][0] > 0 if result else False
    
    def get_table_info(self, table_name: str) -> Optional[pd.DataFrame]:
        """Get table schema information"""
        query = f"DESCRIBE TABLE {table_name}"
        return self.execute_query(query)
    
    def _insert_dataframe_batch(self, df: pd.DataFrame, table_name: str) -> bool:
        """Helper method to batch insert DataFrame data"""
        try:
            # Get column names
            columns = df.columns.tolist()
            placeholders = ', '.join(['%s'] * len(columns))
            columns_str = ', '.join(columns)
            
            sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
            
            # Convert DataFrame to list of tuples
            data = [tuple(row) for row in df.values]
            
            # Execute in batches
            batch_size = 1000
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                self.cursor.executemany(sql, batch)
            
            return True
            
        except Exception as e:
            logger.error(f"Batch insert failed: {str(e)}")
            return False
    
    @contextmanager
    def transaction(self):
        """Context manager for transactions"""
        if not self.is_connected():
            raise Exception("Not connected to Snowflake")
        
        try:
            self.connection.autocommit(False)
            logger.info("🔄 Transaction started")
            yield self
            self.connection.commit()
            logger.info("✅ Transaction committed")
        except Exception as e:
            self.connection.rollback()
            logger.error(f"❌ Transaction rolled back: {str(e)}")
            raise
        finally:
            self.connection.autocommit(True)
    
    def close_connection(self):
        """Close Snowflake connection"""
        try:
            if self.cursor:
                self.cursor.close()
                logger.debug("Cursor closed")
            
            if self.connection:
                self.connection.close()
                logger.info("🔐 Snowflake connection closed")
            
            self._connected = False
            
        except Exception as e:
            logger.error(f"Error closing connection: {str(e)}")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close_connection()
    
    def __del__(self):
        """Destructor - ensure connection is closed"""
        if self._connected:
            self.close_connection()


# Convenience function for quick connections
def get_snowflake_connection() -> SnowflakeManager:
    """Get a connected SnowflakeManager instance"""
    sf = SnowflakeManager()
    if sf.connect():
        return sf
    else:
        raise ConnectionError("Failed to establish Snowflake connection")


# Usage examples and testing
if __name__ == "__main__":
    # Test the connection
    print("🧪 Testing Snowflake Connection...")
    
    try:
        with SnowflakeManager() as sf:
            # Test basic query
            version_df = sf.execute_query("SELECT CURRENT_VERSION() as VERSION, CURRENT_USER() as USER")
            print("📊 Connection Test Results:")
            print(version_df)
            
            # Test database info
            tables_df = sf.execute_query("""
                SELECT TABLE_NAME, TABLE_TYPE 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s
            """, {'1': settings.snowflake_schema})
            
            print(f"\n📋 Existing tables in {settings.snowflake_schema}:")
            print(tables_df if len(tables_df) > 0 else "No tables found")
            
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        print(f"❌ Connection test failed: {str(e)}")