"""
Account Summary AI Package
Provides AI-powered account summary generation using LangChain and OpenAI
"""

from .data_aggregator import AccountDataAggregator
from .notes_processor import AccountNotesProcessor
from .summary_chain import AccountSummaryChain
from .summary_service import AccountSummaryService

__all__ = [
    'AccountDataAggregator',
    'AccountNotesProcessor', 
    'AccountSummaryChain',
    'AccountSummaryService'
]

__version__ = '1.0.0'
