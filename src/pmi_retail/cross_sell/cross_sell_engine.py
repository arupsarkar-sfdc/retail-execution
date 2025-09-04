"""
Cross-Sell Optimization Engine with Promotional Integration
Leverages transaction patterns, product affinities, and campaign data for intelligent cross-sell recommendations
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger
import sys
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from itertools import combinations
import joblib

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from pmi_retail.database.snowflake.connection import SnowflakeManager


class CrossSellOptimizationEngine:
    """
    Advanced cross-sell optimization engine combining market basket analysis,
    product affinities, promotional context, and customer segmentation
    """
    
    def __init__(self, sf_manager: SnowflakeManager):
        self.sf = sf_manager
        self.product_affinity_matrix = None
        self.category_affinity_scores = None
        
        # Cross-sell configuration
        self.min_support = 0.01  # Minimum support for association rules
        self.min_confidence = 0.1  # Minimum confidence for recommendations
        self.max_recommendations = 5  # Maximum recommendations per account
        
        # Promotional integration settings
        self.promotional_boost = 1.2  # Score boost for promoted products
        self.campaign_recency_weight = 0.8  # Weight for recent campaign engagement
    
    def calculate_market_basket_analysis(self, lookback_days: int = 365) -> pd.DataFrame:
        """
        Perform market basket analysis to identify product associations
        
        Args:
            lookback_days: Number of days to analyze for product associations
            
        Returns:
            DataFrame with product association rules
        """
        logger.info(f"Performing market basket analysis for last {lookback_days} days...")
        
        # Get transaction data with product relationships
        basket_query = f"""
        WITH transaction_baskets AS (
            SELECT 
                t.ACCOUNT_ID,
                t.TRANSACTION_DATE,
                p.PRODUCT_ID,
                p.PRODUCT_NAME,
                p.CATEGORY,
                p.BRAND,
                p.SUBCATEGORY,
                t.NET_AMOUNT,
                t.QUANTITY,
                a.SEGMENT,
                a.ACCOUNT_TYPE
            FROM TRANSACTIONS t
            JOIN PRODUCTS p ON t.PRODUCT_ID = p.PRODUCT_ID
            JOIN ACCOUNTS a ON t.ACCOUNT_ID = a.ACCOUNT_ID
            WHERE t.TRANSACTION_DATE >= DATEADD(day, -{lookback_days}, CURRENT_DATE())
        ),
        product_pairs AS (
            SELECT 
                t1.ACCOUNT_ID,
                t1.TRANSACTION_DATE,
                t1.SEGMENT,
                t1.CATEGORY as PRODUCT_A_CATEGORY,
                t1.BRAND as PRODUCT_A_BRAND,
                t1.PRODUCT_ID as PRODUCT_A_ID,
                t1.PRODUCT_NAME as PRODUCT_A_NAME,
                t2.CATEGORY as PRODUCT_B_CATEGORY,
                t2.BRAND as PRODUCT_B_BRAND,
                t2.PRODUCT_ID as PRODUCT_B_ID,
                t2.PRODUCT_NAME as PRODUCT_B_NAME,
                t1.NET_AMOUNT + t2.NET_AMOUNT as COMBINED_VALUE
            FROM transaction_baskets t1
            JOIN transaction_baskets t2 ON t1.ACCOUNT_ID = t2.ACCOUNT_ID 
                                       AND t1.TRANSACTION_DATE = t2.TRANSACTION_DATE
                                       AND t1.PRODUCT_ID != t2.PRODUCT_ID
        ),
        association_rules AS (
            SELECT 
                PRODUCT_A_CATEGORY,
                PRODUCT_A_BRAND,
                PRODUCT_B_CATEGORY,
                PRODUCT_B_BRAND,
                SEGMENT,
                COUNT(DISTINCT ACCOUNT_ID) as CO_OCCURRENCE_COUNT,
                COUNT(DISTINCT CONCAT(ACCOUNT_ID, TRANSACTION_DATE)) as TRANSACTION_COUNT,
                AVG(COMBINED_VALUE) as AVG_BASKET_VALUE,
                SUM(COMBINED_VALUE) as TOTAL_BASKET_VALUE
            FROM product_pairs
            GROUP BY PRODUCT_A_CATEGORY, PRODUCT_A_BRAND, PRODUCT_B_CATEGORY, PRODUCT_B_BRAND, SEGMENT
        )
        SELECT 
            *,
            -- Calculate support (frequency of co-occurrence)
            CO_OCCURRENCE_COUNT * 1.0 / (
                SELECT COUNT(DISTINCT ACCOUNT_ID) FROM transaction_baskets 
                WHERE SEGMENT = ar.SEGMENT
            ) as SUPPORT,
            
            -- Calculate confidence (conditional probability)
            CO_OCCURRENCE_COUNT * 1.0 / (
                SELECT COUNT(DISTINCT ACCOUNT_ID) 
                FROM transaction_baskets tb 
                WHERE tb.CATEGORY = ar.PRODUCT_A_CATEGORY 
                  AND tb.BRAND = ar.PRODUCT_A_BRAND 
                  AND tb.SEGMENT = ar.SEGMENT
            ) as CONFIDENCE,
            
            -- Calculate lift (strength of association)
            (CO_OCCURRENCE_COUNT * 1.0 / (
                SELECT COUNT(DISTINCT ACCOUNT_ID) FROM transaction_baskets 
                WHERE SEGMENT = ar.SEGMENT
            )) / (
                (SELECT COUNT(DISTINCT ACCOUNT_ID) 
                 FROM transaction_baskets tb1 
                 WHERE tb1.CATEGORY = ar.PRODUCT_A_CATEGORY 
                   AND tb1.BRAND = ar.PRODUCT_A_BRAND 
                   AND tb1.SEGMENT = ar.SEGMENT) * 1.0 / 
                (SELECT COUNT(DISTINCT ACCOUNT_ID) FROM transaction_baskets WHERE SEGMENT = ar.SEGMENT) *
                (SELECT COUNT(DISTINCT ACCOUNT_ID) 
                 FROM transaction_baskets tb2 
                 WHERE tb2.CATEGORY = ar.PRODUCT_B_CATEGORY 
                   AND tb2.BRAND = ar.PRODUCT_B_BRAND 
                   AND tb2.SEGMENT = ar.SEGMENT) * 1.0 / 
                (SELECT COUNT(DISTINCT ACCOUNT_ID) FROM transaction_baskets WHERE SEGMENT = ar.SEGMENT)
            ) as LIFT
        FROM association_rules ar
        WHERE CO_OCCURRENCE_COUNT >= 3  -- Minimum occurrences
        ORDER BY SUPPORT DESC, CONFIDENCE DESC, LIFT DESC
        """
        
        try:
            associations_df = self.sf.execute_query(basket_query)
            
            # Filter by minimum support and confidence
            filtered_associations = associations_df[
                (associations_df['SUPPORT'] >= self.min_support) &
                (associations_df['CONFIDENCE'] >= self.min_confidence)
            ]
            
            logger.info(f"Generated {len(filtered_associations)} product association rules")
            return filtered_associations
            
        except Exception as e:
            logger.error(f"Failed to calculate market basket analysis: {str(e)}")
            return pd.DataFrame()
    
    def calculate_product_affinity_matrix(self, associations_df: pd.DataFrame) -> np.ndarray:
        """
        Calculate product affinity matrix for collaborative filtering
        """
        logger.info("Calculating product affinity matrix...")
        
        if len(associations_df) == 0:
            return np.array([])
        
        try:
            # Create product-to-product affinity matrix
            products_a = associations_df[['PRODUCT_A_CATEGORY', 'PRODUCT_A_BRAND']].drop_duplicates()
            products_b = associations_df[['PRODUCT_B_CATEGORY', 'PRODUCT_B_BRAND']].drop_duplicates()
            
            # Combine unique products
            all_products = pd.concat([
                products_a.rename(columns={'PRODUCT_A_CATEGORY': 'CATEGORY', 'PRODUCT_A_BRAND': 'BRAND'}),
                products_b.rename(columns={'PRODUCT_B_CATEGORY': 'CATEGORY', 'PRODUCT_B_BRAND': 'BRAND'})
            ]).drop_duplicates().reset_index(drop=True)
            
            # Create affinity matrix
            affinity_matrix = np.zeros((len(all_products), len(all_products)))
            
            for _, rule in associations_df.iterrows():
                # Find indices for product A and B
                prod_a_idx = all_products[
                    (all_products['CATEGORY'] == rule['PRODUCT_A_CATEGORY']) & 
                    (all_products['BRAND'] == rule['PRODUCT_A_BRAND'])
                ].index[0] if len(all_products[
                    (all_products['CATEGORY'] == rule['PRODUCT_A_CATEGORY']) & 
                    (all_products['BRAND'] == rule['PRODUCT_A_BRAND'])
                ]) > 0 else 0
                
                prod_b_idx = all_products[
                    (all_products['CATEGORY'] == rule['PRODUCT_B_CATEGORY']) & 
                    (all_products['BRAND'] == rule['PRODUCT_B_BRAND'])
                ].index[0] if len(all_products[
                    (all_products['CATEGORY'] == rule['PRODUCT_B_CATEGORY']) & 
                    (all_products['BRAND'] == rule['PRODUCT_B_BRAND'])
                ]) > 0 else 0
                
                # Use confidence * lift as affinity score
                affinity_score = rule['CONFIDENCE'] * rule['LIFT']
                affinity_matrix[prod_a_idx, prod_b_idx] = affinity_score
            
            self.product_affinity_matrix = affinity_matrix
            self.product_index = all_products
            
            logger.info(f"Created {len(all_products)}x{len(all_products)} product affinity matrix")
            return affinity_matrix
            
        except Exception as e:
            logger.error(f"Failed to calculate affinity matrix: {str(e)}")
            return np.array([])
    
    def analyze_promotional_impact(self, lookback_days: int = 180) -> pd.DataFrame:
        """
        Analyze promotional campaign impact on cross-sell opportunities
        """
        logger.info(f"Analyzing promotional impact for last {lookback_days} days...")
        
        promotional_query = f"""
        WITH campaign_transactions AS (
            SELECT 
                t.ACCOUNT_ID,
                t.PRODUCT_ID,
                p.CATEGORY,
                p.BRAND,
                t.CAMPAIGN_ID,
                c.CAMPAIGN_NAME,
                c.CAMPAIGN_TYPE,
                c.DISCOUNT_PERCENTAGE,
                c.TARGET_SEGMENT,
                t.NET_AMOUNT,
                t.TRANSACTION_DATE,
                a.SEGMENT
            FROM TRANSACTIONS t
            JOIN PRODUCTS p ON t.PRODUCT_ID = p.PRODUCT_ID
            JOIN ACCOUNTS a ON t.ACCOUNT_ID = a.ACCOUNT_ID
            LEFT JOIN CAMPAIGNS c ON t.CAMPAIGN_ID = c.CAMPAIGN_ID
            WHERE t.TRANSACTION_DATE >= DATEADD(day, -{lookback_days}, CURRENT_DATE())
        ),
        promotional_cross_sell AS (
            SELECT 
                ct1.CAMPAIGN_ID,
                ct1.CAMPAIGN_NAME,
                ct1.CATEGORY as PRIMARY_CATEGORY,
                ct1.BRAND as PRIMARY_BRAND,
                ct2.CATEGORY as CROSS_SELL_CATEGORY,
                ct2.BRAND as CROSS_SELL_BRAND,
                ct1.SEGMENT,
                COUNT(DISTINCT ct1.ACCOUNT_ID) as ACCOUNTS_ENGAGED,
                COUNT(*) as CROSS_SELL_INSTANCES,
                AVG(ct1.NET_AMOUNT + ct2.NET_AMOUNT) as AVG_BASKET_VALUE,
                SUM(ct1.NET_AMOUNT + ct2.NET_AMOUNT) as TOTAL_CROSS_SELL_VALUE,
                AVG(ct1.DISCOUNT_PERCENTAGE) as AVG_DISCOUNT
            FROM campaign_transactions ct1
            JOIN campaign_transactions ct2 ON ct1.ACCOUNT_ID = ct2.ACCOUNT_ID 
                                          AND ct1.TRANSACTION_DATE = ct2.TRANSACTION_DATE
                                          AND ct1.PRODUCT_ID != ct2.PRODUCT_ID
            WHERE ct1.CAMPAIGN_ID IS NOT NULL
            GROUP BY ct1.CAMPAIGN_ID, ct1.CAMPAIGN_NAME, ct1.CATEGORY, ct1.BRAND,
                     ct2.CATEGORY, ct2.BRAND, ct1.SEGMENT
        )
        SELECT *,
               -- Calculate promotional lift for cross-sell
               CROSS_SELL_INSTANCES * 1.0 / ACCOUNTS_ENGAGED as CROSS_SELL_RATE,
               
               -- Calculate revenue per account
               TOTAL_CROSS_SELL_VALUE / ACCOUNTS_ENGAGED as REVENUE_PER_ACCOUNT,
               
               -- Calculate effectiveness score
               (CROSS_SELL_INSTANCES * AVG_BASKET_VALUE) / (AVG_DISCOUNT + 1) as PROMOTION_EFFECTIVENESS
        FROM promotional_cross_sell
        WHERE ACCOUNTS_ENGAGED >= 2  -- Minimum statistical significance
        ORDER BY PROMOTION_EFFECTIVENESS DESC
        """
        
        try:
            promotional_df = self.sf.execute_query(promotional_query)
            logger.info(f"Analyzed promotional impact for {len(promotional_df)} campaign-product combinations")
            return promotional_df
            
        except Exception as e:
            logger.error(f"Failed to analyze promotional impact: {str(e)}")
            return pd.DataFrame()
    
    def generate_account_cross_sell_recommendations(self, account_id: str, include_promotions: bool = True) -> Dict[str, Any]:
        """
        Generate personalized cross-sell recommendations for a specific account
        """
        logger.info(f"Generating cross-sell recommendations for account {account_id}")
        
        try:
            # Get account's purchase history and segment
            account_history_query = f"""
            WITH account_profile AS (
                SELECT 
                    a.ACCOUNT_ID,
                    a.ACCOUNT_NAME,
                    a.SEGMENT,
                    a.ACCOUNT_TYPE,
                    a.ANNUAL_REVENUE
                FROM ACCOUNTS a
                WHERE a.ACCOUNT_ID = '{account_id}'
            ),
            purchase_history AS (
                SELECT 
                    t.ACCOUNT_ID,
                    p.PRODUCT_ID,
                    p.PRODUCT_NAME,
                    p.CATEGORY,
                    p.BRAND,
                    p.SUBCATEGORY,
                    p.UNIT_PRICE,
                    t.NET_AMOUNT,
                    t.QUANTITY,
                    t.TRANSACTION_DATE,
                    t.CAMPAIGN_ID,
                    c.CAMPAIGN_TYPE,
                    c.DISCOUNT_PERCENTAGE
                FROM TRANSACTIONS t
                JOIN PRODUCTS p ON t.PRODUCT_ID = p.PRODUCT_ID
                LEFT JOIN CAMPAIGNS c ON t.CAMPAIGN_ID = c.CAMPAIGN_ID
                WHERE t.ACCOUNT_ID = '{account_id}'
                  AND t.TRANSACTION_DATE >= DATEADD(day, -365, CURRENT_DATE())
            ),
            category_summary AS (
                SELECT 
                    CATEGORY,
                    COUNT(DISTINCT PRODUCT_ID) as PRODUCTS_PURCHASED,
                    COUNT(*) as PURCHASE_FREQUENCY,
                    SUM(NET_AMOUNT) as TOTAL_SPEND,
                    AVG(NET_AMOUNT) as AVG_SPEND,
                    MAX(TRANSACTION_DATE) as LAST_PURCHASE_DATE,
                    COUNT(DISTINCT CAMPAIGN_ID) as CAMPAIGNS_RESPONDED
                FROM purchase_history
                GROUP BY CATEGORY
            )
            SELECT 
                ap.*,
                cs.CATEGORY,
                cs.PRODUCTS_PURCHASED,
                cs.PURCHASE_FREQUENCY,
                cs.TOTAL_SPEND,
                cs.AVG_SPEND,
                cs.LAST_PURCHASE_DATE,
                cs.CAMPAIGNS_RESPONDED,
                DATEDIFF(day, cs.LAST_PURCHASE_DATE, CURRENT_DATE()) as DAYS_SINCE_LAST_PURCHASE
            FROM account_profile ap
            LEFT JOIN category_summary cs ON 1=1
            ORDER BY cs.TOTAL_SPEND DESC
            """
            
            account_data = self.sf.execute_query(account_history_query)
            
            if len(account_data) == 0:
                return {'error': f'Account {account_id} not found or has no purchase history'}
            
            account_info = account_data.iloc[0]
            segment = account_info['SEGMENT']
            
            # Get association rules for this account's segment
            associations_df = self.calculate_market_basket_analysis()
            
            if len(associations_df) == 0:
                return {'error': 'No association rules available for recommendations'}
            
            segment_rules = associations_df[associations_df['SEGMENT'] == segment]
            
            # Generate recommendations based on purchased categories
            recommendations = []
            purchased_categories = set(account_data['CATEGORY'].dropna())
            
            for category in purchased_categories:
                # Find products that go well with this category
                category_rules = segment_rules[
                    (segment_rules['PRODUCT_A_CATEGORY'] == category)
                ].sort_values(['CONFIDENCE', 'LIFT'], ascending=[False, False])
                
                for _, rule in category_rules.head(3).iterrows():  # Top 3 per category
                    rec_category = rule['PRODUCT_B_CATEGORY']
                    rec_brand = rule['PRODUCT_B_BRAND']
                    
                    # For demo purposes, allow all recommendations regardless of purchase history
                    # In production, you might want to filter out recently purchased items
                    pass
                    
                    # Calculate recommendation score (convert to float to avoid decimal issues)
                    confidence = float(rule['CONFIDENCE']) if rule['CONFIDENCE'] is not None else 0.0
                    lift = float(rule['LIFT']) if rule['LIFT'] is not None else 0.0
                    base_score = confidence * lift * 100
                    
                    # Apply promotional boost if applicable
                    promotional_boost = 1.0
                    if include_promotions:
                        promotional_data = self.analyze_promotional_impact()
                        relevant_promos = promotional_data[
                            (promotional_data['PRIMARY_CATEGORY'] == category) &
                            (promotional_data['CROSS_SELL_CATEGORY'] == rec_category) &
                            (promotional_data['SEGMENT'] == segment)
                        ]
                        
                        if len(relevant_promos) > 0:
                            promotional_boost = self.promotional_boost
                    
                    final_score = base_score * promotional_boost
                    
                    recommendations.append({
                        'recommended_category': rec_category,
                        'recommended_brand': rec_brand,
                        'trigger_category': category,
                        'confidence': rule['CONFIDENCE'],
                        'lift': rule['LIFT'],
                        'support': rule['SUPPORT'],
                        'base_score': base_score,
                        'promotional_boost': promotional_boost,
                        'final_score': final_score,
                        'avg_basket_value': rule['AVG_BASKET_VALUE']
                    })
            
            # Sort by final score and take top recommendations
            recommendations = sorted(recommendations, key=lambda x: x['final_score'], reverse=True)
            top_recommendations = recommendations[:self.max_recommendations]
            
            # Get specific product suggestions
            product_suggestions = []
            for rec in top_recommendations:
                products_query = f"""
                SELECT TOP 3 PRODUCT_ID, PRODUCT_NAME, UNIT_PRICE, PRODUCT_DESCRIPTION
                FROM PRODUCTS 
                WHERE CATEGORY = '{rec['recommended_category']}' 
                  AND BRAND = '{rec['recommended_brand']}'
                  AND STATUS = 'Active'
                ORDER BY UNIT_PRICE DESC
                """
                
                products = self.sf.execute_query(products_query)
                if len(products) > 0:
                    rec['suggested_products'] = products.to_dict('records')
                else:
                    rec['suggested_products'] = []
            
            # Get active promotions that could boost these recommendations
            active_promotions = []
            if include_promotions:
                promotions_query = f"""
                SELECT CAMPAIGN_ID, CAMPAIGN_NAME, CAMPAIGN_TYPE, DISCOUNT_PERCENTAGE, TARGET_PRODUCTS
                FROM CAMPAIGNS 
                WHERE STATUS = 'Active' 
                  AND START_DATE <= CURRENT_DATE()
                  AND END_DATE >= CURRENT_DATE()
                  AND (TARGET_SEGMENT = '{segment}' OR TARGET_SEGMENT = 'ALL')
                ORDER BY DISCOUNT_PERCENTAGE DESC
                """
                
                promotions_df = self.sf.execute_query(promotions_query)
                if len(promotions_df) > 0:
                    active_promotions = promotions_df.to_dict('records')
            
            return {
                'account_id': account_id,
                'account_name': account_info['ACCOUNT_NAME'],
                'segment': segment,
                'purchased_categories': list(purchased_categories),
                'recommendations': top_recommendations,
                'active_promotions': active_promotions,
                'analysis_metadata': {
                    'total_association_rules': len(segment_rules),
                    'recommendation_count': len(top_recommendations),
                    'promotional_boost_applied': include_promotions
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate cross-sell recommendations for {account_id}: {str(e)}")
            return {'error': str(e)}
    
    def optimize_promotional_cross_sell_campaigns(self, segment: str = None) -> Dict[str, Any]:
        """
        Optimize promotional campaigns for maximum cross-sell effectiveness
        """
        logger.info("Optimizing promotional cross-sell campaigns...")
        
        try:
            # Get promotional impact analysis
            promotional_df = self.analyze_promotional_impact()
            
            if len(promotional_df) == 0:
                return {'error': 'No promotional data available for optimization'}
            
            # Filter by segment if specified
            if segment:
                promotional_df = promotional_df[promotional_df['SEGMENT'] == segment]
            
            # Identify top-performing promotional combinations
            top_performers = promotional_df.nlargest(10, 'PROMOTION_EFFECTIVENESS')
            
            # Identify underperforming combinations that need optimization
            underperformers = promotional_df[
                promotional_df['PROMOTION_EFFECTIVENESS'] < promotional_df['PROMOTION_EFFECTIVENESS'].median()
            ]
            
            # Generate optimization recommendations
            optimizations = []
            
            # Recommendation 1: Scale successful combinations
            for _, perf in top_performers.iterrows():
                optimizations.append({
                    'type': 'scale_success',
                    'priority': 'high',
                    'primary_category': perf['PRIMARY_CATEGORY'],
                    'cross_sell_category': perf['CROSS_SELL_CATEGORY'],
                    'current_effectiveness': perf['PROMOTION_EFFECTIVENESS'],
                    'recommendation': f"Scale campaign targeting {perf['PRIMARY_CATEGORY']} with {perf['CROSS_SELL_CATEGORY']} cross-sell",
                    'expected_impact': f"Potential to increase cross-sell revenue by ${perf['REVENUE_PER_ACCOUNT'] * 100:,.2f}"
                })
            
            # Recommendation 2: Optimize underperformers
            for _, underperf in underperformers.head(5).iterrows():
                optimizations.append({
                    'type': 'optimize_underperformer',
                    'priority': 'medium',
                    'primary_category': underperf['PRIMARY_CATEGORY'],
                    'cross_sell_category': underperf['CROSS_SELL_CATEGORY'],
                    'current_effectiveness': underperf['PROMOTION_EFFECTIVENESS'],
                    'recommendation': f"Reduce discount or improve targeting for {underperf['PRIMARY_CATEGORY']} + {underperf['CROSS_SELL_CATEGORY']}",
                    'expected_impact': f"Could save ${underperf['AVG_DISCOUNT'] * underperf['ACCOUNTS_ENGAGED']:,.2f} in discount costs"
                })
            
            # Calculate overall metrics
            total_cross_sell_revenue = promotional_df['TOTAL_CROSS_SELL_VALUE'].sum()
            total_discount_cost = (promotional_df['AVG_DISCOUNT'] * promotional_df['ACCOUNTS_ENGAGED']).sum()
            roi = (total_cross_sell_revenue - total_discount_cost) / total_discount_cost * 100
            
            return {
                'optimization_recommendations': optimizations,
                'performance_metrics': {
                    'total_cross_sell_revenue': total_cross_sell_revenue,
                    'total_discount_cost': total_discount_cost,
                    'promotional_roi': roi,
                    'top_performing_categories': top_performers[['PRIMARY_CATEGORY', 'CROSS_SELL_CATEGORY', 'PROMOTION_EFFECTIVENESS']].to_dict('records'),
                    'optimization_opportunities': len(underperformers)
                },
                'segment_analysis': segment if segment else 'All Segments'
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize promotional campaigns: {str(e)}")
            return {'error': str(e)}
    
    def generate_comprehensive_cross_sell_analysis(self, lookback_days: int = 365) -> Dict[str, Any]:
        """
        Generate comprehensive cross-sell analysis combining all metrics
        """
        logger.info("Starting comprehensive cross-sell analysis...")
        
        results = {}
        
        try:
            # Step 1: Market basket analysis
            associations_df = self.calculate_market_basket_analysis(lookback_days)
            results['association_rules'] = associations_df
            
            # Step 2: Product affinity matrix
            if len(associations_df) > 0:
                affinity_matrix = self.calculate_product_affinity_matrix(associations_df)
                results['affinity_matrix_shape'] = affinity_matrix.shape if len(affinity_matrix) > 0 else (0, 0)
            
            # Step 3: Promotional impact analysis
            promotional_df = self.analyze_promotional_impact(lookback_days // 2)  # Shorter period for promotions
            results['promotional_analysis'] = promotional_df
            
            # Step 4: Cross-sell opportunity summary
            if len(associations_df) > 0:
                opportunity_summary = self._create_cross_sell_opportunity_summary(associations_df, promotional_df)
                results['opportunity_summary'] = opportunity_summary
            
            # Step 5: Segment-specific insights
            segment_insights = self._generate_segment_cross_sell_insights(associations_df)
            results['segment_insights'] = segment_insights
            
            logger.info("Comprehensive cross-sell analysis completed successfully")
            
        except Exception as e:
            logger.error(f"Comprehensive cross-sell analysis failed: {str(e)}")
            results['error'] = str(e)
        
        return results
    
    def _create_cross_sell_opportunity_summary(self, associations_df: pd.DataFrame, promotional_df: pd.DataFrame) -> pd.DataFrame:
        """Create summary of cross-sell opportunities by category"""
        
        if len(associations_df) == 0:
            return pd.DataFrame()
        
        # Aggregate opportunities by category pairs
        opportunity_summary = associations_df.groupby(['PRODUCT_A_CATEGORY', 'PRODUCT_B_CATEGORY']).agg({
            'CO_OCCURRENCE_COUNT': 'sum',
            'CONFIDENCE': 'mean',
            'LIFT': 'mean',
            'SUPPORT': 'mean',
            'AVG_BASKET_VALUE': 'mean',
            'TOTAL_BASKET_VALUE': 'sum'
        }).round(3).reset_index()
        
        # Add promotional context if available
        if len(promotional_df) > 0:
            promo_summary = promotional_df.groupby(['PRIMARY_CATEGORY', 'CROSS_SELL_CATEGORY']).agg({
                'PROMOTION_EFFECTIVENESS': 'mean',
                'CROSS_SELL_RATE': 'mean',
                'REVENUE_PER_ACCOUNT': 'mean'
            }).round(2).reset_index()
            
            # Merge with opportunity summary
            opportunity_summary = opportunity_summary.merge(
                promo_summary,
                left_on=['PRODUCT_A_CATEGORY', 'PRODUCT_B_CATEGORY'],
                right_on=['PRIMARY_CATEGORY', 'CROSS_SELL_CATEGORY'],
                how='left'
            ).drop(['PRIMARY_CATEGORY', 'CROSS_SELL_CATEGORY'], axis=1, errors='ignore')
        
        # Calculate overall opportunity score
        opportunity_summary['OPPORTUNITY_SCORE'] = (
            opportunity_summary['CONFIDENCE'] * 0.3 +
            opportunity_summary['LIFT'] * 0.3 +
            opportunity_summary['SUPPORT'] * 100 * 0.2 +  # Scale support to similar range
            opportunity_summary.get('PROMOTION_EFFECTIVENESS', 0) * 0.2
        ).round(2)
        
        return opportunity_summary.sort_values('OPPORTUNITY_SCORE', ascending=False)
    
    def _generate_segment_cross_sell_insights(self, associations_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate cross-sell insights by customer segment"""
        
        if len(associations_df) == 0:
            return {}
        
        segment_insights = {}
        
        for segment in associations_df['SEGMENT'].unique():
            segment_data = associations_df[associations_df['SEGMENT'] == segment]
            
            # Top opportunities for this segment
            top_opportunities = segment_data.nlargest(5, 'CONFIDENCE')[
                ['PRODUCT_A_CATEGORY', 'PRODUCT_B_CATEGORY', 'CONFIDENCE', 'LIFT', 'AVG_BASKET_VALUE']
            ].to_dict('records')
            
            # Segment characteristics
            avg_confidence = segment_data['CONFIDENCE'].mean()
            avg_lift = segment_data['LIFT'].mean()
            avg_basket_value = segment_data['AVG_BASKET_VALUE'].mean()
            total_rules = len(segment_data)
            
            segment_insights[segment] = {
                'top_cross_sell_opportunities': top_opportunities,
                'segment_metrics': {
                    'average_confidence': round(avg_confidence, 3),
                    'average_lift': round(avg_lift, 3),
                    'average_basket_value': round(avg_basket_value, 2),
                    'total_association_rules': total_rules
                },
                'segment_strategy': self._get_segment_cross_sell_strategy(segment, avg_confidence, avg_lift)
            }
        
        return segment_insights
    
    def _get_segment_cross_sell_strategy(self, segment: str, avg_confidence: float, avg_lift: float) -> Dict[str, str]:
        """Get recommended cross-sell strategy for segment"""
        
        if segment == 'Premium':
            return {
                'strategy': 'Premium Bundle Strategy',
                'approach': 'Focus on high-value complementary products and exclusive offerings',
                'tactics': 'Personal recommendations, premium bundling, early access offers'
            }
        elif segment == 'Standard':
            return {
                'strategy': 'Value-Driven Cross-Sell',
                'approach': 'Emphasize value and practical benefits of additional products',
                'tactics': 'Volume discounts, practical bundles, seasonal promotions'
            }
        elif segment == 'Basic':
            return {
                'strategy': 'Entry-Level Cross-Sell',
                'approach': 'Start with low-cost, high-utility complementary products',
                'tactics': 'Small add-ons, trial sizes, loyalty incentives'
            }
        else:
            # Default strategy for other segments
            if avg_confidence > 0.3 and avg_lift > 1.5:
                return {
                    'strategy': 'High-Confidence Cross-Sell',
                    'approach': 'Leverage strong product associations with targeted recommendations',
                    'tactics': 'Data-driven recommendations, A/B test different approaches'
                }
            else:
                return {
                    'strategy': 'Exploratory Cross-Sell',
                    'approach': 'Test different product combinations to find optimal associations',
                    'tactics': 'Broad sampling, customer feedback collection, gradual optimization'
                }
    
    def save_cross_sell_results_to_snowflake(self, cross_sell_data: Dict[str, Any]) -> bool:
        """
        Save cross-sell analysis results to Snowflake tables
        """
        logger.info("Saving cross-sell results to Snowflake...")
        
        try:
            # Create cross-sell tables if they don't exist
            self._create_cross_sell_tables()
            
            # Save association rules
            if 'association_rules' in cross_sell_data and len(cross_sell_data['association_rules']) > 0:
                self._save_dataframe_to_table(
                    cross_sell_data['association_rules'],
                    'PRODUCT_ASSOCIATION_RULES'
                )
            
            # Save promotional analysis
            if 'promotional_analysis' in cross_sell_data and len(cross_sell_data['promotional_analysis']) > 0:
                self._save_dataframe_to_table(
                    cross_sell_data['promotional_analysis'],
                    'PROMOTIONAL_CROSS_SELL_ANALYSIS'
                )
            
            # Save opportunity summary
            if 'opportunity_summary' in cross_sell_data and len(cross_sell_data['opportunity_summary']) > 0:
                self._save_dataframe_to_table(
                    cross_sell_data['opportunity_summary'],
                    'CROSS_SELL_OPPORTUNITY_SUMMARY'
                )
            
            logger.info("Successfully saved cross-sell results to Snowflake")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save cross-sell results to Snowflake: {str(e)}")
            return False
    
    def _create_cross_sell_tables(self):
        """
        NOTE: For PMI demo, we skip table creation to show in-memory approach
        This demonstrates the temporary nature of custom solutions vs persistent Salesforce storage
        """
        logger.info("Skipping permanent table creation for demo - using in-memory analysis only")
        logger.warning("Custom solution limitation: No persistent storage of cross-sell analysis results")
        pass
    
    def _save_dataframe_to_table(self, df: pd.DataFrame, table_name: str):
        """
        NOTE: For PMI demo, we skip database persistence
        This demonstrates the ephemeral nature of custom-built analytics
        """
        logger.info(f"Simulating save to {table_name} - {len(df)} records processed in memory only")
        logger.warning(f"Custom solution limitation: {table_name} data exists only during session")
        pass


class CrossSellAgent:
    """
    Interactive agent for cross-sell analysis and recommendations
    """
    
    def __init__(self, sf_manager: SnowflakeManager):
        self.cross_sell_engine = CrossSellOptimizationEngine(sf_manager)
        self.sf = sf_manager
    
    def analyze_account_cross_sell_opportunities(self, account_id: str, include_promotions: bool = True) -> Dict[str, Any]:
        """Analyze cross-sell opportunities for specific account"""
        return self.cross_sell_engine.generate_account_cross_sell_recommendations(account_id, include_promotions)
    
    def identify_top_cross_sell_opportunities(self, segment: str = None, limit: int = 10) -> Dict[str, Any]:
        """Identify top cross-sell opportunities across all accounts or specific segment"""
        
        try:
            # Generate comprehensive analysis
            analysis = self.cross_sell_engine.generate_comprehensive_cross_sell_analysis()
            
            if 'association_rules' not in analysis or len(analysis['association_rules']) == 0:
                return {'error': 'No cross-sell data available'}
            
            associations_df = analysis['association_rules']
            
            # Filter by segment if specified
            if segment:
                associations_df = associations_df[associations_df['SEGMENT'] == segment]
                if len(associations_df) == 0:
                    return {'error': f'No data available for segment: {segment}'}
            
            # Get top opportunities
            top_opportunities = associations_df.nlargest(limit, 'CONFIDENCE')[
                ['PRODUCT_A_CATEGORY', 'PRODUCT_A_BRAND', 'PRODUCT_B_CATEGORY', 'PRODUCT_B_BRAND', 
                 'SEGMENT', 'CONFIDENCE', 'LIFT', 'SUPPORT', 'AVG_BASKET_VALUE', 'CO_OCCURRENCE_COUNT']
            ].to_dict('records')
            
            # Calculate summary metrics
            avg_confidence = associations_df['CONFIDENCE'].mean()
            avg_lift = associations_df['LIFT'].mean()
            total_opportunities = len(associations_df)
            
            return {
                'top_opportunities': top_opportunities,
                'summary_metrics': {
                    'total_cross_sell_rules': total_opportunities,
                    'average_confidence': round(avg_confidence, 3),
                    'average_lift': round(avg_lift, 3),
                    'segment_filter': segment if segment else 'All Segments'
                },
                'segment_insights': analysis.get('segment_insights', {})
            }
            
        except Exception as e:
            logger.error(f"Failed to identify cross-sell opportunities: {str(e)}")
            return {'error': str(e)}
    
    def optimize_promotional_cross_sell_strategy(self, target_category: str = None) -> Dict[str, Any]:
        """Optimize promotional strategy for cross-sell effectiveness"""
        
        try:
            # Get promotional optimization results
            optimization = self.cross_sell_engine.optimize_promotional_cross_sell_campaigns()
            
            if 'error' in optimization:
                return optimization
            
            # Filter by target category if specified
            if target_category:
                filtered_recommendations = [
                    rec for rec in optimization['optimization_recommendations']
                    if rec['primary_category'] == target_category or rec['cross_sell_category'] == target_category
                ]
                optimization['optimization_recommendations'] = filtered_recommendations
                optimization['category_filter'] = target_category
            
            return optimization
            
        except Exception as e:
            logger.error(f"Failed to optimize promotional strategy: {str(e)}")
            return {'error': str(e)}
    
    def generate_campaign_cross_sell_targeting(self, campaign_type: str, target_segment: str = None) -> Dict[str, Any]:
        """Generate cross-sell targeting recommendations for specific campaign type"""
        
        try:
            # Get comprehensive analysis
            analysis = self.cross_sell_engine.generate_comprehensive_cross_sell_analysis()
            
            if 'association_rules' not in analysis:
                return {'error': 'No cross-sell data available for targeting'}
            
            associations_df = analysis['association_rules']
            
            # Filter by segment if specified
            if target_segment:
                associations_df = associations_df[associations_df['SEGMENT'] == target_segment]
            
            # Define campaign-specific targeting strategies
            campaign_strategies = {
                'new_product_launch': {
                    'focus': 'high_lift',
                    'min_lift': 1.5,
                    'strategy': 'Target products with strong cross-sell associations to drive adoption'
                },
                'seasonal_promotion': {
                    'focus': 'high_confidence',
                    'min_confidence': 0.3,
                    'strategy': 'Focus on proven product combinations with high purchase probability'
                },
                'customer_retention': {
                    'focus': 'high_basket_value',
                    'min_basket_value': associations_df['AVG_BASKET_VALUE'].median() if len(associations_df) > 0 else 0,
                    'strategy': 'Target high-value cross-sell opportunities to increase customer lifetime value'
                },
                'inventory_clearance': {
                    'focus': 'broad_appeal',
                    'min_support': 0.02,
                    'strategy': 'Target products with broad cross-sell appeal to move inventory'
                }
            }
            
            if campaign_type not in campaign_strategies:
                return {'error': f'Unsupported campaign type: {campaign_type}'}
            
            strategy = campaign_strategies[campaign_type]
            
            # Apply campaign-specific filters
            if strategy['focus'] == 'high_lift':
                targeted_rules = associations_df[associations_df['LIFT'] >= strategy['min_lift']]
            elif strategy['focus'] == 'high_confidence':
                targeted_rules = associations_df[associations_df['CONFIDENCE'] >= strategy['min_confidence']]
            elif strategy['focus'] == 'high_basket_value':
                targeted_rules = associations_df[associations_df['AVG_BASKET_VALUE'] >= strategy['min_basket_value']]
            elif strategy['focus'] == 'broad_appeal':
                targeted_rules = associations_df[associations_df['SUPPORT'] >= strategy['min_support']]
            else:
                targeted_rules = associations_df
            
            # Get top recommendations
            top_recommendations = targeted_rules.nlargest(10, strategy['focus'].split('_')[1].upper() if '_' in strategy['focus'] else 'CONFIDENCE')
            
            # Calculate campaign metrics
            total_potential_accounts = targeted_rules['CO_OCCURRENCE_COUNT'].sum()
            avg_basket_value = targeted_rules['AVG_BASKET_VALUE'].mean()
            total_potential_revenue = targeted_rules['TOTAL_BASKET_VALUE'].sum()
            
            return {
                'campaign_type': campaign_type,
                'targeting_strategy': strategy,
                'segment': target_segment if target_segment else 'All Segments',
                'recommendations': top_recommendations.to_dict('records'),
                'campaign_metrics': {
                    'total_targetable_accounts': int(total_potential_accounts),
                    'average_basket_value': round(avg_basket_value, 2),
                    'total_revenue_potential': round(total_potential_revenue, 2),
                    'recommendation_count': len(top_recommendations)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate campaign targeting: {str(e)}")
            return {'error': str(e)}


def main():
    """Test the cross-sell optimization engine"""
    print("🛒 Cross-Sell Optimization Engine")
    print("=" * 50)
    
    try:
        # Initialize Snowflake manager
        sf_manager = SnowflakeManager()
        if not sf_manager.connect():
            print("❌ Failed to connect to Snowflake")
            return
        
        print("✅ Connected to Snowflake")
        
        # Initialize cross-sell engine
        cross_sell_engine = CrossSellOptimizationEngine(sf_manager)
        
        # Generate comprehensive cross-sell analysis
        print("🔄 Generating comprehensive cross-sell analysis...")
        cross_sell_data = cross_sell_engine.generate_comprehensive_cross_sell_analysis()
        
        if 'association_rules' in cross_sell_data:
            rules_df = cross_sell_data['association_rules']
            print(f"✅ Analyzed {len(rules_df)} product association rules")
            
            # Display top opportunities
            if len(rules_df) > 0:
                print("\n📊 Top Cross-Sell Opportunities:")
                top_rules = rules_df.nlargest(5, 'CONFIDENCE')[
                    ['PRODUCT_A_CATEGORY', 'PRODUCT_B_CATEGORY', 'CONFIDENCE', 'LIFT', 'AVG_BASKET_VALUE']
                ]
                print(top_rules)
        
        # Test promotional analysis
        if 'promotional_analysis' in cross_sell_data:
            promo_df = cross_sell_data['promotional_analysis']
            print(f"\n🎯 Analyzed {len(promo_df)} promotional cross-sell combinations")
        
        # Save to Snowflake
        print("\n💾 Saving results to Snowflake...")
        success = cross_sell_engine.save_cross_sell_results_to_snowflake(cross_sell_data)
        if success:
            print("✅ Results saved successfully")
        else:
            print("❌ Failed to save results")
        
        # Test agent functionality
        print("\n🤖 Testing Cross-Sell Agent...")
        agent = CrossSellAgent(sf_manager)
        
        # Get sample account for testing
        accounts_query = "SELECT TOP 1 ACCOUNT_ID FROM ACCOUNTS WHERE HIERARCHY_LEVEL >= 2"
        sample_accounts = sf_manager.execute_query(accounts_query)
        
        if len(sample_accounts) > 0:
            sample_account_id = sample_accounts.iloc[0]['ACCOUNT_ID']
            
            # Test account-specific recommendations
            recommendations = agent.analyze_account_cross_sell_opportunities(sample_account_id)
            
            if 'error' not in recommendations:
                print(f"💡 Generated {len(recommendations['recommendations'])} recommendations for account {sample_account_id}")
                for rec in recommendations['recommendations'][:3]:  # Show top 3
                    print(f"  • {rec['trigger_category']} → {rec['recommended_category']} (Score: {rec['final_score']:.1f})")
        
        sf_manager.close_connection()
        print("\n🎉 Cross-sell analysis completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()