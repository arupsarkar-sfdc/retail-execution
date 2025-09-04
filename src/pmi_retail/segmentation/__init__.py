"""
Real-Time Customer Segmentation & Propensity Scoring System

This package provides comprehensive customer segmentation capabilities including:
- RFM Analysis (Recency, Frequency, Monetary)
- Behavioral Segmentation (10 distinct customer segments)
- Product Propensity Scoring
- Engagement Metrics
- Campaign Targeting Recommendations
- Interactive Dashboards and CLI Tools

Key Components:
- RealTimeSegmentationEngine: Core segmentation logic
- SegmentationAgent: LangChain-based agent for interactive analysis
- Interactive Dashboard: Streamlit-based visualization
- CLI Interface: Command-line tools for batch operations

Usage:
    from pmi_retail.segmentation import RealTimeSegmentationEngine, SegmentationAgent
    from pmi_retail.database.snowflake.connection import SnowflakeManager
    
    # Initialize
    sf_manager = SnowflakeManager()
    sf_manager.connect()
    engine = RealTimeSegmentationEngine(sf_manager)
    
    # Generate segments
    segments = engine.generate_comprehensive_segments()
    
    # Get recommendations
    agent = SegmentationAgent(sf_manager)
    opportunities = agent.identify_high_value_opportunities()
"""

from .segmentation_engine import RealTimeSegmentationEngine, SegmentationAgent

__all__ = [
    'RealTimeSegmentationEngine',
    'SegmentationAgent'
]

__version__ = "1.0.0"
__author__ = "PMI Workshop Team"
