"""
CLI Interface for Cross-Sell Optimization Engine
Provides command-line access to cross-sell analysis and recommendations
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
import subprocess

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from pmi_retail.cross_sell.cross_sell_engine import CrossSellOptimizationEngine, CrossSellAgent
from pmi_retail.database.snowflake.connection import SnowflakeManager

app = typer.Typer(help="Cross-Sell Optimization CLI")
console = Console()

@app.command()
def analyze(
    lookback_days: int = typer.Option(365, help="Number of days to analyze"),
    save_to_snowflake: bool = typer.Option(True, help="Save results to Snowflake"),
    export_csv: bool = typer.Option(False, help="Export results to CSV files")
):
    """Run comprehensive cross-sell analysis"""
    console.print(Panel("🛒 Cross-Sell Optimization Analysis", style="blue"))
    
    try:
        # Initialize engine
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Initializing cross-sell engine...", total=None)
            
            sf_manager = SnowflakeManager()
            if not sf_manager.connect():
                console.print("[red]❌ Failed to connect to Snowflake[/red]")
                return
            
            engine = CrossSellOptimizationEngine(sf_manager)
            
            # Run analysis
            progress.update(task, description="Generating comprehensive cross-sell analysis...")
            cross_sell_data = engine.generate_comprehensive_cross_sell_analysis(lookback_days)
            
            if not cross_sell_data:
                console.print("[red]❌ No cross-sell data generated[/red]")
                return
            
            progress.update(task, description="✅ Analysis completed!")
        
        # Display results
        console.print(f"\n[green]✅ Cross-sell analysis completed for {lookback_days} days[/green]")
        
        # Display market basket analysis
        if 'market_basket' in cross_sell_data:
            basket_df = cross_sell_data['market_basket']
            console.print(f"\n🛍️ Market Basket Analysis:")
            console.print(f"   • Product combinations: {len(basket_df):,}")
            
            if 'CONFIDENCE' in basket_df.columns:
                avg_confidence = basket_df['CONFIDENCE'].mean()
                console.print(f"   • Average confidence: {avg_confidence:.2f}")
                
                high_confidence = len(basket_df[basket_df['CONFIDENCE'] > 0.5])
                console.print(f"   • High confidence rules: {high_confidence:,}")
        
        # Display product affinity
        if 'product_affinity' in cross_sell_data:
            affinity_df = cross_sell_data['product_affinity']
            console.print(f"\n🎯 Product Affinity Analysis:")
            console.print(f"   • Product pairs analyzed: {len(affinity_df):,}")
            
            if 'AFFINITY_SCORE' in affinity_df.columns:
                avg_affinity = affinity_df['AFFINITY_SCORE'].mean()
                console.print(f"   • Average affinity score: {avg_affinity:.2f}")
        
        # Save to Snowflake
        if save_to_snowflake:
            with console.status("💾 Saving results to Snowflake..."):
                success = engine.save_cross_sell_results_to_snowflake(cross_sell_data)
                if success:
                    console.print("[green]✅ Results saved to Snowflake tables[/green]")
                else:
                    console.print("[red]❌ Failed to save results to Snowflake[/red]")
        
        # Export to CSV
        if export_csv:
            export_dir = Path("data/exports/cross_sell")
            export_dir.mkdir(parents=True, exist_ok=True)
            
            # Export market basket analysis
            if 'market_basket' in cross_sell_data:
                basket_file = export_dir / f"market_basket_{lookback_days}days.csv"
                cross_sell_data['market_basket'].to_csv(basket_file, index=False)
                console.print(f"📄 Market basket analysis exported: {basket_file}")
            
            # Export product affinity
            if 'product_affinity' in cross_sell_data:
                affinity_file = export_dir / f"product_affinity_{lookback_days}days.csv"
                cross_sell_data['product_affinity'].to_csv(affinity_file, index=False)
                console.print(f"📄 Product affinity exported: {affinity_file}")
        
        sf_manager.close_connection()
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")

@app.command()
def dashboard():
    """Launch the cross-sell dashboard"""
    console.print(Panel("🛒 Cross-Sell Optimization Dashboard", style="blue"))
    
    dashboard_path = Path(__file__).parent / "cross_sell_dashboard.py"
    
    if not dashboard_path.exists():
        console.print(f"[red]❌ Dashboard not found at: {dashboard_path}[/red]")
        return
    
    try:
        console.print(f"[green]✅ Starting dashboard at: http://localhost:8502[/green]")
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(dashboard_path),
            "--server.port", "8502"
        ])
    except KeyboardInterrupt:
        console.print("[yellow]Dashboard stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Failed to launch dashboard: {str(e)}[/red]")

@app.command()
def account_recommendations(
    account_id: str = typer.Argument(..., help="Account ID to get recommendations for"),
    max_recommendations: int = typer.Option(5, help="Maximum number of recommendations")
):
    """Get product recommendations for a specific account"""
    console.print(Panel(f"🛒 Cross-Sell Recommendations for {account_id}", style="blue"))
    
    try:
        sf_manager = SnowflakeManager()
        if not sf_manager.connect():
            console.print("[red]❌ Failed to connect to Snowflake[/red]")
            return
        
        agent = CrossSellAgent(sf_manager)
        recommendations = agent.analyze_account_cross_sell_opportunities(account_id)
        
        if 'recommendations' in recommendations and recommendations['recommendations']:
            console.print(f"\n[green]✅ Found {len(recommendations['recommendations'])} recommendations[/green]")
            
            table = Table()
            table.add_column("Category", style="cyan")
            table.add_column("Brand", style="magenta")
            table.add_column("Confidence", justify="right", style="green")
            table.add_column("Lift", justify="right", style="yellow")
            table.add_column("Score", justify="right", style="blue")
            
            for rec in recommendations['recommendations']:
                table.add_row(
                    rec.get('recommended_category', 'N/A'),
                    rec.get('recommended_brand', 'N/A'),
                    f"{rec.get('confidence', 0):.3f}",
                    f"{rec.get('lift', 0):.2f}",
                    f"{rec.get('final_score', 0):.1f}"
                )
            
            console.print(table)
        else:
            console.print("[yellow]⚠️ No recommendations found for this account[/yellow]")
        
        sf_manager.close_connection()
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")

@app.command()
def market_basket(
    lookback_days: int = typer.Option(365, help="Number of days to analyze"),
    min_support: float = typer.Option(0.01, help="Minimum support threshold"),
    min_confidence: float = typer.Option(0.1, help="Minimum confidence threshold")
):
    """Generate market basket analysis"""
    console.print(Panel("🛍️ Market Basket Analysis", style="blue"))
    
    try:
        sf_manager = SnowflakeManager()
        if not sf_manager.connect():
            console.print("[red]❌ Failed to connect to Snowflake[/red]")
            return
        
        engine = CrossSellOptimizationEngine(sf_manager)
        engine.min_support = min_support
        engine.min_confidence = min_confidence
        
        with console.status("Analyzing market basket..."):
            basket_df = engine.calculate_market_basket_analysis(lookback_days)
        
        if len(basket_df) > 0:
            console.print(f"\n[green]✅ Found {len(basket_df)} association rules[/green]")
            
            # Display top rules
            top_rules = basket_df.nlargest(10, 'CONFIDENCE')
            
            table = Table()
            table.add_column("Antecedent", style="cyan")
            table.add_column("Consequent", style="magenta")
            table.add_column("Support", justify="right", style="green")
            table.add_column("Confidence", justify="right", style="yellow")
            table.add_column("Lift", justify="right", style="blue")
            
            for _, rule in top_rules.iterrows():
                table.add_row(
                    rule['ANTECEDENT'],
                    rule['CONSEQUENT'],
                    f"{rule['SUPPORT']:.3f}",
                    f"{rule['CONFIDENCE']:.3f}",
                    f"{rule['LIFT']:.2f}"
                )
            
            console.print(table)
        else:
            console.print("[yellow]⚠️ No association rules found[/yellow]")
        
        sf_manager.close_connection()
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")

@app.command()
def promotional_optimization(
    campaign_type: str = typer.Option("general", help="Type of promotional campaign"),
    lookback_days: int = typer.Option(365, help="Number of days to analyze")
):
    """Generate promotional optimization recommendations"""
    console.print(Panel("🎯 Promotional Optimization", style="blue"))
    
    try:
        sf_manager = SnowflakeManager()
        if not sf_manager.connect():
            console.print("[red]❌ Failed to connect to Snowflake[/red]")
            return
        
        agent = CrossSellAgent(sf_manager)
        
        with console.status("Generating promotional recommendations..."):
            recommendations = agent.generate_promotional_recommendations(campaign_type, lookback_days)
        
        if 'promotional_opportunities' in recommendations:
            opp_data = recommendations['promotional_opportunities']
            
            if opp_data:
                console.print(f"\n[green]✅ Found {len(opp_data)} promotional opportunities[/green]")
                
                for i, opp in enumerate(opp_data[:5], 1):  # Top 5
                    console.print(f"\n[bold]Opportunity {i}:[/bold] {opp.get('CAMPAIGN_NAME', 'Unknown Campaign')}")
                    console.print(f"  • Target Products: {opp.get('TARGET_PRODUCTS', 'N/A')}")
                    console.print(f"  • Expected Impact: {opp.get('EXPECTED_IMPACT', 'N/A')}")
                    console.print(f"  • Target Accounts: {opp.get('TARGET_ACCOUNTS', 0):,}")
                    console.print(f"  • Revenue Potential: ${opp.get('REVENUE_POTENTIAL', 0):,.2f}")
            else:
                console.print("[yellow]⚠️ No promotional opportunities found[/yellow]")
        else:
            console.print("[yellow]⚠️ No promotional data available[/yellow]")
        
        sf_manager.close_connection()
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")

@app.command()
def status():
    """Check cross-sell system status"""
    console.print(Panel("🔍 Cross-Sell System Status", style="blue"))
    
    try:
        sf_manager = SnowflakeManager()
        if not sf_manager.connect():
            console.print("[red]❌ Snowflake connection: Failed[/red]")
            return
        
        console.print("[green]✅ Snowflake connection: Active[/green]")
        
        # Check if cross-sell tables exist
        tables_to_check = [
            'CROSS_SELL_RECOMMENDATIONS',
            'MARKET_BASKET_ANALYSIS',
            'PRODUCT_AFFINITY_SCORES'
        ]
        
        for table in tables_to_check:
            try:
                result = sf_manager.execute_query(f"SELECT COUNT(*) FROM {table} LIMIT 1")
                if not result.empty:
                    count = result.iloc[0, 0]
                    console.print(f"[green]✅ Table {table}: {count:,} records[/green]")
                else:
                    console.print(f"[yellow]⚠️ Table {table}: Empty[/yellow]")
            except Exception:
                console.print(f"[red]❌ Table {table}: Not found[/red]")
        
        sf_manager.close_connection()
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")

@app.command()
def help_examples():
    """Show usage examples"""
    console.print(Panel("📚 Cross-Sell CLI Usage Examples", style="blue"))
    
    console.print("\n[bold]Basic Analysis:[/bold]")
    console.print("cross-sell analyze --lookback-days 365 --no-save-to-snowflake")
    console.print("cross-sell analyze --lookback-days 90 --export-csv")
    
    console.print("\n[bold]Account Recommendations:[/bold]")
    console.print("cross-sell account-recommendations ACC0001")
    console.print("cross-sell account-recommendations ACC0001 --max-recommendations 10")
    
    console.print("\n[bold]Market Basket Analysis:[/bold]")
    console.print("cross-sell market-basket --lookback-days 180")
    console.print("cross-sell market-basket --min-support 0.05 --min-confidence 0.2")
    
    console.print("\n[bold]Promotional Optimization:[/bold]")
    console.print("cross-sell promotional-optimization --campaign-type seasonal")
    console.print("cross-sell promotional-optimization --campaign-type new_product_launch")
    
    console.print("\n[bold]System Management:[/bold]")
    console.print("cross-sell status")
    console.print("cross-sell dashboard")

def main():
    """Entry point for the CLI application"""
    app()

if __name__ == "__main__":
    main()