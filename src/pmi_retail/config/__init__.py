"""
PMI Retail Workshop Configuration
Loads settings from environment variables
"""

import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    # Look for .env file in project root
    project_root = Path(__file__).parent.parent.parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment from: {env_path}")
    else:
        print(f"Warning: .env file not found at {env_path}")
except ImportError:
    print("Warning: python-dotenv not available, using system environment variables")


@dataclass
class Settings:
    """Application settings loaded from environment variables"""
    
    # Snowflake Configuration
    snowflake_user: Optional[str] = None
    snowflake_password: Optional[str] = None
    snowflake_account: Optional[str] = None
    snowflake_warehouse: Optional[str] = None
    snowflake_database: Optional[str] = None
    snowflake_schema: Optional[str] = None
    snowflake_role: Optional[str] = None
    
    # Environment
    environment: str = "development"
    
    def __post_init__(self):
        """Load values from environment variables if not set"""
        self.snowflake_user = self.snowflake_user or os.getenv("SNOWFLAKE_USER")
        self.snowflake_password = self.snowflake_password or os.getenv("SNOWFLAKE_PASSWORD")
        self.snowflake_account = self.snowflake_account or os.getenv("SNOWFLAKE_ACCOUNT")
        self.snowflake_warehouse = self.snowflake_warehouse or os.getenv("SNOWFLAKE_WAREHOUSE")
        self.snowflake_database = self.snowflake_database or os.getenv("SNOWFLAKE_DATABASE")
        self.snowflake_schema = self.snowflake_schema or os.getenv("SNOWFLAKE_SCHEMA")
        self.snowflake_role = self.snowflake_role or os.getenv("SNOWFLAKE_ROLE")
        self.environment = os.getenv("ENVIRONMENT", "development")


# Global settings instance
settings = Settings()

