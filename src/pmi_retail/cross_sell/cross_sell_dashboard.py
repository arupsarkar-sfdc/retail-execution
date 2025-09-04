"""
Cross-Sell Optimization Dashboard
Interactive Streamlit interface for cross-sell analysis and recommendations
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from pmi_retail.cross_sell.cross_sell_engine import CrossSellOptimizationEngine, CrossSellAgent
from pmi_retail.database.snowflake.connection import SnowflakeManager

# Page configuration
st.set_page_config(
    page_title="Cross-Sell Optimization",
    page_icon="🛒",
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

.opportunity-high { border-left-color: #d62728; }
.opportunity-medium { border-left-color: #ff7f0e; }
.opportunity-low { border-left-color: #2ca02c; }

.recommendation-card {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #dee2e6;
    margin-bottom: 0.5rem;
}

.cross-sell-header {
    font-size: 1.2rem;
    font-weight: bold;
    color: #1f77b4;
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_cross_sell_engine():
    """Initialize and cache the cross-sell engine"""
    try:
        sf_manager = SnowflakeManager()
        if sf_manager.connect():
            return CrossSellOptimizationEngine(sf_manager), CrossSellAgent(sf_manager)
        else:
            st.error("Failed to connect to Snowflake")
            return None, None
    except Exception as e:
        st.error(f"Error initializing cross-sell engine: {str(e)}")
        return None, None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_cross_sell_data(lookback_days=365):
    """Load cross-sell data with caching"""
    engine, agent = get_cross_sell_engine()
    if engine is None:
        return None
    
    try:
        cross_sell_data = engine.generate_comprehensive_cross_sell_analysis(lookback_days)
        return cross_sell_data
    except Exception as e:
        st.error(f"Error loading cross-sell data: {str(e)}")
        return None

def create_association_rules_chart(rules_df):
    """Create scatter plot of association rules"""
    if len(rules_df) == 0:
        return None
    
    # Create scatter plot with confidence vs lift
    fig = px.scatter(
        rules_df,
        x='CONFIDENCE',
        y='LIFT',
        size='SUPPORT',
        color='SEGMENT',
        hover_data=['PRODUCT_A_CATEGORY', 'PRODUCT_B_CATEGORY', 'AVG_BASKET_VALUE'],
        title='Product Association Rules: Confidence vs Lift',
        labels={
            'CONFIDENCE': 'Confidence (Purchase Probability)',
            'LIFT': 'Lift (Association Strength)',
            'SUPPORT': 'Support (Frequency)'
        }
    )
    
    # Add threshold lines
    fig.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="Lift = 1.0 (No Association)")
    fig.add_vline(x=0.1, line_dash="dash", line_color="orange", annotation_text="Min Confidence Threshold")
    
    fig.update_layout(height=600)
    return fig

def create_promotional_effectiveness_chart(promo_df):
    """Create promotional effectiveness visualization"""
    if len(promo_df) == 0:
        return None
    
    # Create bar chart of top promotional campaigns
    top_promos = promo_df.nlargest(10, 'PROMOTION_EFFECTIVENESS')
    
    fig = px.bar(
        top_promos,
        x='PROMOTION_EFFECTIVENESS',
        y='CAMPAIGN_NAME',
        color='SEGMENT',
        hover_data=['CROSS_SELL_RATE', 'REVENUE_PER_ACCOUNT', 'AVG_DISCOUNT'],
        title='Top 10 Promotional Cross-Sell Campaigns by Effectiveness',
        orientation='h'
    )
    
    fig.update_layout(height=500)
    return fig

def create_cross_sell_network(rules_df, top_n=20):
    """Create network diagram of product relationships"""
    if len(rules_df) == 0:
        return None
    
    # Get top association rules
    top_rules = rules_df.nlargest(top_n, 'CONFIDENCE')
    
    # Create network data
    nodes = set()
    edges = []
    
    for _, rule in top_rules.iterrows():
        prod_a = f"{rule['PRODUCT_A_CATEGORY']}"
        prod_b = f"{rule['PRODUCT_B_CATEGORY']}"
        
        nodes.add(prod_a)
        nodes.add(prod_b)
        
        edges.append({
            'source': prod_a,
            'target': prod_b,
            'confidence': rule['CONFIDENCE'],
            'lift': rule['LIFT']
        })
    
    # For simplicity, create a chord diagram instead
    categories = list(nodes)
    matrix = np.zeros((len(categories), len(categories)))
    
    for edge in edges:
        try:
            source_idx = categories.index(edge['source'])
            target_idx = categories.index(edge['target'])
            matrix[source_idx][target_idx] = edge['confidence'] * 100
        except ValueError:
            continue
    
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=categories,
        y=categories,
        colorscale='Blues',
        hoverongaps=False,
        hovertemplate='From: %{y}<br>To: %{x}<br>Confidence: %{z:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title='Product Cross-Sell Affinity Matrix',
        xaxis_title='Target Products',
        yaxis_title='Primary Products',
        height=600
    )
    
    return fig

def create_opportunity_summary_chart(opportunity_df):
    """Create opportunity summary visualization"""
    if len(opportunity_df) == 0:
        return None
    
    # Create bubble chart
    fig = px.scatter(
        opportunity_df.head(20),  # Top 20 opportunities
        x='CONFIDENCE',
        y='LIFT',
        size='TOTAL_BASKET_VALUE',
        color='OPPORTUNITY_SCORE',
        hover_data=['PRODUCT_A_CATEGORY', 'PRODUCT_B_CATEGORY'],
        title='Top 20 Cross-Sell Opportunities',
        color_continuous_scale='Viridis'
    )
    
    fig.update_layout(height=500)
    return fig

def main():
    st.title("🛒 Cross-Sell Optimization Dashboard")
    st.markdown("Advanced product affinity analysis and promotional cross-sell optimization without Salesforce Einstein Next Best Action")
    
    # Sidebar controls
    st.sidebar.header("Analysis Parameters")
    lookback_days = st.sidebar.slider("Analysis Period (Days)", 90, 730, 365)
    refresh_data = st.sidebar.button("🔄 Refresh Analysis")
    
    # Analysis type selection
    analysis_type = st.sidebar.selectbox(
        "Analysis Focus",
        ["Overview", "Account Deep Dive", "Campaign Optimization", "Product Affinity"]
    )
    
    # Load data
    if refresh_data:
        st.cache_data.clear()  # Clear cache to force refresh
    
    with st.spinner("Loading cross-sell analysis..."):
        cross_sell_data = load_cross_sell_data(lookback_days)
    
    if cross_sell_data is None:
        st.error("Unable to load cross-sell data. Please check your Snowflake connection.")
        return
    
    if not cross_sell_data or 'association_rules' not in cross_sell_data:
        st.warning("No cross-sell data available. Please ensure you have transaction data in Snowflake.")
        return
    
    # Main dashboard content based on analysis type
    if analysis_type == "Overview":
        display_overview(cross_sell_data, lookback_days)
    elif analysis_type == "Account Deep Dive":
        display_account_deep_dive(cross_sell_data)
    elif analysis_type == "Campaign Optimization":
        display_campaign_optimization(cross_sell_data)
    elif analysis_type == "Product Affinity":
        display_product_affinity(cross_sell_data)

def display_overview(cross_sell_data, lookback_days):
    """Display overview dashboard"""
    rules_df = cross_sell_data['association_rules']
    promotional_df = cross_sell_data.get('promotional_analysis', pd.DataFrame())
    opportunity_df = cross_sell_data.get('opportunity_summary', pd.DataFrame())
    
    # Key metrics
    st.header("📊 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Association Rules", f"{len(rules_df):,}")
    
    with col2:
        avg_confidence = rules_df['CONFIDENCE'].mean() if len(rules_df) > 0 else 0
        st.metric("Avg Confidence", f"{avg_confidence:.3f}")
    
    with col3:
        avg_lift = rules_df['LIFT'].mean() if len(rules_df) > 0 else 0
        st.metric("Avg Lift", f"{avg_lift:.2f}")
    
    with col4:
        high_quality_rules = len(rules_df[(rules_df['CONFIDENCE'] > 0.2) & (rules_df['LIFT'] > 1.5)]) if len(rules_df) > 0 else 0
        st.metric("High-Quality Rules", high_quality_rules)
    
    # Association rules visualization
    st.header("🔗 Product Association Analysis")
    
    if len(rules_df) > 0:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Association rules scatter plot
            rules_chart = create_association_rules_chart(rules_df)
            if rules_chart:
                st.plotly_chart(rules_chart, use_container_width=True)
        
        with col2:
            # Top rules table
            st.subheader("Top Association Rules")
            top_rules = rules_df.nlargest(10, 'CONFIDENCE')[
                ['PRODUCT_A_CATEGORY', 'PRODUCT_B_CATEGORY', 'CONFIDENCE', 'LIFT']
            ]
            st.dataframe(top_rules, use_container_width=True, height=400)
    
    # Cross-sell network
    st.header("🌐 Cross-Sell Affinity Network")
    network_chart = create_cross_sell_network(rules_df)
    if network_chart:
        st.plotly_chart(network_chart, use_container_width=True)
    
    # Promotional analysis
    if len(promotional_df) > 0:
        st.header("🎯 Promotional Cross-Sell Performance")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            promo_chart = create_promotional_effectiveness_chart(promotional_df)
            if promo_chart:
                st.plotly_chart(promo_chart, use_container_width=True)
        
        with col2:
            st.subheader("Promotional Metrics")
            total_promo_revenue = promotional_df['TOTAL_CROSS_SELL_VALUE'].sum()
            avg_cross_sell_rate = promotional_df['CROSS_SELL_RATE'].mean()
            avg_effectiveness = promotional_df['PROMOTION_EFFECTIVENESS'].mean()
            
            st.metric("Total Promo Revenue", f"${total_promo_revenue:,.0f}")
            st.metric("Avg Cross-Sell Rate", f"{avg_cross_sell_rate:.3f}")
            st.metric("Avg Effectiveness", f"{avg_effectiveness:.1f}")
    
    # Opportunity summary
    if len(opportunity_df) > 0:
        st.header("💰 Cross-Sell Opportunities")
        
        opp_chart = create_opportunity_summary_chart(opportunity_df)
        if opp_chart:
            st.plotly_chart(opp_chart, use_container_width=True)
        
        # Opportunity breakdown
        col1, col2, col3 = st.columns(3)
        
        with col1:
            high_opp = len(opportunity_df[opportunity_df['OPPORTUNITY_SCORE'] > 75])
            st.metric("High Opportunities", high_opp, help="Opportunity Score > 75")
        
        with col2:
            medium_opp = len(opportunity_df[(opportunity_df['OPPORTUNITY_SCORE'] > 50) & (opportunity_df['OPPORTUNITY_SCORE'] <= 75)])
            st.metric("Medium Opportunities", medium_opp, help="Opportunity Score 50-75")
        
        with col3:
            total_potential = opportunity_df['TOTAL_BASKET_VALUE'].sum()
            st.metric("Total Potential Value", f"${total_potential:,.0f}")

def display_account_deep_dive(cross_sell_data):
    """Display account-specific cross-sell analysis"""
    st.header("🔍 Account Cross-Sell Deep Dive")
    
    # Account selection
    engine, agent = get_cross_sell_engine()
    if not agent:
        st.error("Could not initialize cross-sell agent")
        return
    
    # Get list of accounts
    try:
        accounts_query = """
        SELECT DISTINCT a.ACCOUNT_ID, a.ACCOUNT_NAME, a.SEGMENT
        FROM ACCOUNTS a
        JOIN TRANSACTIONS t ON a.ACCOUNT_ID = t.ACCOUNT_ID
        WHERE a.HIERARCHY_LEVEL >= 2 OR a.ACCOUNT_TYPE = 'Independent'
        ORDER BY a.ACCOUNT_NAME
        LIMIT 100
        """
        
        sf_manager = SnowflakeManager()
        sf_manager.connect()
        accounts_df = sf_manager.execute_query(accounts_query)
        
        if len(accounts_df) == 0:
            st.warning("No accounts found with transaction history")
            return
        
        # Account selection
        selected_account = st.selectbox(
            "Select Account for Analysis",
            accounts_df['ACCOUNT_ID'].tolist(),
            format_func=lambda x: f"{accounts_df[accounts_df['ACCOUNT_ID']==x]['ACCOUNT_NAME'].iloc[0]} ({x})"
        )
        
        include_promotions = st.checkbox("Include Promotional Context", value=True)
        
        if st.button("Analyze Account"):
            with st.spinner("Generating account recommendations..."):
                recommendations = agent.analyze_account_cross_sell_opportunities(selected_account, include_promotions)
            
            if 'error' in recommendations:
                st.error(recommendations['error'])
                return
            
            # Account profile
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Account", recommendations['account_name'])
            
            with col2:
                st.metric("Segment", recommendations['segment'])
            
            with col3:
                st.metric("Categories Purchased", len(recommendations['purchased_categories']))
            
            # Purchased categories
            st.subheader("Purchase History")
            categories_text = ", ".join(recommendations['purchased_categories'])
            st.info(f"**Categories:** {categories_text}")
            
            # Recommendations
            if recommendations['recommendations']:
                st.subheader("🎯 Cross-Sell Recommendations")
                
                for i, rec in enumerate(recommendations['recommendations'], 1):
                    score_color = "high" if rec['final_score'] >= 70 else "medium" if rec['final_score'] >= 50 else "low"
                    
                    st.markdown(f"""
                    <div class="recommendation-card opportunity-{score_color}">
                        <div class="cross-sell-header">#{i} {rec['recommended_category']} - {rec['recommended_brand']}</div>
                        <div><strong>Trigger:</strong> {rec['trigger_category']}</div>
                        <div><strong>Score:</strong> {rec['final_score']:.1f} (Confidence: {rec['confidence']:.3f}, Lift: {rec['lift']:.2f})</div>
                        <div><strong>Promotional Boost:</strong> {rec['promotional_boost']:.1f}x</div>
                        <div><strong>Expected Basket Value:</strong> ${rec['avg_basket_value']:,.0f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show suggested products
                    if rec.get('suggested_products'):
                        with st.expander(f"Suggested {rec['recommended_category']} Products"):
                            products_df = pd.DataFrame(rec['suggested_products'])
                            st.dataframe(products_df, use_container_width=True)
            else:
                st.warning("No cross-sell recommendations found for this account")
            
            # Active promotions
            if recommendations['active_promotions']:
                st.subheader("🎁 Active Promotions")
                for promo in recommendations['active_promotions'][:5]:
                    discount = promo.get('DISCOUNT_PERCENTAGE', 0)
                    st.info(f"**{promo['CAMPAIGN_NAME']}** ({promo['CAMPAIGN_TYPE']}) - {discount}% discount")
        
        sf_manager.close_connection()
        
    except Exception as e:
        st.error(f"Error in account analysis: {str(e)}")

def display_campaign_optimization(cross_sell_data):
    """Display campaign optimization analysis"""
    st.header("🚀 Campaign Cross-Sell Optimization")
    
    engine, agent = get_cross_sell_engine()
    if not agent:
        st.error("Could not initialize cross-sell agent")
        return
    
    # Campaign type selection
    campaign_types = {
        'new_product_launch': 'New Product Launch',
        'seasonal_promotion': 'Seasonal Promotion', 
        'customer_retention': 'Customer Retention',
        'inventory_clearance': 'Inventory Clearance'
    }
    
    selected_campaign = st.selectbox("Select Campaign Type", list(campaign_types.keys()), 
                                   format_func=lambda x: campaign_types[x])
    
    # Segment filter
    rules_df = cross_sell_data.get('association_rules', pd.DataFrame())
    segments = ['All'] + list(rules_df['SEGMENT'].unique()) if len(rules_df) > 0 else ['All']
    selected_segment = st.selectbox("Target Segment", segments)
    
    segment_filter = None if selected_segment == 'All' else selected_segment
    
    if st.button("Generate Campaign Strategy"):
        with st.spinner("Generating campaign targeting strategy..."):
            targeting = agent.generate_campaign_cross_sell_targeting(selected_campaign, segment_filter)
        
        if 'error' in targeting:
            st.error(targeting['error'])
            return
        
        # Display strategy
        if 'targeting_strategy' in targeting:
            strategy = targeting['targeting_strategy']
            
            st.subheader("📋 Campaign Strategy")
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"**Focus:** {strategy['focus'].replace('_', ' ').title()}")
                st.info(f"**Segment:** {targeting['segment']}")
            
            with col2:
                st.success(f"**Strategy:** {strategy['strategy']}")
        
        # Campaign metrics
        if 'campaign_metrics' in targeting:
            metrics = targeting['campaign_metrics']
            
            st.subheader("📊 Campaign Potential")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Targetable Accounts", f"{metrics['total_targetable_accounts']:,}")
            
            with col2:
                st.metric("Avg Basket Value", f"${metrics['average_basket_value']:,.2f}")
            
            with col3:
                st.metric("Revenue Potential", f"${metrics['total_revenue_potential']:,.0f}")
            
            with col4:
                st.metric("Recommendations", metrics['recommendation_count'])
        
        # Top recommendations
        if 'recommendations' in targeting and targeting['recommendations']:
            st.subheader("🎯 Top Cross-Sell Targets")
            
            recs_df = pd.DataFrame(targeting['recommendations'][:15])  # Top 15
            
            # Create interactive chart
            fig = px.scatter(
                recs_df,
                x='CONFIDENCE',
                y='LIFT',
                size='AVG_BASKET_VALUE',
                color='SEGMENT',
                hover_data=['PRODUCT_A_CATEGORY', 'PRODUCT_B_CATEGORY'],
                title=f'{campaign_types[selected_campaign]} - Cross-Sell Targets'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Detailed table
            display_df = recs_df[['PRODUCT_A_CATEGORY', 'PRODUCT_B_CATEGORY', 'SEGMENT', 
                                 'CONFIDENCE', 'LIFT', 'AVG_BASKET_VALUE']].round(3)
            st.dataframe(display_df, use_container_width=True)
    
    # Promotional optimization
    st.subheader("📈 Promotional Optimization")
    
    if st.button("Analyze Promotional Effectiveness"):
        with st.spinner("Analyzing promotional cross-sell effectiveness..."):
            optimization = agent.optimize_promotional_cross_sell_strategy()
        
        if 'error' not in optimization and 'performance_metrics' in optimization:
            metrics = optimization['performance_metrics']
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Cross-Sell Revenue", f"${metrics['total_cross_sell_revenue']:,.0f}")
            
            with col2:
                st.metric("Total Discount Cost", f"${metrics['total_discount_cost']:,.0f}")
            
            with col3:
                roi = metrics['promotional_roi']
                st.metric("Promotional ROI", f"{roi:.1f}%", delta=f"{roi-100:.1f}%")
            
            # Optimization recommendations
            if 'optimization_recommendations' in optimization:
                st.subheader("💡 Optimization Recommendations")
                
                for rec in optimization['optimization_recommendations'][:5]:
                    priority_colors = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
                    priority_icon = priority_colors.get(rec['priority'].lower(), '⚪')
                    
                    st.markdown(f"""
                    <div class="recommendation-card">
                        <div class="cross-sell-header">{priority_icon} {rec['priority'].upper()} - {rec['type'].replace('_', ' ').title()}</div>
                        <div><strong>Categories:</strong> {rec['primary_category']} → {rec['cross_sell_category']}</div>
                        <div><strong>Recommendation:</strong> {rec['recommendation']}</div>
                        <div><strong>Expected Impact:</strong> {rec['expected_impact']}</div>
                    </div>
                    """, unsafe_allow_html=True)

def display_product_affinity(cross_sell_data):
    """Display detailed product affinity analysis"""
    st.header("🔗 Product Affinity Analysis")
    
    rules_df = cross_sell_data.get('association_rules', pd.DataFrame())
    
    if len(rules_df) == 0:
        st.warning("No association rules data available")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        segments = ['All'] + list(rules_df['SEGMENT'].unique())
        selected_segment = st.selectbox("Filter by Segment", segments)
    
    with col2:
        categories = ['All'] + list(set(rules_df['PRODUCT_A_CATEGORY'].unique()) | set(rules_df['PRODUCT_B_CATEGORY'].unique()))
        selected_category = st.selectbox("Filter by Category", categories)
    
    with col3:
        min_confidence = st.slider("Minimum Confidence", 0.0, 1.0, 0.1, 0.01)
    
    # Apply filters
    filtered_df = rules_df.copy()
    
    if selected_segment != 'All':
        filtered_df = filtered_df[filtered_df['SEGMENT'] == selected_segment]
    
    if selected_category != 'All':
        filtered_df = filtered_df[
            (filtered_df['PRODUCT_A_CATEGORY'] == selected_category) |
            (filtered_df['PRODUCT_B_CATEGORY'] == selected_category)
        ]
    
    filtered_df = filtered_df[filtered_df['CONFIDENCE'] >= min_confidence]
    
    if len(filtered_df) == 0:
        st.warning("No rules match the selected filters")
        return
    
    # Affinity metrics
    st.subheader("📊 Affinity Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Rules Found", len(filtered_df))
    
    with col2:
        avg_confidence = filtered_df['CONFIDENCE'].mean()
        st.metric("Avg Confidence", f"{avg_confidence:.3f}")
    
    with col3:
        avg_lift = filtered_df['LIFT'].mean()
        st.metric("Avg Lift", f"{avg_lift:.2f}")
    
    with col4:
        total_value = filtered_df['TOTAL_BASKET_VALUE'].sum()
        st.metric("Total Value Potential", f"${total_value:,.0f}")
    
    # Detailed affinity analysis
    st.subheader("🔍 Detailed Affinity Analysis")
    
    # Top affinities by confidence
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Top Affinities by Confidence**")
        top_confidence = filtered_df.nlargest(10, 'CONFIDENCE')[
            ['PRODUCT_A_CATEGORY', 'PRODUCT_B_CATEGORY', 'CONFIDENCE', 'LIFT', 'SUPPORT']
        ]
        st.dataframe(top_confidence, use_container_width=True)
    
    with col2:
        st.write("**Top Affinities by Lift**")
        top_lift = filtered_df.nlargest(10, 'LIFT')[
            ['PRODUCT_A_CATEGORY', 'PRODUCT_B_CATEGORY', 'CONFIDENCE', 'LIFT', 'SUPPORT']
        ]
        st.dataframe(top_lift, use_container_width=True)
    
    # Category-level affinity heatmap
    st.subheader("🌡️ Category Affinity Heatmap")
    
    # Create category-level aggregation
    category_affinity = filtered_df.groupby(['PRODUCT_A_CATEGORY', 'PRODUCT_B_CATEGORY']).agg({
        'CONFIDENCE': 'mean',
        'LIFT': 'mean',
        'SUPPORT': 'mean'
    }).reset_index()
    
    # Create pivot for heatmap
    confidence_pivot = category_affinity.pivot(
        index='PRODUCT_A_CATEGORY', 
        columns='PRODUCT_B_CATEGORY', 
        values='CONFIDENCE'
    ).fillna(0)
    
    if not confidence_pivot.empty:
        fig = go.Figure(data=go.Heatmap(
            z=confidence_pivot.values,
            x=confidence_pivot.columns,
            y=confidence_pivot.index,
            colorscale='Blues',
            hoverongaps=False,
            hovertemplate='Primary: %{y}<br>Cross-Sell: %{x}<br>Confidence: %{z:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title='Category Cross-Sell Confidence Matrix',
            xaxis_title='Cross-Sell Categories',
            yaxis_title='Primary Categories',
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Segment comparison
    if selected_segment == 'All':
        st.subheader("📈 Segment Comparison")
        
        segment_comparison = rules_df.groupby('SEGMENT').agg({
            'CONFIDENCE': ['mean', 'count'],
            'LIFT': 'mean',
            'AVG_BASKET_VALUE': 'mean'
        }).round(3)
        
        segment_comparison.columns = ['Avg_Confidence', 'Rule_Count', 'Avg_Lift', 'Avg_Basket_Value']
        segment_comparison = segment_comparison.reset_index()
        
        # Create comparison chart
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Avg Confidence by Segment', 'Rule Count by Segment',
                          'Avg Lift by Segment', 'Avg Basket Value by Segment'),
            specs=[[{'type': 'bar'}, {'type': 'bar'}],
                   [{'type': 'bar'}, {'type': 'bar'}]]
        )
        
        fig.add_trace(
            go.Bar(x=segment_comparison['SEGMENT'], y=segment_comparison['Avg_Confidence'], name='Confidence'),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(x=segment_comparison['SEGMENT'], y=segment_comparison['Rule_Count'], name='Rule Count'),
            row=1, col=2
        )
        
        fig.add_trace(
            go.Bar(x=segment_comparison['SEGMENT'], y=segment_comparison['Avg_Lift'], name='Lift'),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(x=segment_comparison['SEGMENT'], y=segment_comparison['Avg_Basket_Value'], name='Basket Value'),
            row=2, col=2
        )
        
        fig.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Segment insights table
        st.write("**Segment Performance Summary**")
        st.dataframe(segment_comparison, use_container_width=True)
    
    # Export functionality
    st.header("💾 Export Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Export Filtered Rules"):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="filtered_association_rules.csv",
                mime="text/csv"
            )
    
    with col2:
        if len(cross_sell_data.get('promotional_analysis', [])) > 0:
            if st.button("Export Promotional Analysis"):
                csv = cross_sell_data['promotional_analysis'].to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="promotional_cross_sell_analysis.csv",
                    mime="text/csv"
                )
    
    with col3:
        if len(cross_sell_data.get('opportunity_summary', [])) > 0:
            if st.button("Export Opportunities"):
                csv = cross_sell_data['opportunity_summary'].to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="cross_sell_opportunities.csv",
                    mime="text/csv"
                )
    
    # Technical Implementation Details
    with st.expander("🔧 Technical Implementation Details"):
        st.markdown("""
        **This cross-sell optimization system demonstrates:**
        
        **Without Salesforce Data Cloud/Einstein Next Best Action:**
        - Custom market basket analysis using complex SQL queries on Snowflake
        - Manual association rule mining (Apriori algorithm implementation)
        - Custom product affinity matrix calculations using collaborative filtering
        - Manual promotional effectiveness analysis and optimization
        - Custom cross-sell recommendation engine with promotional context
        - Manual A/B testing framework for promotional campaigns
        - Custom dashboard development in Streamlit with Plotly visualizations
        
        **Key Technical Components:**
        - Complex SQL queries analyzing TRANSACTIONS, PRODUCTS, CAMPAIGNS tables
        - Python-based association rule mining with confidence, lift, and support metrics
        - Custom promotional boost calculations based on campaign performance
        - Manual segment-specific recommendation strategies
        - Custom opportunity scoring combining multiple business metrics
        - Manual model performance monitoring and optimization
        
        **Data Processing Pipeline:**
        1. Market basket analysis on transaction co-occurrence patterns
        2. Product affinity matrix creation using cosine similarity
        3. Promotional impact analysis linking campaigns to cross-sell performance  
        4. Account-specific recommendation generation with promotional context
        5. Campaign optimization based on historical cross-sell effectiveness
        
        **Refresh Requirements:** 
        - Manual analysis refresh (currently every 5 minutes cache)
        - Custom data pipeline orchestration needed for production
        - Manual model retraining and parameter tuning
        - Custom alerting for data quality and performance issues
        
        **With Salesforce Data Cloud + Einstein Next Best Action:**
        - Out-of-the-box ML-powered product affinity modeling
        - Native promotional campaign integration and optimization
        - Automated real-time recommendation scoring
        - Built-in A/B testing and performance analytics
        - Automatic model updates and drift detection
        - Native customer journey orchestration
        """)

if __name__ == "__main__":
    main()