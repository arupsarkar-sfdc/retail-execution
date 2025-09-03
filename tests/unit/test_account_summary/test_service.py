"""
Unit tests for Account Summary Service
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from src.pmi_retail.agents.account_summary import AccountSummaryService


class TestAccountSummaryService:
    """Test cases for AccountSummaryService"""
    
    def test_service_initialization(self):
        """Test service initialization"""
        service = AccountSummaryService()
        assert service is not None
        assert service.model_name == "gpt-4"
        assert service.temperature == 0.1
        assert service.max_tokens == 2000
    
    def test_service_status(self):
        """Test service status check"""
        service = AccountSummaryService()
        status = service.get_service_status()
        
        assert status is not None
        assert 'service_initialized' in status
        assert 'model_name' in status
        assert 'components' in status
        assert status['service_initialized'] is True
    
    def test_account_validation_invalid(self):
        """Test account validation with invalid ID"""
        service = AccountSummaryService()
        is_valid = service.validate_account_id("INVALID_ID")
        assert is_valid is False
    
    def test_get_account_list(self):
        """Test getting account list"""
        service = AccountSummaryService()
        accounts = service.get_account_list()
        
        # Should return a list (may be empty if no database connection)
        assert isinstance(accounts, list)
    
    def test_generate_summary_invalid_account(self):
        """Test summary generation with invalid account"""
        service = AccountSummaryService()
        result = service.generate_account_summary("INVALID_ACCOUNT")
        
        assert 'error' in result
        assert result['account_id'] == "INVALID_ACCOUNT"


if __name__ == "__main__":
    pytest.main([__file__])
