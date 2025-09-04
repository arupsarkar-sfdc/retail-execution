"""
Real-Time Customer Segmentation Dashboard
Interactive Streamlit interface for the segmentation engine
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from pmi_retail.segmentation.segmentation_engine import RealTimeSegmentationEngine, SegmentationAgent
from pmi_retail.database.snowflake.connection import SnowflakeManager

# Page configuration
st.set_page_config(
    page_title="Real-Time Customer Segmentation",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #1f77b4;
}

.segment-header {
    font-size: 1.2rem;
    font-weight: bold;
    color: #1f77b4;
    margin-bottom: 0.5rem;
}

.opportunity-high { border-left-color: #d62728; }
.opportunity-medium { border-left-color: #ff7f0e; }
.opportunity-low { border-left-color: #2ca02c; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_segmentation_engine():
    """Initialize and cache the segmentation engine"""
    try:
        sf_manager = SnowflakeManager()
        if sf_manager.connect():
            return RealTimeSegmentationEngine(sf_manager), SegmentationAgent(sf_manager)
        else:
            st.error("Failed to connect to Snowflake")
            return None, None
    except Exception as e:
        st.error(f"Error initializing segmentation engine: {str(e)}")
        return None, None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_segmentation_data(lookback_days=365):
    """Load segmentation data with caching"""
    engine, agent = get_segmentation_engine()
    if engine is None:
        return None
    
    try:
        segments_data = engine.generate_comprehensive_segments(lookback_days)
        return segments_data
    except Exception as e:
        st.error(f"Error loading segmentation data: {str(e)}")
        return None

def create_rfm_scatter_plot(rfm_df):
    """Create 3D RFM scatter plot"""
    fig = go.Figure(data=[go.Scatter3d(
        x=rfm_df['RECENCY_DAYS'],
        y=rfm_df['FREQUENCY'],
        z=rfm_df['MONETARY_VALUE'],
        mode='markers',
        marker=dict(
            size=8,
            color=rfm_df['RFM_SCORE_NUMERIC'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="RFM Score")
        ),
        text=rfm_df['ACCOUNT_NAME'],
        hovertemplate='<b>%{text}</b><br>' +
                      'Recency: %{x} days<br>' +
                      'Frequency: %{y}<br>' +
                      'Monetary: $%{z:,.0f}<br>' +
                      '<extra></extra>'
    )])
    
    fig.update_layout(
        title='RFM Analysis - 3D Customer Distribution',
        scene=dict(
            xaxis_title='Recency (Days)',
            yaxis_title='Frequency',
            zaxis_title='Monetary Value ($)'
        ),
        height=600
    )
    
    return fig

def create_segment_distribution_chart(segment_summary):
    """Create segment distribution visualization"""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Account Count by Segment', 'Revenue Distribution', 
                       'Average RFM Score', 'Recent Spend Trend'),
        specs=[[{'type': 'bar'}, {'type': 'bar'}],
               [{'type': 'bar'}, {'type': 'bar'}]]
    )
    
    # Account count
    fig.add_trace(
        go.Bar(x=segment_summary['BEHAVIORAL_SEGMENT'], 
               y=segment_summary['ACCOUNT_COUNT'],
               name='Account Count',
               marker_color='lightblue'),
        row=1, col=1
    )
    
    # Revenue distribution
    fig.add_trace(
        go.Bar(x=segment_summary['BEHAVIORAL_SEGMENT'], 
               y=segment_summary['TOTAL_MONETARY_VALUE'],
               name='Total Revenue',
               marker_color='lightgreen'),
        row=1, col=2
    )
    
    # Average RFM Score
    fig.add_trace(
        go.Bar(x=segment_summary['BEHAVIORAL_SEGMENT'], 
               y=segment_summary['AVG_RFM_SCORE'],
               name='Avg RFM Score',
               marker_color='orange'),
        row=2, col=1
    )
    
    # Recent spend trend
    fig.add_trace(
        go.Bar(x=segment_summary['BEHAVIORAL_SEGMENT'], 
               y=segment_summary['AVG_SPEND_TREND_PCT'],
               name='Spend Trend %',
               marker_color='red'),
        row=2, col=2
    )
    
    fig.update_layout(height=600, showlegend=False)
    fig.update_xaxes(tickangle=45)
    
    return fig

def create_propensity_heatmap(propensity_df):
    """Create product propensity heatmap"""
    if len(propensity_df) == 0:
        return None
    
    # Aggregate by category for better visualization
    category_propensity = propensity_df.groupby(['ACCOUNT_ID', 'CATEGORY'])['PROPENSITY_SCORE'].mean().reset_index()
    pivot_df = category_propensity.pivot(index='ACCOUNT_ID', columns='CATEGORY', values='PROPENSITY_SCORE').fillna(0)
    
    # Limit to top 20 accounts for readability
    top_accounts = pivot_df.sum(axis=1).nlargest(20).index
    pivot_df = pivot_df.loc[top_accounts]
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=[f"Account {i+1}" for i in range(len(pivot_df))],  # Anonymous account labels
        colorscale='RdYlBu_r',
        hoverongaps=False,
        hovertemplate='Account: %{y}<br>Category: %{x}<br>Propensity Score: %{z:.1f}<extra></extra>'
    ))
    
    fig.update_layout(
        title='Product Category Propensity Scores (Top 20 Accounts)',
        xaxis_title='Product Category',
        yaxis_title='Accounts',
        height=500
    )
    
    return fig

def main():
    st.title("🎯 Real-Time Customer Segmentation Dashboard")
    st.markdown("Advanced RFM analysis and behavioral segmentation without Salesforce Data Cloud")
    
    # Sidebar controls
    st.sidebar.header("Analysis Parameters")
    lookback_days = st.sidebar.slider("Analysis Period (Days)", 30, 730, 365)
    refresh_data = st.sidebar.button("🔄 Refresh Analysis")
    
    # Load data
    if refresh_data:
        st.cache_data.clear()  # Clear cache to force refresh
    
    with st.spinner("Loading segmentation analysis..."):
        segments_data = load_segmentation_data(lookback_days)
    
    if segments_data is None:
        st.error("Unable to load segmentation data. Please check your Snowflake connection.")
        return
    
    if not segments_data or 'rfm_analysis' not in segments_data:
        st.warning("No segmentation data available. Please ensure you have transaction data in Snowflake.")
        return
    
    # Main dashboard
    rfm_df = segments_data['rfm_analysis']
    segment_summary = segments_data.get('segment_summary', pd.DataFrame())
    propensity_df = segments_data.get('product_propensity', pd.DataFrame())
    
    # Key metrics
    st.header("📊 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Accounts", f"{len(rfm_df):,}")
    
    with col2:
        total_revenue = rfm_df['MONETARY_VALUE'].sum()
        st.metric("Total Revenue", f"${total_revenue:,.0f}")
    
    with col3:
        avg_rfm = rfm_df['RFM_SCORE_NUMERIC'].mean()
        st.metric("Average RFM Score", f"{avg_rfm:.2f}")
    
    with col4:
        if len(segment_summary) > 0:
            top_segment = segment_summary.iloc[0]['BEHAVIORAL_SEGMENT']
            st.metric("Largest Segment", top_segment)
    
    # Segment overview
    st.header("🎯 Behavioral Segments")
    
    if len(segment_summary) > 0:
        # Create two columns for segment overview
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Segment distribution chart
            segment_chart = create_segment_distribution_chart(segment_summary)
            st.plotly_chart(segment_chart, use_container_width=True)
        
        with col2:
            # Segment priority table
            st.subheader("Segment Priorities")
            priority_df = segment_summary[['BEHAVIORAL_SEGMENT', 'ACCOUNT_COUNT', 'SEGMENT_PRIORITY']].copy()
            priority_df = priority_df.sort_values('SEGMENT_PRIORITY')
            
            for _, row in priority_df.iterrows():
                priority_class = "opportunity-high" if row['SEGMENT_PRIORITY'] <= 3 else "opportunity-medium" if row['SEGMENT_PRIORITY'] <= 6 else "opportunity-low"
                st.markdown(f"""
                <div class="metric-card {priority_class}">
                    <div class="segment-header">{row['BEHAVIORAL_SEGMENT']}</div>
                    <div>{row['ACCOUNT_COUNT']} accounts</div>
                </div>
                """, unsafe_allow_html=True)
    
    # RFM Analysis
    st.header("📈 RFM Analysis")
    
    # RFM 3D scatter plot
    rfm_chart = create_rfm_scatter_plot(rfm_df)
    st.plotly_chart(rfm_chart, use_container_width=True)
    
    # RFM distribution
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fig_r = px.histogram(rfm_df, x='R_QUINTILE', title='Recency Distribution')
        st.plotly_chart(fig_r, use_container_width=True)
    
    with col2:
        fig_f = px.histogram(rfm_df, x='F_QUINTILE', title='Frequency Distribution')
        st.plotly_chart(fig_f, use_container_width=True)
    
    with col3:
        fig_m = px.histogram(rfm_df, x='M_QUINTILE', title='Monetary Distribution')
        st.plotly_chart(fig_m, use_container_width=True)
    
    # Product Propensity Analysis
    if len(propensity_df) > 0:
        st.header("🛒 Product Propensity Analysis")
        
        propensity_chart = create_propensity_heatmap(propensity_df)
        if propensity_chart:
            st.plotly_chart(propensity_chart, use_container_width=True)
        
        # Top propensity opportunities
        st.subheader("Top Product Opportunities")
        top_propensity = propensity_df.nlargest(10, 'PROPENSITY_SCORE')[
            ['ACCOUNT_NAME', 'CATEGORY', 'BRAND', 'PROPENSITY_SCORE', 'LAST_PURCHASE_DATE']
        ]
        st.dataframe(top_propensity, use_container_width=True)
    
    # Business Opportunities
    st.header("💰 Business Opportunities")
    
    engine, agent = get_segmentation_engine()
    if agent:
        with st.spinner("Identifying high-value opportunities..."):
            opportunities = agent.identify_high_value_opportunities()
        
        if 'opportunities' in opportunities:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("At-Risk High Value Accounts")
                at_risk = opportunities['opportunities']['at_risk_high_value']
                if at_risk:
                    at_risk_df = pd.DataFrame(at_risk)
                    st.dataframe(at_risk_df, use_container_width=True)
                    total_at_risk = sum(acc['MONETARY_VALUE'] for acc in at_risk)
                    st.error(f"💸 Potential Revenue at Risk: ${total_at_risk:,.2f}")
                else:
                    st.success("✅ No high-value accounts at risk")
            
            with col2:
                st.subheader("Promising New Customers")
                new_customers = opportunities['opportunities']['promising_new_customers']
                if new_customers:
                    new_df = pd.DataFrame(new_customers)
                    st.dataframe(new_df, use_container_width=True)
                    st.info(f"🌟 {len(new_customers)} high-potential new customers identified")
                else:
                    st.info("No new customers with high potential identified")
        
        # Action recommendations
        if 'recommendations' in opportunities and opportunities['recommendations']:
            st.subheader("🎯 Recommended Actions")
            
            for rec in opportunities['recommendations']:
                priority_color = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}
                priority_icon = priority_color.get(rec['priority'], "⚪")
                
                st.markdown(f"""
                <div class="metric-card">
                    <div class="segment-header">{priority_icon} {rec['priority']} Priority - {rec['category']}</div>
                    <div><strong>Action:</strong> {rec['action']}</div>
                    <div><strong>Expected Impact:</strong> {rec['expected_impact']}</div>
                    <div><strong>Timeline:</strong> {rec['timeline']}</div>
                </div>
                """, unsafe_allow_html=True)
    
    # Account Deep Dive
    st.header("🔍 Account Deep Dive")
    
    account_names = rfm_df['ACCOUNT_NAME'].tolist()
    selected_account_name = st.selectbox("Select an account for detailed analysis:", account_names)
    
    if selected_account_name:
        selected_account_id = rfm_df[rfm_df['ACCOUNT_NAME'] == selected_account_name]['ACCOUNT_ID'].iloc[0]
        
        if agent:
            account_analysis = agent.analyze_account_segment(selected_account_id)
            
            if 'error' not in account_analysis:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Account Profile")
                    st.write(f"**Account:** {account_analysis['account_name']}")
                    st.write(f"**Current Segment:** {account_analysis['current_segment']}")
                    st.write(f"**RFM Score:** {account_analysis['rfm_score']}")
                
                with col2:
                    st.subheader("Recommendations")
                    for rec in account_analysis.get('recommendations', []):
                        priority_color = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
                        priority_icon = priority_color.get(rec['priority'].lower(), "⚪")
                        st.write(f"{priority_icon} **{rec['type'].title()}:** {rec['action']}")
                
                # Product opportunities for this account
                product_opps = account_analysis.get('top_product_opportunities', [])
                if product_opps:
                    st.subheader("Product Opportunities")
                    opps_df = pd.DataFrame(product_opps)
                    st.dataframe(opps_df, use_container_width=True)
            else:
                st.error(f"Error analyzing account: {account_analysis['error']}")
    
    # Campaign Targeting
    st.header("📢 Campaign Targeting Recommendations")
    
    campaign_types = ['promotional', 'premium', 'retention', 'acquisition']
    selected_campaign = st.selectbox("Select campaign type:", campaign_types)
    
    if agent and selected_campaign:
        targeting_recs = agent.generate_campaign_targeting_recommendations(selected_campaign)
        
        if 'strategy' in targeting_recs:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Campaign Strategy")
                strategy = targeting_recs['strategy']
                st.write(f"**Message:** {strategy['message']}")
                st.write(f"**Primary Targets:** {', '.join(strategy['primary_targets'])}")
                st.write(f"**Secondary Targets:** {', '.join(strategy['secondary_targets'])}")
                if strategy['avoid']:
                    st.write(f"**Avoid:** {', '.join(strategy['avoid'])}")
            
            with col2:
                st.subheader("Targeting Summary")
                summary = targeting_recs['targeting_summary']
                st.metric("Primary Target Accounts", summary['primary_count'])
                st.metric("Secondary Target Accounts", summary['secondary_count'])
                st.metric("Total Campaign Reach", summary['total_reach'])
        
        # Show target account lists
        if 'primary_targets' in targeting_recs and targeting_recs['primary_targets']:
            st.subheader("Primary Target Accounts")
            primary_df = pd.DataFrame(targeting_recs['primary_targets'])
            st.dataframe(primary_df, use_container_width=True)
    
    # Data Export
    st.header("💾 Export Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Export RFM Analysis"):
            csv = rfm_df.to_csv(index=False)
            st.download_button(
                label="Download RFM CSV",
                data=csv,
                file_name=f"rfm_analysis_{lookback_days}days.csv",
                mime="text/csv"
            )
    
    with col2:
        if len(segment_summary) > 0 and st.button("Export Segment Summary"):
            csv = segment_summary.to_csv(index=False)
            st.download_button(
                label="Download Segments CSV",
                data=csv,
                file_name=f"segment_summary_{lookback_days}days.csv",
                mime="text/csv"
            )
    
    with col3:
        if len(propensity_df) > 0 and st.button("Export Propensity Scores"):
            csv = propensity_df.to_csv(index=False)
            st.download_button(
                label="Download Propensity CSV",
                data=csv,
                file_name=f"propensity_scores_{lookback_days}days.csv",
                mime="text/csv"
            )
    
    # Technical Details
    with st.expander("🔧 Technical Implementation Details"):
        st.markdown("""
        **This segmentation system demonstrates:**
        
        **Without Salesforce Data Cloud:**
        - Custom RFM analysis using Snowflake SQL
        - Python-based behavioral segmentation algorithms
        - Real-time propensity scoring with machine learning
        - Manual campaign targeting logic
        - Custom dashboard development in Streamlit
        
        **Key Technical Components:**
        - Complex SQL queries for RFM calculations
        - Scikit-learn for clustering and classification
        - Custom business rules for segment assignment
        - Manual data pipeline orchestration
        - Custom visualization with Plotly
        
        **Data Sources:**
        - ACCOUNTS table (hierarchy and attributes)
        - TRANSACTIONS table (purchase history)
        - CAMPAIGNS table (marketing engagement)
        - LOYALTY_MEMBERS table (program participation)
        - CONTACTS table (customer demographics)
        
        **Refresh Frequency:** Currently manual refresh. In production, this would require:
        - Scheduled batch jobs (daily/weekly)
        - Data pipeline monitoring
        - Custom alerting for data quality issues
        - Manual model retraining and updates
        """)

if __name__ == "__main__":
    main()