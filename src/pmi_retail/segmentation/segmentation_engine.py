"""
Real-Time Customer Segmentation & Propensity Scoring Engine
Leverages existing Snowflake data to provide dynamic account segmentation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger
import sys
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
import joblib

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from pmi_retail.database.snowflake.connection import SnowflakeManager


class RealTimeSegmentationEngine:
    """
    Advanced customer segmentation engine using RFM analysis, 
    behavioral patterns, and propensity scoring
    """
    
    def __init__(self, sf_manager: SnowflakeManager):
        self.sf = sf_manager
        self.scaler = StandardScaler()
        self.kmeans_model = None
        self.propensity_models = {}
        
        # Segmentation configuration
        self.segment_definitions = {
            'Champions': {'description': 'High value, recent, frequent customers', 'priority': 1},
            'Loyal Customers': {'description': 'Regular customers with consistent purchase patterns', 'priority': 2},
            'Potential Loyalists': {'description': 'Recent customers with good potential', 'priority': 3},
            'New Customers': {'description': 'Recent first-time customers', 'priority': 4},
            'Promising': {'description': 'High value but infrequent customers', 'priority': 5},
            'Need Attention': {'description': 'Good customers at risk of churning', 'priority': 6},
            'About to Sleep': {'description': 'Declining engagement, intervention needed', 'priority': 7},
            'At Risk': {'description': 'High value customers showing churn signals', 'priority': 8},
            'Cannot Lose Them': {'description': 'High value customers with very low recent activity', 'priority': 9},
            'Hibernating': {'description': 'Low value customers with no recent activity', 'priority': 10}
        }
    
    def calculate_account_rfm_scores(self, lookback_days: int = 365) -> pd.DataFrame:
        """
        Calculate RFM (Recency, Frequency, Monetary) scores for all accounts
        
        Args:
            lookback_days: Number of days to look back for transaction analysis
            
        Returns:
            DataFrame with RFM scores for each account
        """
        logger.info(f"Calculating RFM scores for last {lookback_days} days...")
        
        # Complex query to calculate RFM metrics
        rfm_query = f"""
        WITH account_transactions AS (
            SELECT 
                a.ACCOUNT_ID,
                a.ACCOUNT_NAME,
                a.ACCOUNT_TYPE,
                a.SEGMENT as CURRENT_SEGMENT,
                a.HIERARCHY_LEVEL,
                a.ANNUAL_REVENUE,
                t.TRANSACTION_DATE,
                t.NET_AMOUNT,
                t.QUANTITY
            FROM ACCOUNTS a
            LEFT JOIN TRANSACTIONS t ON a.ACCOUNT_ID = t.ACCOUNT_ID
            WHERE t.TRANSACTION_DATE >= DATEADD(day, -{lookback_days}, CURRENT_DATE())
               OR t.TRANSACTION_DATE IS NULL
        ),
        rfm_metrics AS (
            SELECT 
                ACCOUNT_ID,
                ACCOUNT_NAME,
                ACCOUNT_TYPE,
                CURRENT_SEGMENT,
                HIERARCHY_LEVEL,
                ANNUAL_REVENUE,
                -- Recency: Days since last purchase
                CASE 
                    WHEN MAX(TRANSACTION_DATE) IS NULL THEN 999
                    ELSE DATEDIFF(day, MAX(TRANSACTION_DATE), CURRENT_DATE())
                END as RECENCY_DAYS,
                
                -- Frequency: Number of purchase occasions
                COUNT(DISTINCT TRANSACTION_DATE) as FREQUENCY,
                
                -- Monetary: Total spend amount
                COALESCE(SUM(NET_AMOUNT), 0) as MONETARY_VALUE,
                
                -- Additional metrics
                COALESCE(AVG(NET_AMOUNT), 0) as AVG_ORDER_VALUE,
                COALESCE(SUM(QUANTITY), 0) as TOTAL_QUANTITY,
                COUNT(TRANSACTION_DATE) as TOTAL_TRANSACTIONS
            FROM account_transactions
            GROUP BY ACCOUNT_ID, ACCOUNT_NAME, ACCOUNT_TYPE, CURRENT_SEGMENT, HIERARCHY_LEVEL, ANNUAL_REVENUE
        )
        SELECT * FROM rfm_metrics
        ORDER BY MONETARY_VALUE DESC
        """
        
        try:
            rfm_df = self.sf.execute_query(rfm_query)
            logger.info(f"Calculated RFM scores for {len(rfm_df)} accounts")
            return rfm_df
        except Exception as e:
            logger.error(f"Failed to calculate RFM scores: {str(e)}")
            return pd.DataFrame()
    
    def calculate_rfm_quintiles(self, rfm_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate RFM quintiles and scores (1-5 scale)
        """
        logger.info("Calculating RFM quintiles...")
        
        # Create copy to avoid modifying original
        df = rfm_df.copy()
        
        # Calculate quintiles (1 = worst, 5 = best)
        # For Recency: lower is better (more recent)
        df['R_QUINTILE'] = pd.qcut(df['RECENCY_DAYS'].rank(method='first'), 
                                   q=5, labels=[5, 4, 3, 2, 1])
        
        # For Frequency: higher is better
        df['F_QUINTILE'] = pd.qcut(df['FREQUENCY'].rank(method='first'), 
                                   q=5, labels=[1, 2, 3, 4, 5])
        
        # For Monetary: higher is better
        df['M_QUINTILE'] = pd.qcut(df['MONETARY_VALUE'].rank(method='first'), 
                                   q=5, labels=[1, 2, 3, 4, 5])
        
        # Convert to numeric
        df['R_QUINTILE'] = df['R_QUINTILE'].astype(int)
        df['F_QUINTILE'] = df['F_QUINTILE'].astype(int)
        df['M_QUINTILE'] = df['M_QUINTILE'].astype(int)
        
        # Create combined RFM score
        df['RFM_SCORE'] = df['R_QUINTILE'].astype(str) + \
                          df['F_QUINTILE'].astype(str) + \
                          df['M_QUINTILE'].astype(str)
        
        # Calculate overall score (simple average for now)
        df['RFM_SCORE_NUMERIC'] = (df['R_QUINTILE'] + df['F_QUINTILE'] + df['M_QUINTILE']) / 3
        
        logger.info("RFM quintiles calculated successfully")
        return df
    
    def assign_behavioral_segments(self, rfm_df: pd.DataFrame) -> pd.DataFrame:
        """
        Assign behavioral segments based on RFM quintiles using business rules
        """
        logger.info("Assigning behavioral segments...")
        
        df = rfm_df.copy()
        
        def get_segment(row):
            r, f, m = row['R_QUINTILE'], row['F_QUINTILE'], row['M_QUINTILE']
            
            # Champions: High value, frequent, recent customers
            if r >= 4 and f >= 4 and m >= 4:
                return 'Champions'
            
            # Loyal Customers: Regular customers, not necessarily high spenders
            elif r >= 3 and f >= 4 and m >= 3:
                return 'Loyal Customers'
            
            # Potential Loyalists: Recent customers with good frequency or value
            elif r >= 4 and (f >= 3 or m >= 3):
                return 'Potential Loyalists'
            
            # New Customers: Recent customers with low frequency
            elif r >= 4 and f <= 2:
                return 'New Customers'
            
            # Promising: High value but not frequent or recent
            elif m >= 4 and (r <= 3 or f <= 3):
                return 'Promising'
            
            # Need Attention: Moderate customers with declining recency
            elif r == 3 and f >= 3 and m >= 3:
                return 'Need Attention'
            
            # About to Sleep: Declining in all metrics
            elif r <= 2 and f >= 2 and m >= 2:
                return 'About to Sleep'
            
            # At Risk: High value customers with low recent activity
            elif m >= 4 and r <= 2:
                return 'At Risk'
            
            # Cannot Lose Them: Highest value customers with very low recency
            elif m == 5 and r == 1:
                return 'Cannot Lose Them'
            
            # Hibernating: Low value, low frequency, low recency
            else:
                return 'Hibernating'
        
        df['BEHAVIORAL_SEGMENT'] = df.apply(get_segment, axis=1)
        
        # Add segment metadata
        df['SEGMENT_PRIORITY'] = df['BEHAVIORAL_SEGMENT'].map(
            lambda x: self.segment_definitions[x]['priority']
        )
        df['SEGMENT_DESCRIPTION'] = df['BEHAVIORAL_SEGMENT'].map(
            lambda x: self.segment_definitions[x]['description']
        )
        
        # Log segment distribution
        segment_counts = df['BEHAVIORAL_SEGMENT'].value_counts()
        logger.info("Behavioral segment distribution:")
        for segment, count in segment_counts.items():
            logger.info(f"  {segment}: {count} accounts")
        
        return df
    
    def calculate_engagement_metrics(self, account_ids: List[str] = None) -> pd.DataFrame:
        """
        Calculate additional engagement metrics for accounts
        """
        logger.info("Calculating engagement metrics...")
        
        # Filter accounts if specified
        account_filter = ""
        if account_ids:
            account_list = "', '".join(account_ids)
            account_filter = f"AND a.ACCOUNT_ID IN ('{account_list}')"
        
        engagement_query = f"""
        WITH engagement_metrics AS (
            SELECT 
                a.ACCOUNT_ID,
                a.ACCOUNT_NAME,
                
                -- Campaign engagement
                COUNT(DISTINCT t.CAMPAIGN_ID) as CAMPAIGNS_RESPONDED,
                
                -- Loyalty program engagement  
                CASE WHEN lm.MEMBER_ID IS NOT NULL THEN 1 ELSE 0 END as IS_LOYALTY_MEMBER,
                COALESCE(lm.LOYALTY_TIER, 'None') as LOYALTY_TIER,
                COALESCE(lm.POINTS_BALANCE, 0) as LOYALTY_POINTS,
                
                -- Product diversity
                COUNT(DISTINCT p.CATEGORY) as PRODUCT_CATEGORIES_PURCHASED,
                COUNT(DISTINCT p.BRAND) as BRANDS_PURCHASED,
                
                -- Seasonal engagement (last 90 days vs previous 90 days)
                SUM(CASE WHEN t.TRANSACTION_DATE >= DATEADD(day, -90, CURRENT_DATE()) 
                         THEN t.NET_AMOUNT ELSE 0 END) as RECENT_90_DAYS_SPEND,
                SUM(CASE WHEN t.TRANSACTION_DATE BETWEEN DATEADD(day, -180, CURRENT_DATE()) 
                                                      AND DATEADD(day, -90, CURRENT_DATE())
                         THEN t.NET_AMOUNT ELSE 0 END) as PREVIOUS_90_DAYS_SPEND,
                
                -- Channel diversity
                COUNT(DISTINCT t.ORDER_SOURCE) as CHANNELS_USED,
                
                -- Notes and interactions
                COALESCE(note_counts.TOTAL_NOTES, 0) as TOTAL_INTERACTION_NOTES,
                COALESCE(note_counts.RECENT_NOTES, 0) as RECENT_INTERACTION_NOTES
                
            FROM ACCOUNTS a
            LEFT JOIN TRANSACTIONS t ON a.ACCOUNT_ID = t.ACCOUNT_ID
            LEFT JOIN PRODUCTS p ON t.PRODUCT_ID = p.PRODUCT_ID
            LEFT JOIN LOYALTY_MEMBERS lm ON a.ACCOUNT_ID = lm.ACCOUNT_ID
            LEFT JOIN (
                SELECT 
                    ACCOUNT_ID,
                    COUNT(*) as TOTAL_NOTES,
                    SUM(CASE WHEN CREATED_TIMESTAMP >= DATEADD(day, -90, CURRENT_DATE()) 
                             THEN 1 ELSE 0 END) as RECENT_NOTES
                FROM NOTES
                WHERE ACCOUNT_ID IS NOT NULL
                GROUP BY ACCOUNT_ID
            ) note_counts ON a.ACCOUNT_ID = note_counts.ACCOUNT_ID
            
            WHERE 1=1 {account_filter}
            GROUP BY a.ACCOUNT_ID, a.ACCOUNT_NAME, lm.MEMBER_ID, lm.LOYALTY_TIER, 
                     lm.POINTS_BALANCE, note_counts.TOTAL_NOTES, note_counts.RECENT_NOTES
        )
        SELECT *,
               -- Calculate engagement trend
               CASE 
                   WHEN PREVIOUS_90_DAYS_SPEND > 0 THEN 
                       (RECENT_90_DAYS_SPEND - PREVIOUS_90_DAYS_SPEND) / PREVIOUS_90_DAYS_SPEND * 100
                   WHEN RECENT_90_DAYS_SPEND > 0 THEN 100
                   ELSE 0
               END as SPEND_TREND_PERCENTAGE
        FROM engagement_metrics
        ORDER BY RECENT_90_DAYS_SPEND DESC
        """
        
        try:
            engagement_df = self.sf.execute_query(engagement_query)
            logger.info(f"Calculated engagement metrics for {len(engagement_df)} accounts")
            return engagement_df
        except Exception as e:
            logger.error(f"Failed to calculate engagement metrics: {str(e)}")
            return pd.DataFrame()
    
    def calculate_product_propensity_scores(self, account_ids: List[str] = None) -> pd.DataFrame:
        """
        Calculate propensity scores for product categories and brands
        """
        logger.info("Calculating product propensity scores...")
        
        # Get historical purchase patterns
        account_filter = ""
        if account_ids:
            account_list = "', '".join(account_ids)
            account_filter = f"AND a.ACCOUNT_ID IN ('{account_list}')"
        
        propensity_query = f"""
        WITH purchase_history AS (
            SELECT 
                a.ACCOUNT_ID,
                a.ACCOUNT_NAME,
                a.SEGMENT,
                p.CATEGORY,
                p.BRAND,
                COUNT(*) as PURCHASE_COUNT,
                SUM(t.NET_AMOUNT) as TOTAL_SPEND,
                AVG(t.NET_AMOUNT) as AVG_SPEND,
                MAX(t.TRANSACTION_DATE) as LAST_PURCHASE_DATE,
                DATEDIFF(day, MAX(t.TRANSACTION_DATE), CURRENT_DATE()) as DAYS_SINCE_LAST
            FROM ACCOUNTS a
            JOIN TRANSACTIONS t ON a.ACCOUNT_ID = t.ACCOUNT_ID
            JOIN PRODUCTS p ON t.PRODUCT_ID = p.PRODUCT_ID
            WHERE t.TRANSACTION_DATE >= DATEADD(day, -365, CURRENT_DATE())
              {account_filter}
            GROUP BY a.ACCOUNT_ID, a.ACCOUNT_NAME, a.SEGMENT, p.CATEGORY, p.BRAND
        ),
        category_benchmarks AS (
            SELECT 
                SEGMENT,
                CATEGORY,
                AVG(PURCHASE_COUNT) as SEGMENT_AVG_PURCHASES,
                AVG(TOTAL_SPEND) as SEGMENT_AVG_SPEND,
                PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY PURCHASE_COUNT) as TOP_20_PURCHASES
            FROM purchase_history
            GROUP BY SEGMENT, CATEGORY
        )
        SELECT 
            ph.*,
            cb.SEGMENT_AVG_PURCHASES,
            cb.SEGMENT_AVG_SPEND,
            cb.TOP_20_PURCHASES,
            
            -- Calculate propensity scores (0-100 scale)
            CASE 
                WHEN cb.SEGMENT_AVG_PURCHASES > 0 THEN 
                    LEAST(100, (ph.PURCHASE_COUNT / cb.SEGMENT_AVG_PURCHASES) * 50)
                ELSE 0 
            END as CATEGORY_AFFINITY_SCORE,
            
            -- Recency score (recent purchases get higher score)
            CASE 
                WHEN ph.DAYS_SINCE_LAST <= 30 THEN 100
                WHEN ph.DAYS_SINCE_LAST <= 60 THEN 80
                WHEN ph.DAYS_SINCE_LAST <= 90 THEN 60
                WHEN ph.DAYS_SINCE_LAST <= 180 THEN 40
                ELSE 20
            END as RECENCY_SCORE,
            
            -- Frequency score
            CASE 
                WHEN ph.PURCHASE_COUNT >= cb.TOP_20_PURCHASES THEN 100
                WHEN ph.PURCHASE_COUNT >= cb.SEGMENT_AVG_PURCHASES THEN 70
                WHEN ph.PURCHASE_COUNT >= cb.SEGMENT_AVG_PURCHASES * 0.5 THEN 50
                ELSE 30
            END as FREQUENCY_SCORE
            
        FROM purchase_history ph
        JOIN category_benchmarks cb ON ph.SEGMENT = cb.SEGMENT AND ph.CATEGORY = cb.CATEGORY
        ORDER BY ph.ACCOUNT_ID, ph.TOTAL_SPEND DESC
        """
        
        try:
            propensity_df = self.sf.execute_query(propensity_query)
            
            if len(propensity_df) > 0:
                # Convert decimal columns to float to avoid type conversion issues
                propensity_df['CATEGORY_AFFINITY_SCORE'] = pd.to_numeric(propensity_df['CATEGORY_AFFINITY_SCORE'], errors='coerce')
                propensity_df['RECENCY_SCORE'] = pd.to_numeric(propensity_df['RECENCY_SCORE'], errors='coerce')
                propensity_df['FREQUENCY_SCORE'] = pd.to_numeric(propensity_df['FREQUENCY_SCORE'], errors='coerce')
                
                # Calculate combined propensity score
                propensity_df['PROPENSITY_SCORE'] = (
                    propensity_df['CATEGORY_AFFINITY_SCORE'] * 0.4 +
                    propensity_df['RECENCY_SCORE'] * 0.3 +
                    propensity_df['FREQUENCY_SCORE'] * 0.3
                ).round(2)
                
            logger.info(f"Calculated product propensity scores for {len(propensity_df)} account-product combinations")
            return propensity_df
        except Exception as e:
            logger.error(f"Failed to calculate product propensity scores: {str(e)}")
            return pd.DataFrame()
    
    def generate_comprehensive_segments(self, lookback_days: int = 365) -> Dict[str, pd.DataFrame]:
        """
        Generate comprehensive segmentation analysis combining all metrics
        
        Returns:
            Dictionary containing different segmentation DataFrames
        """
        logger.info("Starting comprehensive segmentation analysis...")
        
        results = {}
        
        try:
            # Step 1: Calculate RFM scores
            rfm_df = self.calculate_account_rfm_scores(lookback_days)
            if len(rfm_df) == 0:
                logger.error("No RFM data available")
                return results
            
            # Step 2: Calculate quintiles and segments
            rfm_with_quintiles = self.calculate_rfm_quintiles(rfm_df)
            segmented_accounts = self.assign_behavioral_segments(rfm_with_quintiles)
            
            # Step 3: Calculate engagement metrics
            engagement_df = self.calculate_engagement_metrics()
            
            # Step 4: Merge RFM and engagement data
            if len(engagement_df) > 0:
                comprehensive_df = segmented_accounts.merge(
                    engagement_df, 
                    on=['ACCOUNT_ID', 'ACCOUNT_NAME'], 
                    how='left'
                )
            else:
                comprehensive_df = segmented_accounts
            
            # Step 5: Calculate product propensity scores
            propensity_df = self.calculate_product_propensity_scores()
            
            # Store results
            results['rfm_analysis'] = comprehensive_df
            results['product_propensity'] = propensity_df
            results['segment_summary'] = self._create_segment_summary(comprehensive_df)
            
            logger.info("Comprehensive segmentation analysis completed successfully")
            
        except Exception as e:
            logger.error(f"Comprehensive segmentation failed: {str(e)}")
            
        return results
    
    def _create_segment_summary(self, segmented_df: pd.DataFrame) -> pd.DataFrame:
        """Create summary statistics for each behavioral segment"""
        
        summary_stats = segmented_df.groupby('BEHAVIORAL_SEGMENT').agg({
            'ACCOUNT_ID': 'count',
            'MONETARY_VALUE': ['mean', 'sum'],
            'FREQUENCY': 'mean',
            'RECENCY_DAYS': 'mean',
            'RFM_SCORE_NUMERIC': 'mean',
            'ANNUAL_REVENUE': 'mean',
            'CAMPAIGNS_RESPONDED': 'mean',
            'PRODUCT_CATEGORIES_PURCHASED': 'mean',
            'RECENT_90_DAYS_SPEND': ['mean', 'sum'],
            'SPEND_TREND_PERCENTAGE': 'mean'
        }).round(2)
        
        # Flatten column names
        summary_stats.columns = [
            'ACCOUNT_COUNT', 'AVG_MONETARY_VALUE', 'TOTAL_MONETARY_VALUE', 
            'AVG_FREQUENCY', 'AVG_RECENCY_DAYS', 'AVG_RFM_SCORE',
            'AVG_ANNUAL_REVENUE', 'AVG_CAMPAIGNS_RESPONDED', 
            'AVG_PRODUCT_CATEGORIES', 'AVG_RECENT_SPEND', 'TOTAL_RECENT_SPEND',
            'AVG_SPEND_TREND_PCT'
        ]
        
        summary_stats = summary_stats.reset_index()
        
        # Add segment metadata
        summary_stats['SEGMENT_PRIORITY'] = summary_stats['BEHAVIORAL_SEGMENT'].map(
            lambda x: self.segment_definitions[x]['priority']
        )
        summary_stats['SEGMENT_DESCRIPTION'] = summary_stats['BEHAVIORAL_SEGMENT'].map(
            lambda x: self.segment_definitions[x]['description']
        )
        
        return summary_stats.sort_values('SEGMENT_PRIORITY')
    
    def get_account_recommendations(self, account_id: str) -> Dict[str, Any]:
        """
        Get personalized recommendations for a specific account
        """
        logger.info(f"Generating recommendations for account {account_id}")
        
        try:
            # Get account's current segmentation
            segments = self.generate_comprehensive_segments()
            
            if 'rfm_analysis' not in segments:
                return {'error': 'No segmentation data available'}
            
            account_data = segments['rfm_analysis'][
                segments['rfm_analysis']['ACCOUNT_ID'] == account_id
            ]
            
            if len(account_data) == 0:
                return {'error': f'Account {account_id} not found'}
            
            account = account_data.iloc[0]
            
            # Get product propensity for this account
            propensity_data = segments['product_propensity'][
                segments['product_propensity']['ACCOUNT_ID'] == account_id
            ].sort_values('PROPENSITY_SCORE', ascending=False)
            
            # Generate recommendations based on segment
            segment = account['BEHAVIORAL_SEGMENT']
            recommendations = self._generate_segment_specific_recommendations(
                account, segment, propensity_data
            )
            
            return {
                'account_id': account_id,
                'account_name': account['ACCOUNT_NAME'],
                'current_segment': segment,
                'rfm_score': account['RFM_SCORE'],
                'recommendations': recommendations,
                'top_product_opportunities': propensity_data.head(5).to_dict('records') if len(propensity_data) > 0 else []
            }
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations for {account_id}: {str(e)}")
            return {'error': str(e)}
    
    def _generate_segment_specific_recommendations(self, account: pd.Series, segment: str, propensity_data: pd.DataFrame) -> List[Dict]:
        """Generate segment-specific recommendations"""
        
        recommendations = []
        
        if segment == 'Champions':
            recommendations.extend([
                {'type': 'retention', 'priority': 'high', 'action': 'Offer exclusive premium products or early access'},
                {'type': 'expansion', 'priority': 'high', 'action': 'Cross-sell complementary product categories'},
                {'type': 'advocacy', 'priority': 'medium', 'action': 'Request referrals and case study participation'}
            ])
        
        elif segment == 'At Risk' or segment == 'Cannot Lose Them':
            recommendations.extend([
                {'type': 'retention', 'priority': 'critical', 'action': 'Immediate personal outreach by sales rep'},
                {'type': 'incentive', 'priority': 'high', 'action': 'Offer significant discount or special pricing'},
                {'type': 'engagement', 'priority': 'high', 'action': 'Schedule account review meeting'}
            ])
        
        elif segment == 'New Customers':
            recommendations.extend([
                {'type': 'onboarding', 'priority': 'high', 'action': 'Provide product education and usage guidance'},
                {'type': 'engagement', 'priority': 'medium', 'action': 'Follow up within 30 days of first purchase'},
                {'type': 'expansion', 'priority': 'medium', 'action': 'Introduce related product categories'}
            ])
        
        elif segment == 'Need Attention':
            recommendations.extend([
                {'type': 'engagement', 'priority': 'high', 'action': 'Proactive check-in call or email'},
                {'type': 'incentive', 'priority': 'medium', 'action': 'Targeted promotional offers'},
                {'type': 'feedback', 'priority': 'medium', 'action': 'Gather feedback on service satisfaction'}
            ])
        
        else:  # Default recommendations for other segments
            recommendations.extend([
                {'type': 'engagement', 'priority': 'medium', 'action': 'Regular communication cadence'},
                {'type': 'expansion', 'priority': 'low', 'action': 'Introduce new product categories based on purchase history'}
            ])
        
        return recommendations
    
    def save_segments_to_snowflake(self, segments_data: Dict[str, pd.DataFrame]) -> bool:
        """
        Save segmentation results to Snowflake tables
        """
        logger.info("Saving segmentation results to Snowflake...")
        
        try:
            # Create segmentation tables if they don't exist
            self._create_segmentation_tables()
            
            # Save RFM analysis
            if 'rfm_analysis' in segments_data:
                self._save_dataframe_to_table(
                    segments_data['rfm_analysis'], 
                    'ACCOUNT_SEGMENTATION_SCORES'
                )
            
            # Save product propensity
            if 'product_propensity' in segments_data:
                self._save_dataframe_to_table(
                    segments_data['product_propensity'], 
                    'PRODUCT_PROPENSITY_SCORES'
                )
            
            # Save segment summary
            if 'segment_summary' in segments_data:
                self._save_dataframe_to_table(
                    segments_data['segment_summary'], 
                    'SEGMENT_PERFORMANCE_SUMMARY'
                )
            
            logger.info("Successfully saved segmentation results to Snowflake")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save segments to Snowflake: {str(e)}")
            return False
    
    def _create_segmentation_tables(self):
        """Create tables to store segmentation results"""
        
        # Account segmentation scores table
        segmentation_table_sql = """
        CREATE TABLE IF NOT EXISTS ACCOUNT_SEGMENTATION_SCORES (
            ACCOUNT_ID VARCHAR(50),
            ACCOUNT_NAME VARCHAR(200),
            BEHAVIORAL_SEGMENT VARCHAR(50),
            SEGMENT_PRIORITY INTEGER,
            RFM_SCORE VARCHAR(10),
            RFM_SCORE_NUMERIC DECIMAL(5,2),
            R_QUINTILE INTEGER,
            F_QUINTILE INTEGER,
            M_QUINTILE INTEGER,
            RECENCY_DAYS INTEGER,
            FREQUENCY INTEGER,
            MONETARY_VALUE DECIMAL(15,2),
            LAST_UPDATED TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            PRIMARY KEY (ACCOUNT_ID)
        )
        """
        
        # Product propensity scores table
        propensity_table_sql = """
        CREATE TABLE IF NOT EXISTS PRODUCT_PROPENSITY_SCORES (
            ACCOUNT_ID VARCHAR(50),
            CATEGORY VARCHAR(100),
            BRAND VARCHAR(100),
            PROPENSITY_SCORE DECIMAL(5,2),
            CATEGORY_AFFINITY_SCORE DECIMAL(5,2),
            RECENCY_SCORE INTEGER,
            FREQUENCY_SCORE INTEGER,
            LAST_PURCHASE_DATE DATE,
            LAST_UPDATED TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            PRIMARY KEY (ACCOUNT_ID, CATEGORY, BRAND)
        )
        """
        
        # Segment performance summary table
        summary_table_sql = """
        CREATE TABLE IF NOT EXISTS SEGMENT_PERFORMANCE_SUMMARY (
            BEHAVIORAL_SEGMENT VARCHAR(50),
            ACCOUNT_COUNT INTEGER,
            AVG_MONETARY_VALUE DECIMAL(15,2),
            TOTAL_MONETARY_VALUE DECIMAL(15,2),
            AVG_FREQUENCY DECIMAL(10,2),
            AVG_RECENCY_DAYS DECIMAL(10,2),
            SEGMENT_PRIORITY INTEGER,
            LAST_UPDATED TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            PRIMARY KEY (BEHAVIORAL_SEGMENT)
        )
        """
        
        self.sf.execute_sql(segmentation_table_sql)
        self.sf.execute_sql(propensity_table_sql)
        self.sf.execute_sql(summary_table_sql)
    
    def _save_dataframe_to_table(self, df: pd.DataFrame, table_name: str):
        """Helper method to save DataFrame to Snowflake table"""
        
        # Clear existing data
        self.sf.execute_sql(f"DELETE FROM {table_name}")
        
        # Insert new data
        for _, row in df.iterrows():
            values = []
            for val in row.values:
                if pd.isna(val) or val is None:
                    values.append('NULL')
                elif isinstance(val, str):
                    # Escape single quotes
                    escaped_val = val.replace("'", "''")
                    values.append(f"'{escaped_val}'")
                else:
                    values.append(str(val))
            
            columns = ', '.join(row.index.tolist())
            values_str = ', '.join(values)
            
            sql = f"INSERT INTO {table_name} ({columns}) VALUES ({values_str})"
            self.sf.execute_sql(sql)


class SegmentationAgent:
    """
    LangChain-based agent for interactive segmentation analysis
    """
    
    def __init__(self, sf_manager: SnowflakeManager):
        self.segmentation_engine = RealTimeSegmentationEngine(sf_manager)
        self.sf = sf_manager
        
    def analyze_account_segment(self, account_id: str) -> Dict[str, Any]:
        """Analyze specific account's segmentation"""
        return self.segmentation_engine.get_account_recommendations(account_id)
    
    def get_segment_insights(self, segment_name: str = None) -> Dict[str, Any]:
        """Get insights for a specific segment or all segments"""
        
        try:
            segments_data = self.segmentation_engine.generate_comprehensive_segments()
            
            if 'segment_summary' not in segments_data:
                return {'error': 'No segmentation data available'}
            
            summary_df = segments_data['segment_summary']
            
            if segment_name:
                segment_data = summary_df[summary_df['BEHAVIORAL_SEGMENT'] == segment_name]
                if len(segment_data) == 0:
                    return {'error': f'Segment {segment_name} not found'}
                return segment_data.iloc[0].to_dict()
            else:
                return {
                    'total_segments': len(summary_df),
                    'segments': summary_df.to_dict('records')
                }
                
        except Exception as e:
            logger.error(f"Failed to get segment insights: {str(e)}")
            return {'error': str(e)}
    
    def identify_high_value_opportunities(self) -> Dict[str, Any]:
        """Identify high-value business opportunities from segmentation"""
        
        try:
            segments_data = self.segmentation_engine.generate_comprehensive_segments()
            
            if 'rfm_analysis' not in segments_data:
                return {'error': 'No segmentation data available'}
            
            rfm_df = segments_data['rfm_analysis']
            
            # Identify key opportunities
            opportunities = {
                'at_risk_high_value': rfm_df[
                    (rfm_df['BEHAVIORAL_SEGMENT'].isin(['At Risk', 'Cannot Lose Them'])) &
                    (rfm_df['MONETARY_VALUE'] > rfm_df['MONETARY_VALUE'].quantile(0.7))
                ][['ACCOUNT_ID', 'ACCOUNT_NAME', 'BEHAVIORAL_SEGMENT', 'MONETARY_VALUE', 'RECENCY_DAYS']].to_dict('records'),
                
                'promising_new_customers': rfm_df[
                    (rfm_df['BEHAVIORAL_SEGMENT'] == 'New Customers') &
                    (rfm_df['RFM_SCORE_NUMERIC'] >= 4.0)
                ][['ACCOUNT_ID', 'ACCOUNT_NAME', 'MONETARY_VALUE', 'FREQUENCY']].to_dict('records'),
                
                'champions_for_expansion': rfm_df[
                    (rfm_df['BEHAVIORAL_SEGMENT'] == 'Champions') &
                    (rfm_df.get('PRODUCT_CATEGORIES_PURCHASED', 0) < 3)
                ][['ACCOUNT_ID', 'ACCOUNT_NAME', 'PRODUCT_CATEGORIES_PURCHASED']].to_dict('records'),
                
                'hibernating_with_potential': rfm_df[
                    (rfm_df['BEHAVIORAL_SEGMENT'] == 'Hibernating') &
                    (rfm_df['ANNUAL_REVENUE'] > rfm_df['ANNUAL_REVENUE'].median())
                ][['ACCOUNT_ID', 'ACCOUNT_NAME', 'ANNUAL_REVENUE', 'RECENCY_DAYS']].to_dict('records')
            }
            
            # Calculate opportunity metrics
            metrics = {
                'total_at_risk_value': sum(acc['MONETARY_VALUE'] for acc in opportunities['at_risk_high_value']),
                'new_customer_potential': len(opportunities['promising_new_customers']),
                'expansion_opportunities': len(opportunities['champions_for_expansion']),
                'reactivation_targets': len(opportunities['hibernating_with_potential'])
            }
            
            return {
                'opportunities': opportunities,
                'metrics': metrics,
                'recommendations': self._generate_opportunity_recommendations(opportunities, metrics)
            }
            
        except Exception as e:
            logger.error(f"Failed to identify opportunities: {str(e)}")
            return {'error': str(e)}
    
    def _generate_opportunity_recommendations(self, opportunities: Dict, metrics: Dict) -> List[Dict]:
        """Generate actionable recommendations from opportunities"""
        
        recommendations = []
        
        # At-risk customer recommendations
        if metrics['total_at_risk_value'] > 0:
            recommendations.append({
                'priority': 'Critical',
                'category': 'Retention',
                'action': f'Immediate retention campaign for {len(opportunities["at_risk_high_value"])} high-value at-risk accounts',
                'expected_impact': f'Prevent ${metrics["total_at_risk_value"]:,.2f} in potential revenue loss',
                'timeline': '7-14 days'
            })
        
        # New customer recommendations
        if metrics['new_customer_potential'] > 0:
            recommendations.append({
                'priority': 'High',
                'category': 'Growth',
                'action': f'Onboarding program for {metrics["new_customer_potential"]} promising new customers',
                'expected_impact': 'Increase customer lifetime value by 30-50%',
                'timeline': '30-60 days'
            })
        
        # Expansion recommendations
        if metrics['expansion_opportunities'] > 0:
            recommendations.append({
                'priority': 'Medium',
                'category': 'Expansion',
                'action': f'Cross-sell campaign for {metrics["expansion_opportunities"]} champion accounts',
                'expected_impact': 'Increase average order value by 20-40%',
                'timeline': '60-90 days'
            })
        
        # Reactivation recommendations
        if metrics['reactivation_targets'] > 0:
            recommendations.append({
                'priority': 'Low',
                'category': 'Reactivation',
                'action': f'Win-back campaign for {metrics["reactivation_targets"]} dormant accounts',
                'expected_impact': 'Reactivate 15-25% of targeted accounts',
                'timeline': '90-120 days'
            })
        
        return recommendations
    
    def generate_campaign_targeting_recommendations(self, campaign_type: str = None) -> Dict[str, Any]:
        """Generate campaign targeting recommendations based on segments"""
        
        try:
            segments_data = self.segmentation_engine.generate_comprehensive_segments()
            
            if 'rfm_analysis' not in segments_data:
                return {'error': 'No segmentation data available'}
            
            rfm_df = segments_data['rfm_analysis']
            
            # Define campaign targeting strategies by segment
            targeting_strategies = {
                'promotional': {
                    'primary_targets': ['Need Attention', 'About to Sleep', 'Promising'],
                    'secondary_targets': ['Potential Loyalists', 'Loyal Customers'],
                    'avoid': ['Champions'],  # Don't discount champions
                    'message': 'Special discount offers and incentives'
                },
                'premium': {
                    'primary_targets': ['Champions', 'Loyal Customers'],
                    'secondary_targets': ['Potential Loyalists'],
                    'avoid': ['Hibernating', 'At Risk'],
                    'message': 'Exclusive premium products and early access'
                },
                'retention': {
                    'primary_targets': ['At Risk', 'Cannot Lose Them', 'About to Sleep'],
                    'secondary_targets': ['Need Attention'],
                    'avoid': ['New Customers', 'Champions'],
                    'message': 'Personalized offers and account review invitations'
                },
                'acquisition': {
                    'primary_targets': ['New Customers', 'Potential Loyalists'],
                    'secondary_targets': ['Promising'],
                    'avoid': ['Hibernating', 'At Risk'],
                    'message': 'Welcome offers and product education'
                }
            }
            
            if campaign_type and campaign_type in targeting_strategies:
                strategy = targeting_strategies[campaign_type]
                
                primary_accounts = rfm_df[
                    rfm_df['BEHAVIORAL_SEGMENT'].isin(strategy['primary_targets'])
                ][['ACCOUNT_ID', 'ACCOUNT_NAME', 'BEHAVIORAL_SEGMENT', 'RFM_SCORE_NUMERIC']].to_dict('records')
                
                secondary_accounts = rfm_df[
                    rfm_df['BEHAVIORAL_SEGMENT'].isin(strategy['secondary_targets'])
                ][['ACCOUNT_ID', 'ACCOUNT_NAME', 'BEHAVIORAL_SEGMENT', 'RFM_SCORE_NUMERIC']].to_dict('records')
                
                return {
                    'campaign_type': campaign_type,
                    'strategy': strategy,
                    'primary_targets': primary_accounts,
                    'secondary_targets': secondary_accounts,
                    'targeting_summary': {
                        'primary_count': len(primary_accounts),
                        'secondary_count': len(secondary_accounts),
                        'total_reach': len(primary_accounts) + len(secondary_accounts)
                    }
                }
            else:
                # Return all strategies
                return {
                    'available_campaigns': list(targeting_strategies.keys()),
                    'strategies': targeting_strategies,
                    'segment_distribution': rfm_df['BEHAVIORAL_SEGMENT'].value_counts().to_dict()
                }
                
        except Exception as e:
            logger.error(f"Failed to generate campaign recommendations: {str(e)}")
            return {'error': str(e)}


def main():
    """Test the segmentation engine"""
    print("🎯 Real-Time Customer Segmentation Engine")
    print("=" * 50)
    
    try:
        # Initialize Snowflake manager
        sf_manager = SnowflakeManager()
        if not sf_manager.connect():
            print("❌ Failed to connect to Snowflake")
            return
        
        print("✅ Connected to Snowflake")
        
        # Initialize segmentation engine
        segmentation_engine = RealTimeSegmentationEngine(sf_manager)
        
        # Generate comprehensive segments
        print("🔄 Generating comprehensive segmentation analysis...")
        segments_data = segmentation_engine.generate_comprehensive_segments()
        
        if 'rfm_analysis' in segments_data:
            rfm_df = segments_data['rfm_analysis']
            print(f"✅ Analyzed {len(rfm_df)} accounts")
            
            # Display segment summary
            if 'segment_summary' in segments_data:
                print("\n📊 Segment Summary:")
                summary_df = segments_data['segment_summary']
                print(summary_df[['BEHAVIORAL_SEGMENT', 'ACCOUNT_COUNT', 'AVG_MONETARY_VALUE', 'SEGMENT_PRIORITY']])
            
            # Save to Snowflake
            print("\n💾 Saving results to Snowflake...")
            success = segmentation_engine.save_segments_to_snowflake(segments_data)
            if success:
                print("✅ Results saved successfully")
            else:
                print("❌ Failed to save results")
        
        # Test agent functionality
        print("\n🤖 Testing Segmentation Agent...")
        agent = SegmentationAgent(sf_manager)
        
        # Get high-value opportunities
        opportunities = agent.identify_high_value_opportunities()
        if 'opportunities' in opportunities:
            print("💰 High-Value Opportunities Identified:")
            for category, accounts in opportunities['opportunities'].items():
                if accounts:
                    print(f"  • {category}: {len(accounts)} accounts")
        
        sf_manager.close_connection()
        print("\n🎉 Segmentation analysis completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()