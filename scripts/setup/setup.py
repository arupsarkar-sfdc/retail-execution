"""
PMI Workshop Setup CLI Script
Provides command-line interface for workshop setup tasks
"""

import typer
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

app = typer.Typer(help="PMI Workshop Setup and Management CLI")
console = Console()

@app.command()
def test_connection():
    """Test Snowflake connection with current settings"""
    console.print(Panel("🧪 Testing Snowflake Connection", style="blue"))
    
    try:
        from src.pmi_retail.database.snowflake.connection import SnowflakeManager
        from src.pmi_retail.config import settings
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Connecting to Snowflake...", total=None)
            
            sf = SnowflakeManager()
            if sf.connect():
                progress.update(task, description="✅ Connected! Testing query...")
                
                # Test query
                result = sf.execute_query("SELECT CURRENT_VERSION() as VERSION, CURRENT_USER() as USER")
                
                if result is not None and len(result) > 0:
                    progress.update(task, description="✅ Connection test successful!")
                    
                    console.print("\n[green]✅ Connection Details:[/green]")
                    console.print(f"• Database: {settings.snowflake_database}")
                    console.print(f"• Schema: {settings.snowflake_schema}")  
                    console.print(f"• Warehouse: {settings.snowflake_warehouse}")
                    console.print(f"• User: {result.iloc[0]['USER']}")
                    console.print(f"• Version: {result.iloc[0]['VERSION']}")
                    
                    sf.close_connection()
                    return True
                else:
                    console.print("[red]❌ Query test failed[/red]")
                    return False
            else:
                console.print("[red]❌ Connection failed[/red]")
                return False
                
    except Exception as e:
        console.print(f"[red]❌ Connection test failed: {str(e)}[/red]")
        console.print("\n[yellow]💡 Check your .env file configuration:[/yellow]")
        console.print("• SNOWFLAKE_USER")
        console.print("• SNOWFLAKE_PASSWORD")
        console.print("• SNOWFLAKE_ACCOUNT")
        return False


@app.command()
def init_database(drop_existing: bool = typer.Option(False, "--drop", help="Drop existing tables first")):
    """Initialize PMI workshop database tables"""
    console.print(Panel("🏗️ Initializing PMI Workshop Database", style="blue"))
    
    if drop_existing:
        console.print("[yellow]⚠️ WARNING: This will drop all existing PMI workshop tables![/yellow]")
        if not typer.confirm("Are you sure you want to continue?"):
            console.print("❌ Operation cancelled")
            return
    
    try:
        from src.pmi_retail.database.snowflake.table_builder import PMITableBuilder
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Initializing database...", total=None)
            
            builder = PMITableBuilder()
            
            # Connect
            progress.update(task, description="Connecting to Snowflake...")
            if not builder.connect():
                console.print("[red]❌ Failed to connect to Snowflake[/red]")
                return False
            
            # Create tables
            progress.update(task, description="Creating database tables...")
            success = builder.create_all_tables(drop_existing=drop_existing)
            
            if success:
                progress.update(task, description="✅ Database initialization complete!")
                
                # Show table summary
                console.print("\n")
                builder.get_table_summary()
                
                console.print(Panel(
                    "[green]🎉 Database setup completed successfully![/green]\n\n"
                    "Next steps:\n"
                    "• Run: [bold]uv run pmi-setup load-sample-data[/bold]\n"
                    "• Test: [bold]uv run pmi-setup test-queries[/bold]",
                    title="Success",
                    style="green"
                ))
                
                builder.close()
                return True
            else:
                console.print("[red]❌ Database initialization failed[/red]")
                builder.close()
                return False
                
    except Exception as e:
        console.print(f"[red]❌ Setup failed: {str(e)}[/red]")
        return False


@app.command()
def load_sample_data(scale: str = typer.Option("small", help="Data scale: small, medium, large")):
    """Load sample data into PMI workshop tables"""
    console.print(Panel(f"📊 Loading Sample Data (Scale: {scale})", style="blue"))
    
    try:
        from src.pmi_retail.utils.data_generator import PMIDataGenerator
        from src.pmi_retail.database.snowflake.connection import SnowflakeManager
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Loading sample data...", total=None)
            
            # Connect to Snowflake
            progress.update(task, description="Connecting to Snowflake...")
            sf = SnowflakeManager()
            if not sf.connect():
                console.print("[red]❌ Failed to connect to Snowflake[/red]")
                return False
            
            # Initialize data generator
            data_gen = PMIDataGenerator(sf, scale=scale)
            
            # Generate and load data
            progress.update(task, description="Generating sample accounts...")
            data_gen.generate_and_load_accounts()
            
            progress.update(task, description="Generating sample products...")
            data_gen.generate_and_load_products()
            
            progress.update(task, description="Generating sample transactions...")
            data_gen.generate_and_load_transactions()
            
            progress.update(task, description="Generating loyalty members...")
            data_gen.generate_and_load_loyalty_members()
            
            progress.update(task, description="✅ Sample data loaded successfully!")
            
        # Show data summary
        console.print("\n[green]✅ Sample data loading completed![/green]")
        
        # Get row counts
        summary_query = """
        SELECT 'ACCOUNTS' as TABLE_NAME, COUNT(*) as ROW_COUNT FROM ACCOUNTS
        UNION ALL
        SELECT 'PRODUCTS' as TABLE_NAME, COUNT(*) as ROW_COUNT FROM PRODUCTS
        UNION ALL
        SELECT 'TRANSACTIONS' as TABLE_NAME, COUNT(*) as ROW_COUNT FROM TRANSACTIONS
        UNION ALL
        SELECT 'LOYALTY_MEMBERS' as TABLE_NAME, COUNT(*) as ROW_COUNT FROM LOYALTY_MEMBERS
        """
        
        result = sf.execute_query(summary_query)
        if result is not None:
            console.print("\n📊 Data Summary:")
            for _, row in result.iterrows():
                console.print(f"• {row['TABLE_NAME']}: {row['ROW_COUNT']:,} rows")
        
        sf.close_connection()
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Data loading failed: {str(e)}[/red]")
        return False


@app.command()
def test_queries():
    """Run test queries to validate the database setup"""
    console.print(Panel("🧪 Running Test Queries", style="blue"))
    
    try:
        from src.pmi_retail.database.snowflake.connection import SnowflakeManager
        
        sf = SnowflakeManager()
        if not sf.connect():
            console.print("[red]❌ Failed to connect to Snowflake[/red]")
            return False
        
        test_queries = {
            "Account Hierarchy": """
                SELECT 
                    a.ACCOUNT_NAME,
                    p.ACCOUNT_NAME as PARENT_NAME,
                    a.HIERARCHY_LEVEL,
                    a.SEGMENT
                FROM ACCOUNTS a
                LEFT JOIN ACCOUNTS p ON a.PARENT_ACCOUNT_ID = p.ACCOUNT_ID
                ORDER BY a.HIERARCHY_LEVEL, a.ACCOUNT_NAME
                LIMIT 10
            """,
            
            "Product Categories": """
                SELECT 
                    CATEGORY,
                    COUNT(*) as PRODUCT_COUNT,
                    AVG(UNIT_PRICE) as AVG_PRICE
                FROM PRODUCTS
                GROUP BY CATEGORY
                ORDER BY PRODUCT_COUNT DESC
            """,
            
            "Recent Transactions": """
                SELECT 
                    t.TRANSACTION_DATE,
                    a.ACCOUNT_NAME,
                    p.PRODUCT_NAME,
                    t.QUANTITY,
                    t.TOTAL_AMOUNT
                FROM TRANSACTIONS t
                JOIN ACCOUNTS a ON t.ACCOUNT_ID = a.ACCOUNT_ID
                JOIN PRODUCTS p ON t.PRODUCT_ID = p.PRODUCT_ID
                ORDER BY t.TRANSACTION_DATE DESC
                LIMIT 5
            """,
            
            "Loyalty Tier Distribution": """
                SELECT 
                    LOYALTY_TIER,
                    COUNT(*) as MEMBER_COUNT,
                    AVG(POINTS_BALANCE) as AVG_POINTS
                FROM LOYALTY_MEMBERS
                WHERE STATUS = 'Active'
                GROUP BY LOYALTY_TIER
                ORDER BY AVG_POINTS DESC
            """
        }
        
        for query_name, query in test_queries.items():
            console.print(f"\n[blue]🔍 {query_name}:[/blue]")
            result = sf.execute_query(query)
            
            if result is not None and len(result) > 0:
                console.print(result.to_string(index=False))
            else:
                console.print("[yellow]No results or query failed[/yellow]")
        
        sf.close_connection()
        console.print("\n[green]✅ Test queries completed![/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Test queries failed: {str(e)}[/red]")
        return False


@app.command()
def status():
    """Show current status of PMI workshop setup"""
    console.print(Panel("📊 PMI Workshop Status", style="blue"))
    
    try:
        from src.pmi_retail.database.snowflake.connection import SnowflakeManager
        from src.pmi_retail.config import settings
        
        sf = SnowflakeManager()
        
        # Check connection
        console.print("\n[blue]🔌 Connection Status:[/blue]")
        if sf.connect():
            console.print("✅ Snowflake connection: [green]Active[/green]")
            
            # Check tables
            console.print("\n[blue]📋 Table Status:[/blue]")
            tables = ['ACCOUNTS', 'PRODUCTS', 'TRANSACTIONS', 'LOYALTY_MEMBERS', 'DATA_QUALITY_RULES']
            
            for table in tables:
                try:
                    count_result = sf.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                    if count_result is not None:
                        count = count_result.iloc[0]['count']
                        console.print(f"✅ {table}: [green]{count:,} rows[/green]")
                    else:
                        console.print(f"❌ {table}: [red]Query failed[/red]")
                except:
                    console.print(f"❌ {table}: [red]Not found[/red]")
            
            # Check views
            console.print("\n[blue]👁️ View Status:[/blue]")
            try:
                view_result = sf.execute_query("SELECT COUNT(*) as count FROM VW_ACCOUNT_HIERARCHY")
                if view_result is not None:
                    count = view_result.iloc[0]['count']
                    console.print(f"✅ VW_ACCOUNT_HIERARCHY: [green]{count:,} rows[/green]")
                else:
                    console.print("❌ VW_ACCOUNT_HIERARCHY: [red]Query failed[/red]")
            except:
                console.print("❌ VW_ACCOUNT_HIERARCHY: [red]Not found[/red]")
            
            # Show configuration
            console.print("\n[blue]⚙️ Configuration:[/blue]")
            console.print(f"• Database: {settings.snowflake_database}")
            console.print(f"• Schema: {settings.snowflake_schema}")
            console.print(f"• Warehouse: {settings.snowflake_warehouse}")
            console.print(f"• Environment: {settings.environment}")
            
            sf.close_connection()
        else:
            console.print("❌ Snowflake connection: [red]Failed[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]❌ Status check failed: {str(e)}[/red]")
        return False


def main():
    """Entry point for the CLI application"""
    app()


if __name__ == "__main__":
    main()