"""
Cross-Sell Optimization & Market Basket Analysis System

This package provides comprehensive cross-sell capabilities including:
- Market Basket Analysis for product associations
- Product Affinity Scoring and recommendations
- Promotional Integration and campaign optimization
- Cross-sell opportunity identification
- Interactive Dashboards and CLI Tools

Key Components:
- CrossSellOptimizationEngine: Core cross-sell logic and market basket analysis
- CrossSellAgent: AI-powered recommendation engine
- Interactive Dashboard: Streamlit-based visualization
- CLI Interface: Command-line tools for batch operations

Usage:
    from pmi_retail.cross_sell import CrossSellOptimizationEngine, CrossSellAgent
    from pmi_retail.database.snowflake.connection import SnowflakeManager
    
    # Initialize
    sf_manager = SnowflakeManager()
    sf_manager.connect()
    engine = CrossSellOptimizationEngine(sf_manager)
    
    # Generate cross-sell recommendations
    recommendations = engine.generate_cross_sell_recommendations()
    
    # Get account-specific recommendations
    agent = CrossSellAgent(sf_manager)
    account_recs = agent.get_account_recommendations('ACC0001')
"""

from .cross_sell_engine import CrossSellOptimizationEngine, CrossSellAgent

__all__ = [
    'CrossSellOptimizationEngine',
    'CrossSellAgent'
]

__version__ = "1.0.0"
__author__ = "PMI Workshop Team"
