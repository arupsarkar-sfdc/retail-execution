"""
Account Data Aggregator
Aggregates all account-related data from multiple Snowflake tables for AI processing
"""

import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

try:
    from pmi_retail.database.snowflake.connection import SnowflakeManager
    from pmi_retail.config import settings
except ImportError as e:
    print(f"Error: Cannot import required modules: {e}")
    print("Make sure you're running from the project root and dependencies are installed.")

logger = logging.getLogger(__name__)


class AccountDataAggregator:
    """Aggregates comprehensive account data from multiple Snowflake tables"""
    
    def __init__(self, snowflake_manager: Optional[SnowflakeManager] = None):
        """
        Initialize Account Data Aggregator
        
        Args:
            snowflake_manager: Optional SnowflakeManager instance
        """
        self.sf = snowflake_manager or SnowflakeManager()
        self.is_connected = False
        
    def connect(self) -> bool:
        """Connect to Snowflake database"""
        try:
            self.is_connected = self.sf.connect()
            if self.is_connected:
                logger.info("✅ Connected to Snowflake for account data aggregation")
            return self.is_connected
        except Exception as e:
            logger.error(f"❌ Failed to connect to Snowflake: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from Snowflake database"""
        if self.is_connected:
            self.sf.close_connection()
            self.is_connected = False
            logger.info("🔐 Disconnected from Snowflake")
    
    def get_account_summary_data(self, account_id: str) -> Dict[str, Any]:
        """
        Get comprehensive account data for AI summary generation
        
        Args:
            account_id: Account ID to fetch data for
            
        Returns:
            Dictionary containing all account-related data
        """
        if not self.is_connected:
            if not self.connect():
                raise ConnectionError("Cannot connect to Snowflake database")
        
        try:
            logger.info(f"📊 Aggregating data for account: {account_id}")
            
            # Fetch all account-related data
            account_data = {
                'account_id': account_id,
                'account_details': self.get_account_details(account_id),
                'contacts': self.get_account_contacts(account_id),
                'notes': self.get_account_notes(account_id),
                'transactions': self.get_account_transactions(account_id),
                'campaigns': self.get_account_campaigns(account_id),
                'aggregated_at': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Successfully aggregated data for account: {account_id}")
            return account_data
            
        except Exception as e:
            logger.error(f"❌ Error aggregating data for account {account_id}: {str(e)}")
            raise
    
    def get_account_details(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get basic account information"""
        try:
            query = """
            SELECT 
                ACCOUNT_ID,
                ACCOUNT_NAME,
                PARENT_ACCOUNT_ID,
                ACCOUNT_TYPE,
                SEGMENT,
                ADDRESS,
                CITY,
                STATE,
                ZIP_CODE,
                COUNTRY,
                PHONE,
                EMAIL,
                REGISTRATION_DATE,
                STATUS,
                HIERARCHY_LEVEL,
                ANNUAL_REVENUE,
                EMPLOYEE_COUNT,
                ENTERPRISE_ID,
                CREATED_TIMESTAMP,
                UPDATED_TIMESTAMP
            FROM ACCOUNTS 
            WHERE ACCOUNT_ID = %s
            """
            
            result = self.sf.execute_query(query, params=[account_id], return_df=False)
            
            if result and len(result) > 0:
                row = result[0]
                return {
                    'account_id': row[0],
                    'account_name': row[1],
                    'parent_account_id': row[2],
                    'account_type': row[3],
                    'segment': row[4],
                    'address': row[5],
                    'city': row[6],
                    'state': row[7],
                    'zip_code': row[8],
                    'country': row[9],
                    'phone': row[10],
                    'email': row[11],
                    'registration_date': row[12],
                    'status': row[13],
                    'hierarchy_level': row[14],
                    'annual_revenue': float(row[15]) if row[15] else 0.0,
                    'employee_count': row[16],
                    'enterprise_id': row[17],
                    'created_timestamp': row[18],
                    'updated_timestamp': row[19]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error fetching account details for {account_id}: {str(e)}")
            return None
    
    def get_account_contacts(self, account_id: str) -> List[Dict[str, Any]]:
        """Get all contacts associated with the account"""
        try:
            query = """
            SELECT 
                CONTACT_ID,
                FIRST_NAME,
                LAST_NAME,
                EMAIL,
                PHONE,
                MOBILE_PHONE,
                CONTACT_TYPE,
                JOB_TITLE,
                DEPARTMENT,
                STATUS,
                CREATED_TIMESTAMP
            FROM CONTACTS 
            WHERE ACCOUNT_ID = %s
            ORDER BY CREATED_TIMESTAMP DESC
            """
            
            result = self.sf.execute_query(query, params=[account_id], return_df=False)
            
            contacts = []
            if result:
                for row in result:
                    contacts.append({
                        'contact_id': row[0],
                        'first_name': row[1],
                        'last_name': row[2],
                        'email': row[3],
                        'phone': row[4],
                        'mobile_phone': row[5],
                        'contact_type': row[6],
                        'job_title': row[7],
                        'department': row[8],
                        'status': row[9],
                        'created_timestamp': row[10]
                    })
            
            logger.info(f"Found {len(contacts)} contacts for account {account_id}")
            return contacts
            
        except Exception as e:
            logger.error(f"Error fetching contacts for account {account_id}: {str(e)}")
            return []
    
    def get_account_notes(self, account_id: str) -> List[Dict[str, Any]]:
        """Get all notes related to the account"""
        try:
            query = """
            SELECT 
                NOTE_ID,
                NOTE_TYPE,
                NOTE_CATEGORY,
                NOTE_PRIORITY,
                NOTE_STATUS,
                SUBJECT,
                NOTE_TEXT,
                CONTACT_ID,
                ACCOUNT_ID,
                ASSIGNED_TO,
                DUE_DATE,
                RESOLUTION_DATE,
                EFFECTIVE_START_DATE,
                EFFECTIVE_END_DATE,
                IS_PRIVATE,
                TAGS,
                CREATED_BY,
                CREATED_TIMESTAMP,
                UPDATED_TIMESTAMP
            FROM NOTES 
            WHERE ACCOUNT_ID = %s
            ORDER BY CREATED_TIMESTAMP DESC
            """
            
            result = self.sf.execute_query(query, params=[account_id], return_df=False)
            
            notes = []
            if result:
                for row in result:
                    notes.append({
                        'note_id': row[0],
                        'note_type': row[1],
                        'note_category': row[2],
                        'note_priority': row[3],
                        'note_status': row[4],
                        'subject': row[5],
                        'note_text': row[6],
                        'contact_id': row[7],
                        'account_id': row[8],
                        'assigned_to': row[9],
                        'due_date': row[10],
                        'resolution_date': row[11],
                        'effective_start_date': row[12],
                        'effective_end_date': row[13],
                        'is_private': row[14],
                        'tags': row[15],
                        'created_by': row[16],
                        'created_timestamp': row[17],
                        'updated_timestamp': row[18]
                    })
            
            logger.info(f"Found {len(notes)} notes for account {account_id}")
            return notes
            
        except Exception as e:
            logger.error(f"Error fetching notes for account {account_id}: {str(e)}")
            return []
    
    def get_account_transactions(self, account_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent transactions for the account"""
        try:
            query = """
            SELECT 
                t.TRANSACTION_ID,
                t.ACCOUNT_ID,
                t.CONTACT_ID,
                t.PRODUCT_ID,
                t.CAMPAIGN_ID,
                t.TRANSACTION_DATE,
                t.QUANTITY,
                t.UNIT_PRICE,
                t.TOTAL_AMOUNT,
                t.DISCOUNT_AMOUNT,
                t.NET_AMOUNT,
                t.SALES_REP,
                t.ORDER_SOURCE,
                p.PRODUCT_NAME,
                p.CATEGORY,
                p.BRAND
            FROM TRANSACTIONS t
            LEFT JOIN PRODUCTS p ON t.PRODUCT_ID = p.PRODUCT_ID
            WHERE t.ACCOUNT_ID = %s
            ORDER BY t.TRANSACTION_DATE DESC
            LIMIT %s
            """
            
            result = self.sf.execute_query(query, params=[account_id, limit], return_df=False)
            
            transactions = []
            if result:
                for row in result:
                    transactions.append({
                        'transaction_id': row[0],
                        'account_id': row[1],
                        'contact_id': row[2],
                        'product_id': row[3],
                        'campaign_id': row[4],
                        'transaction_date': row[5],
                        'quantity': row[6],
                        'unit_price': float(row[7]) if row[7] else 0.0,
                        'total_amount': float(row[8]) if row[8] else 0.0,
                        'discount_amount': float(row[9]) if row[9] else 0.0,
                        'net_amount': float(row[10]) if row[10] else 0.0,
                        'sales_rep': row[11],
                        'order_source': row[12],
                        'product_name': row[13],
                        'product_category': row[14],
                        'product_brand': row[15]
                    })
            
            logger.info(f"Found {len(transactions)} transactions for account {account_id}")
            return transactions
            
        except Exception as e:
            logger.error(f"Error fetching transactions for account {account_id}: {str(e)}")
            return []
    
    def get_account_campaigns(self, account_id: str) -> List[Dict[str, Any]]:
        """Get campaigns associated with the account"""
        try:
            query = """
            SELECT DISTINCT
                c.CAMPAIGN_ID,
                c.CAMPAIGN_NAME,
                c.CAMPAIGN_TYPE,
                c.STATUS,
                c.START_DATE,
                c.END_DATE,
                c.BUDGET,
                c.TARGET_SEGMENT
            FROM CAMPAIGNS c
            INNER JOIN TRANSACTIONS t ON c.CAMPAIGN_ID = t.CAMPAIGN_ID
            WHERE t.ACCOUNT_ID = %s
            ORDER BY c.START_DATE DESC
            """
            
            result = self.sf.execute_query(query, params=[account_id], return_df=False)
            
            campaigns = []
            if result:
                for row in result:
                    campaigns.append({
                        'campaign_id': row[0],
                        'campaign_name': row[1],
                        'campaign_type': row[2],
                        'status': row[3],
                        'start_date': row[4],
                        'end_date': row[5],
                        'budget': float(row[6]) if row[6] else 0.0,
                        'target_segment': row[7]
                    })
            
            logger.info(f"Found {len(campaigns)} campaigns for account {account_id}")
            return campaigns
            
        except Exception as e:
            logger.error(f"Error fetching campaigns for account {account_id}: {str(e)}")
            return []
    
    def get_account_list(self) -> List[str]:
        """Get list of all account IDs for selection"""
        try:
            query = """
            SELECT ACCOUNT_ID, ACCOUNT_NAME, ACCOUNT_TYPE, SEGMENT
            FROM ACCOUNTS 
            WHERE STATUS = 'Active'
            ORDER BY ACCOUNT_NAME
            """
            
            result = self.sf.execute_query(query, return_df=False)
            
            accounts = []
            if result:
                for row in result:
                    accounts.append({
                        'account_id': row[0],
                        'account_name': row[1],
                        'account_type': row[2],
                        'segment': row[3]
                    })
            
            logger.info(f"Found {len(accounts)} active accounts")
            return accounts
            
        except Exception as e:
            logger.error(f"Error fetching account list: {str(e)}")
            return []
    
    def validate_account_id(self, account_id: str) -> bool:
        """Validate if account ID exists and is active"""
        try:
            query = """
            SELECT COUNT(*) 
            FROM ACCOUNTS 
            WHERE ACCOUNT_ID = %s AND STATUS = 'Active'
            """
            
            result = self.sf.execute_query(query, params=[account_id], return_df=False)
            
            if result and len(result) > 0:
                count = result[0][0]
                return count > 0
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating account ID {account_id}: {str(e)}")
            return False
