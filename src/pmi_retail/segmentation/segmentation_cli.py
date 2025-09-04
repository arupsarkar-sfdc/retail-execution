"""
CLI Interface for Real-Time Customer Segmentation
Provides command-line access to segmentation capabilities
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import sys
from pathlib import Path
import json
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from pmi_retail.segmentation.segmentation_engine import RealTimeSegmentationEngine, SegmentationAgent
from pmi_retail.database.snowflake.connection import SnowflakeManager

app = typer.Typer(help="Real-Time Customer Segmentation CLI")
console = Console()

@app.command()
def analyze(
    lookback_days: int = typer.Option(365, help="Number of days to analyze"),
    save_to_snowflake: bool = typer.Option(True, help="Save results to Snowflake"),
    export_csv: bool = typer.Option(False, help="Export results to CSV files")
):
    """Run comprehensive segmentation analysis"""
    console.print(Panel("🎯 Real-Time Customer Segmentation Analysis", style="blue"))
    
    try:
        # Initialize engine
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Initializing segmentation engine...", total=None)
            
            sf_manager = SnowflakeManager()
            if not sf_manager.connect():
                console.print("[red]❌ Failed to connect to Snowflake[/red]")
                return
            
            engine = RealTimeSegmentationEngine(sf_manager)
            
            # Run analysis
            progress.update(task, description="Generating comprehensive segmentation...")
            segments_data = engine.generate_comprehensive_segments(lookback_days)
            
            if not segments_data or 'rfm_analysis' not in segments_data:
                console.print("[red]❌ No segmentation data generated[/red]")
                return
            
            progress.update(task, description="✅ Analysis completed!")
        
        # Display results
        rfm_df = segments_data['rfm_analysis']
        segment_summary = segments_data.get('segment_summary')
        
        console.print(f"\n[green]✅ Analyzed {len(rfm_df):,} accounts over {lookback_days} days[/green]")
        
        # Display segment summary
        if segment_summary is not None and len(segment_summary) > 0:
            console.print("\n📊 Behavioral Segment Summary:")
            
            table = Table()
            table.add_column("Segment", style="cyan")
            table.add_column("Accounts", justify="right", style="magenta")
            table.add_column("Avg Revenue", justify="right", style="green")
            table.add_column("Total Revenue", justify="right", style="green")
            table.add_column("Priority", justify="center", style="yellow")
            
            for _, row in segment_summary.iterrows():
                table.add_row(
                    row['BEHAVIORAL_SEGMENT'],
                    f"{row['ACCOUNT_COUNT']:,}",
                    f"${row['AVG_MONETARY_VALUE']:,.0f}",
                    f"${row['TOTAL_MONETARY_VALUE']:,.0f}",
                    str(row['SEGMENT_PRIORITY'])
                )
            
            console.print(table)
        
        # Display product propensity scores
        if 'product_propensity' in segments_data and len(segments_data['product_propensity']) > 0:
            propensity_df = segments_data['product_propensity']
            
            console.print("\n🎯 Top Product Propensity Scores:")
            
            # Get top 10 propensity scores
            top_propensity = propensity_df.nlargest(10, 'PROPENSITY_SCORE')
            
            table = Table()
            table.add_column("Account", style="cyan")
            table.add_column("Category", style="magenta")
            table.add_column("Brand", style="green")
            table.add_column("Propensity Score", justify="right", style="yellow")
            table.add_column("Affinity Score", justify="right", style="blue")
            table.add_column("Last Purchase", style="white")
            
            for _, row in top_propensity.iterrows():
                table.add_row(
                    row['ACCOUNT_NAME'][:20] + "..." if len(str(row['ACCOUNT_NAME'])) > 20 else str(row['ACCOUNT_NAME']),
                    str(row['CATEGORY']),
                    str(row['BRAND']),
                    f"{row['PROPENSITY_SCORE']:.1f}",
                    f"{row['CATEGORY_AFFINITY_SCORE']:.1f}",
                    str(row['LAST_PURCHASE_DATE']) if pd.notna(row['LAST_PURCHASE_DATE']) else 'N/A'
                )
            
            console.print(table)
            
            # Show propensity score distribution
            console.print(f"\n📊 Propensity Score Statistics:")
            console.print(f"   • Total product combinations: {len(propensity_df):,}")
            console.print(f"   • Average propensity score: {propensity_df['PROPENSITY_SCORE'].mean():.1f}")
            console.print(f"   • Highest propensity score: {propensity_df['PROPENSITY_SCORE'].max():.1f}")
            console.print(f"   • Accounts with high propensity (>80): {len(propensity_df[propensity_df['PROPENSITY_SCORE'] > 80]):,}")
        
        # Save to Snowflake
        if save_to_snowflake:
            with console.status("💾 Saving results to Snowflake..."):
                success = engine.save_segments_to_snowflake(segments_data)
                if success:
                    console.print("[green]✅ Results saved to Snowflake tables[/green]")
                else:
                    console.print("[red]❌ Failed to save results to Snowflake[/red]")
        
        # Export to CSV
        if export_csv:
            export_dir = Path("data/exports/segmentation")
            export_dir.mkdir(parents=True, exist_ok=True)
            
            # Export RFM analysis
            rfm_file = export_dir / f"rfm_analysis_{lookback_days}days.csv"
            rfm_df.to_csv(rfm_file, index=False)
            console.print(f"📄 RFM analysis exported: {rfm_file}")
            
            # Export segment summary
            if segment_summary is not None:
                summary_file = export_dir / f"segment_summary_{lookback_days}days.csv"
                segment_summary.to_csv(summary_file, index=False)
                console.print(f"📄 Segment summary exported: {summary_file}")
            
            # Export propensity scores
            if 'product_propensity' in segments_data:
                propensity_file = export_dir / f"propensity_scores_{lookback_days}days.csv"
                segments_data['product_propensity'].to_csv(propensity_file, index=False)
                console.print(f"📄 Propensity scores exported: {propensity_file}")
        
        sf_manager.close_connection()
        
    except Exception as e:
        console.print(f"[red]❌ Analysis failed: {str(e)}[/red]")

@app.command()
def account_profile(account_id: str):
    """Get detailed profile and recommendations for a specific account"""
    console.print(Panel(f"🔍 Account Profile Analysis: {account_id}", style="blue"))
    
    try:
        sf_manager = SnowflakeManager()
        if not sf_manager.connect():
            console.print("[red]❌ Failed to connect to Snowflake[/red]")
            return
        
        agent = SegmentationAgent(sf_manager)
        
        with console.status("Analyzing account..."):
            analysis = agent.analyze_account_segment(account_id)
        
        if 'error' in analysis:
            console.print(f"[red]❌ {analysis['error']}[/red]")
            return
        
        # Display account profile
        console.print(f"\n[cyan]Account:[/cyan] {analysis['account_name']}")
        console.print(f"[cyan]Current Segment:[/cyan] {analysis['current_segment']}")
        console.print(f"[cyan]RFM Score:[/cyan] {analysis['rfm_score']}")
        
        # Display recommendations
        if 'recommendations' in analysis and analysis['recommendations']:
            console.print("\n🎯 Recommendations:")
            
            for rec in analysis['recommendations']:
                priority_colors = {
                    'critical': 'red',
                    'high': 'yellow', 
                    'medium': 'blue',
                    'low': 'green'
                }
                color = priority_colors.get(rec['priority'].lower(), 'white')
                
                console.print(f"[{color}]• {rec['type'].upper()}[/{color}]: {rec['action']}")
        
        # Display product opportunities
        if 'top_product_opportunities' in analysis and analysis['top_product_opportunities']:
            console.print("\n🛒 Product Opportunities:")
            
            table = Table()
            table.add_column("Category", style="cyan")
            table.add_column("Brand", style="magenta")
            table.add_column("Propensity Score", justify="right", style="green")
            table.add_column("Last Purchase", style="yellow")
            
            for opp in analysis['top_product_opportunities'][:5]:  # Top 5
                table.add_row(
                    opp.get('CATEGORY', 'N/A'),
                    opp.get('BRAND', 'N/A'),
                    f"{opp.get('PROPENSITY_SCORE', 0):.1f}",
                    str(opp.get('LAST_PURCHASE_DATE', 'N/A'))
                )
            
            console.print(table)
        
        sf_manager.close_connection()
        
    except Exception as e:
        console.print(f"[red]❌ Account analysis failed: {str(e)}[/red]")

@app.command()
def opportunities():
    """Identify high-value business opportunities"""
    console.print(Panel("💰 High-Value Business Opportunities", style="blue"))
    
    try:
        sf_manager = SnowflakeManager()
        if not sf_manager.connect():
            console.print("[red]❌ Failed to connect to Snowflake[/red]")
            return
        
        agent = SegmentationAgent(sf_manager)
        
        with console.status("Identifying opportunities..."):
            opportunities = agent.identify_high_value_opportunities()
        
        if 'error' in opportunities:
            console.print(f"[red]❌ {opportunities['error']}[/red]")
            return
        
        # Display opportunity metrics
        if 'metrics' in opportunities:
            metrics = opportunities['metrics']
            console.print("\n📊 Opportunity Metrics:")
            console.print(f"• At-Risk Revenue: ${metrics.get('total_at_risk_value', 0):,.2f}")
            console.print(f"• New Customer Potential: {metrics.get('new_customer_potential', 0)} accounts")
            console.print(f"• Expansion Opportunities: {metrics.get('expansion_opportunities', 0)} accounts")
            console.print(f"• Reactivation Targets: {metrics.get('reactivation_targets', 0)} accounts")
        
        # Display recommendations
        if 'recommendations' in opportunities and opportunities['recommendations']:
            console.print("\n🎯 Action Recommendations:")
            
            for rec in opportunities['recommendations']:
                priority_colors = {
                    'Critical': 'red',
                    'High': 'yellow', 
                    'Medium': 'blue',
                    'Low': 'green'
                }
                color = priority_colors.get(rec['priority'], 'white')
                
                console.print(Panel(
                    f"[bold]{rec['action']}[/bold]\n\n"
                    f"Expected Impact: {rec['expected_impact']}\n"
                    f"Timeline: {rec['timeline']}",
                    title=f"[{color}]{rec['priority']} Priority - {rec['category']}[/{color}]",
                    border_style=color
                ))
        
        sf_manager.close_connection()
        
    except Exception as e:
        console.print(f"[red]❌ Opportunity analysis failed: {str(e)}[/red]")

@app.command()
def campaign_targeting(campaign_type: str):
    """Generate campaign targeting recommendations"""
    console.print(Panel(f"📢 Campaign Targeting: {campaign_type.title()}", style="blue"))
    
    valid_campaigns = ['promotional', 'premium', 'retention', 'acquisition']
    if campaign_type not in valid_campaigns:
        console.print(f"[red]❌ Invalid campaign type. Choose from: {', '.join(valid_campaigns)}[/red]")
        return
    
    try:
        sf_manager = SnowflakeManager()
        if not sf_manager.connect():
            console.print("[red]❌ Failed to connect to Snowflake[/red]")
            return
        
        agent = SegmentationAgent(sf_manager)
        
        with console.status("Generating targeting recommendations..."):
            targeting = agent.generate_campaign_targeting_recommendations(campaign_type)
        
        if 'error' in targeting:
            console.print(f"[red]❌ {targeting['error']}[/red]")
            return
        
        # Display strategy
        if 'strategy' in targeting:
            strategy = targeting['strategy']
            console.print(f"\n[cyan]Campaign Message:[/cyan] {strategy['message']}")
            console.print(f"[cyan]Primary Targets:[/cyan] {', '.join(strategy['primary_targets'])}")
            console.print(f"[cyan]Secondary Targets:[/cyan] {', '.join(strategy['secondary_targets'])}")
            if strategy['avoid']:
                console.print(f"[cyan]Avoid Segments:[/cyan] {', '.join(strategy['avoid'])}")
        
        # Display targeting summary
        if 'targeting_summary' in targeting:
            summary = targeting['targeting_summary']
            console.print(f"\n📊 Campaign Reach:")
            console.print(f"• Primary Targets: {summary['primary_count']:,} accounts")
            console.print(f"• Secondary Targets: {summary['secondary_count']:,} accounts")
            console.print(f"• Total Reach: {summary['total_reach']:,} accounts")
        
        # Display sample target accounts
        if 'primary_targets' in targeting and targeting['primary_targets']:
            console.print(f"\n🎯 Sample Primary Target Accounts:")
            
            table = Table()
            table.add_column("Account", style="cyan")
            table.add_column("Segment", style="magenta")
            table.add_column("RFM Score", justify="right", style="green")
            
            # Show first 10 accounts
            for account in targeting['primary_targets'][:10]:
                table.add_row(
                    account['ACCOUNT_NAME'][:30] + ('...' if len(account['ACCOUNT_NAME']) > 30 else ''),
                    account['BEHAVIORAL_SEGMENT'],
                    f"{account['RFM_SCORE_NUMERIC']:.2f}"
                )
            
            console.print(table)
            
            if len(targeting['primary_targets']) > 10:
                console.print(f"[dim]... and {len(targeting['primary_targets']) - 10} more accounts[/dim]")
        
        sf_manager.close_connection()
        
    except Exception as e:
        console.print(f"[red]❌ Campaign targeting failed: {str(e)}[/red]")

@app.command()
def dashboard():
    """Launch the Streamlit dashboard"""
    console.print(Panel("🚀 Launching Segmentation Dashboard", style="blue"))
    
    import subprocess
    import sys
    
    dashboard_path = Path(__file__).parent.parent.parent.parent / "streamlit_apps" / "segmentation_dashboard.py"
    
    if not dashboard_path.exists():
        console.print(f"[red]❌ Dashboard not found at: {dashboard_path}[/red]")
        return
    
    try:
        console.print(f"[green]✅ Starting dashboard at: http://localhost:8501[/green]")
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(dashboard_path),
            "--server.port", "8501"
        ])
    except KeyboardInterrupt:
        console.print("[yellow]Dashboard stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Failed to launch dashboard: {str(e)}[/red]")

@app.command()
def status():
    """Check segmentation system status"""
    console.print(Panel("🔍 Segmentation System Status", style="blue"))
    
    try:
        # Check database connection
        sf_manager = SnowflakeManager()
        if sf_manager.connect():
            console.print("[green]✅ Snowflake connection: Active[/green]")
            
            # Check if segmentation tables exist
            tables_to_check = [
                'ACCOUNT_SEGMENTATION_SCORES',
                'PRODUCT_PROPENSITY_SCORES',
                'SEGMENT_PERFORMANCE_SUMMARY'
            ]
            
            for table in tables_to_check:
                try:
                    result = sf_manager.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                    if result is not None and len(result) > 0:
                        count = result.iloc[0]['count']
                        console.print(f"[green]✅ {table}: {count:,} records[/green]")
                    else:
                        console.print(f"[yellow]⚠️ {table}: No data or query failed[/yellow]")
                except:
                    console.print(f"[red]❌ {table}: Not found or inaccessible[/red]")
            
            sf_manager.close_connection()
        else:
            console.print("[red]❌ Snowflake connection: Failed[/red]")
            return
        
        # Check if required source tables have data
        required_tables = ['ACCOUNTS', 'TRANSACTIONS', 'PRODUCTS']
        for table in required_tables:
            try:
                result = sf_manager.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                if result is not None and len(result) > 0:
                    count = result.iloc[0]['count']
                    if count > 0:
                        console.print(f"[green]✅ {table}: {count:,} records[/green]")
                    else:
                        console.print(f"[red]❌ {table}: Empty table[/red]")
                else:
                    console.print(f"[red]❌ {table}: Query failed[/red]")
            except:
                console.print(f"[red]❌ {table}: Not found[/red]")
        
    except Exception as e:
        console.print(f"[red]❌ Status check failed: {str(e)}[/red]")

def main():
    """Entry point for the CLI application"""
    app()

if __name__ == "__main__":
    main()