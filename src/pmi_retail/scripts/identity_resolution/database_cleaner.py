"""
Database Cleaner for Identity Resolution Testing
Safely cleans existing data from Snowflake tables before inserting new test data
"""

import sys
from pathlib import Path
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from pmi_retail.database.snowflake.connection import SnowflakeManager
from pmi_retail.config import settings


class DatabaseCleaner:
    """
    Safely cleans existing data from Snowflake tables
    """
    
    def __init__(self):
        self.sf = SnowflakeManager()
        
        # Tables to clean in order (respecting foreign key dependencies)
        self.tables_to_clean = [
            'LOYALTY_MEMBERS',
            'TRANSACTIONS', 
            'NOTES',
            'CONTACTS',
            'ACCOUNTS',
            'CAMPAIGNS',
            'PRODUCTS',
            'DATA_QUALITY_RULES'
        ]
    
    def connect(self) -> bool:
        """Connect to Snowflake"""
        return self.sf.connect()
    
    def clean_all_tables(self, confirm: bool = False) -> bool:
        """
        Clean all tables in the correct order
        
        Args:
            confirm: If True, skip confirmation prompt
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not confirm:
            print("\n⚠️  WARNING: This will DELETE ALL DATA from the following tables:")
            for table in self.tables_to_clean:
                print(f"   - {table}")
            
            response = input("\nAre you sure you want to continue? (yes/no): ").lower().strip()
            if response not in ['yes', 'y']:
                print("❌ Operation cancelled by user")
                return False
        
        logger.info("🧹 Starting database cleanup...")
        
        try:
            # Connect to Snowflake
            if not self.connect():
                logger.error("Failed to connect to Snowflake")
                return False
            
            # Clean each table
            for table_name in self.tables_to_clean:
                if not self.clean_table(table_name):
                    logger.error(f"Failed to clean table {table_name}")
                    return False
            
            logger.info("✅ Database cleanup completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database cleanup failed: {str(e)}")
            return False
        finally:
            self.sf.close_connection()
    
    def clean_table(self, table_name: str) -> bool:
        """
        Clean a specific table
        
        Args:
            table_name: Name of the table to clean
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if table exists
            if not self.sf.table_exists(table_name):
                logger.info(f"Table {table_name} does not exist, skipping...")
                return True
            
            # Get row count before deletion
            count_query = f"SELECT COUNT(*) as ROW_COUNT FROM {table_name}"
            result = self.sf.execute_query(count_query, return_df=False)
            row_count = result[0][0] if result else 0
            
            if row_count == 0:
                logger.info(f"Table {table_name} is already empty")
                return True
            
            # Delete all rows
            delete_sql = f"DELETE FROM {table_name}"
            if self.sf.execute_sql(delete_sql):
                logger.info(f"✅ Cleaned table {table_name}: {row_count:,} rows deleted")
                return True
            else:
                logger.error(f"❌ Failed to clean table {table_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to clean table {table_name}: {str(e)}")
            return False
    
    def clean_specific_tables(self, table_names: list, confirm: bool = False) -> bool:
        """
        Clean specific tables only
        
        Args:
            table_names: List of table names to clean
            confirm: If True, skip confirmation prompt
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not confirm:
            print(f"\n⚠️  WARNING: This will DELETE ALL DATA from the following tables:")
            for table in table_names:
                print(f"   - {table}")
            
            response = input("\nAre you sure you want to continue? (yes/no): ").lower().strip()
            if response not in ['yes', 'y']:
                print("❌ Operation cancelled by user")
                return False
        
        logger.info(f"🧹 Starting cleanup of specific tables: {', '.join(table_names)}")
        
        try:
            # Connect to Snowflake
            if not self.connect():
                logger.error("Failed to connect to Snowflake")
                return False
            
            # Clean each specified table
            for table_name in table_names:
                if not self.clean_table(table_name):
                    logger.error(f"Failed to clean table {table_name}")
                    return False
            
            logger.info("✅ Specific table cleanup completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Specific table cleanup failed: {str(e)}")
            return False
        finally:
            self.sf.close_connection()
    
    def get_table_row_counts(self) -> dict:
        """
        Get row counts for all tables
        
        Returns:
            dict: Dictionary with table names and row counts
        """
        try:
            if not self.connect():
                logger.error("Failed to connect to Snowflake")
                return {}
            
            row_counts = {}
            
            for table_name in self.tables_to_clean:
                if self.sf.table_exists(table_name):
                    count_query = f"SELECT COUNT(*) as ROW_COUNT FROM {table_name}"
                    result = self.sf.execute_query(count_query, return_df=False)
                    row_count = result[0][0] if result else 0
                    row_counts[table_name] = row_count
                else:
                    row_counts[table_name] = "Table does not exist"
            
            return row_counts
            
        except Exception as e:
            logger.error(f"Failed to get table row counts: {str(e)}")
            return {}
        finally:
            self.sf.close_connection()
    
    def print_table_status(self):
        """Print current status of all tables"""
        print("\n" + "="*60)
        print("📊 CURRENT TABLE STATUS")
        print("="*60)
        
        row_counts = self.get_table_row_counts()
        
        for table_name, count in row_counts.items():
            if isinstance(count, int):
                print(f"{table_name:<25} | {count:>8,} rows")
            else:
                print(f"{table_name:<25} | {count}")
        
        print("="*60)


def main():
    """Main function for database cleaning"""
    print("🧹 PMI Workshop - Database Cleaner")
    print("="*50)
    
    cleaner = DatabaseCleaner()
    
    try:
        # Show current status
        cleaner.print_table_status()
        
        # Ask user what they want to do
        print("\nOptions:")
        print("1. Clean all tables")
        print("2. Clean specific tables")
        print("3. Show table status only")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            success = cleaner.clean_all_tables()
            if success:
                print("\n✅ All tables cleaned successfully!")
                cleaner.print_table_status()
            else:
                print("\n❌ Table cleaning failed!")
                
        elif choice == '2':
            print("\nAvailable tables:")
            for i, table in enumerate(cleaner.tables_to_clean, 1):
                print(f"{i}. {table}")
            
            table_input = input("\nEnter table numbers (comma-separated) or table names: ").strip()
            
            # Parse input
            if table_input.replace(',', '').replace(' ', '').isdigit():
                # Numbers provided
                indices = [int(x.strip()) - 1 for x in table_input.split(',')]
                selected_tables = [cleaner.tables_to_clean[i] for i in indices if 0 <= i < len(cleaner.tables_to_clean)]
            else:
                # Table names provided
                selected_tables = [x.strip() for x in table_input.split(',')]
            
            if selected_tables:
                success = cleaner.clean_specific_tables(selected_tables)
                if success:
                    print(f"\n✅ Tables {', '.join(selected_tables)} cleaned successfully!")
                    cleaner.print_table_status()
                else:
                    print("\n❌ Table cleaning failed!")
            else:
                print("❌ No valid tables selected!")
                
        elif choice == '3':
            print("\n📊 Current table status:")
            cleaner.print_table_status()
            
        elif choice == '4':
            print("👋 Goodbye!")
            
        else:
            print("❌ Invalid choice!")
            
    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user")
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        print(f"\n❌ Script failed: {str(e)}")


if __name__ == "__main__":
    main()
