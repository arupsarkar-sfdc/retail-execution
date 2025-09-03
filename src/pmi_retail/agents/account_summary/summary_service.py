"""
Account Summary Service
Main orchestrator service for AI-powered account summary generation
"""

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

try:
    from .data_aggregator import AccountDataAggregator
    from .notes_processor import AccountNotesProcessor
    from .summary_chain import AccountSummaryChain
    from pmi_retail.agents.components.vectorstore import VectorStoreManager
except ImportError as e:
    print(f"Error: Cannot import required modules: {e}")
    print("Make sure you're running from the project root and dependencies are installed.")

logger = logging.getLogger(__name__)


class AccountSummaryService:
    """Main service orchestrating account summary generation"""
    
    def __init__(self, 
                 model_name: str = "gpt-4",
                 temperature: float = 0.1,
                 max_tokens: int = 2000):
        """
        Initialize Account Summary Service
        
        Args:
            model_name: OpenAI model name for summary generation
            temperature: Model temperature for response generation
            max_tokens: Maximum tokens in response
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize components
        self.data_aggregator = AccountDataAggregator()
        self.notes_processor = AccountNotesProcessor()
        self.summary_chain = AccountSummaryChain(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        self.vectorstore_manager = VectorStoreManager()
        
        logger.info("✅ Account Summary Service initialized")
    
    def generate_account_summary(self, account_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive AI-powered account summary
        
        Args:
            account_id: Account ID to generate summary for
            
        Returns:
            Dictionary containing comprehensive account summary
        """
        try:
            logger.info(f"🚀 Starting account summary generation for: {account_id}")
            
            # Step 1: Validate account ID
            if not self.validate_account_id(account_id):
                return {
                    'error': f'Account ID {account_id} not found or inactive',
                    'account_id': account_id,
                    'generated_at': datetime.now().isoformat()
                }
            
            # Step 2: Aggregate all account data
            logger.info("📊 Aggregating account data...")
            account_data = self.data_aggregator.get_account_summary_data(account_id)
            
            if not account_data or not account_data.get('account_details'):
                return {
                    'error': f'No data found for account {account_id}',
                    'account_id': account_id,
                    'generated_at': datetime.now().isoformat()
                }
            
            # Step 3: Process notes for vectorstore
            logger.info("📝 Processing notes for AI analysis...")
            notes = account_data.get('notes', [])
            notes_documents = self.notes_processor.process_account_notes(account_id, notes)
            
            # Step 4: Create vectorstore for enhanced context
            vectorstore = None
            if notes_documents:
                logger.info("🔍 Creating vectorstore for document retrieval...")
                vectorstore = self.summary_chain.create_vectorstore(notes_documents)
                
                if vectorstore:
                    # Create QA chain for document-based questions
                    qa_chain = self.summary_chain.create_qa_chain()
                    if qa_chain:
                        logger.info("✅ QA chain created for document retrieval")
            
            # Step 5: Generate AI summary
            logger.info("🤖 Generating AI-powered summary...")
            ai_summary = self.summary_chain.create_account_summary(account_data)
            
            # Step 6: Extract additional insights
            logger.info("💡 Extracting key insights...")
            key_insights = self.notes_processor.extract_key_insights(notes)
            
            # Step 7: Generate recommendations
            logger.info("📋 Generating recommendations...")
            recommendations = self._generate_recommendations(account_data)
            
            # Step 8: Identify risk factors
            logger.info("⚠️ Identifying risk factors...")
            risk_factors = self._identify_risk_factors(account_data)
            
            # Step 9: Calculate confidence score
            confidence_score = self._calculate_confidence_score(account_data, ai_summary)
            
            # Step 10: Compile final summary
            final_summary = {
                'account_id': account_id,
                'account_name': account_data.get('account_details', {}).get('account_name', 'Unknown'),
                'summary': ai_summary,
                'key_insights': key_insights,
                'recommendations': recommendations,
                'risk_factors': risk_factors,
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'data_sources': ['ACCOUNTS', 'CONTACTS', 'NOTES', 'TRANSACTIONS', 'CAMPAIGNS'],
                    'confidence_score': confidence_score,
                    'total_notes': len(notes),
                    'total_contacts': len(account_data.get('contacts', [])),
                    'total_transactions': len(account_data.get('transactions', [])),
                    'model_used': self.model_name
                }
            }
            
            logger.info(f"✅ Account summary generated successfully for {account_id}")
            return final_summary
            
        except Exception as e:
            logger.error(f"❌ Error generating account summary for {account_id}: {str(e)}")
            return {
                'error': str(e),
                'account_id': account_id,
                'generated_at': datetime.now().isoformat()
            }
        finally:
            # Clean up database connection
            if hasattr(self.data_aggregator, 'disconnect'):
                self.data_aggregator.disconnect()
    
    def get_account_list(self) -> List[Dict[str, str]]:
        """
        Get list of all accounts for selection
        
        Returns:
            List of account dictionaries with ID, name, type, and segment
        """
        try:
            logger.info("📋 Fetching account list...")
            
            if not self.data_aggregator.is_connected:
                if not self.data_aggregator.connect():
                    logger.error("Failed to connect to database")
                    return []
            
            accounts = self.data_aggregator.get_account_list()
            
            logger.info(f"✅ Retrieved {len(accounts)} accounts")
            return accounts
            
        except Exception as e:
            logger.error(f"❌ Error fetching account list: {str(e)}")
            return []
        finally:
            if hasattr(self.data_aggregator, 'disconnect'):
                self.data_aggregator.disconnect()
    
    def validate_account_id(self, account_id: str) -> bool:
        """
        Validate if account ID exists and is active
        
        Args:
            account_id: Account ID to validate
            
        Returns:
            True if account exists and is active, False otherwise
        """
        try:
            if not self.data_aggregator.is_connected:
                if not self.data_aggregator.connect():
                    return False
            
            is_valid = self.data_aggregator.validate_account_id(account_id)
            logger.info(f"Account {account_id} validation: {'✅ Valid' if is_valid else '❌ Invalid'}")
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating account ID {account_id}: {str(e)}")
            return False
    
    def _generate_recommendations(self, account_data: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on account data"""
        try:
            recommendations = []
            
            account_details = account_data.get('account_details', {})
            notes = account_data.get('notes', [])
            transactions = account_data.get('transactions', [])
            contacts = account_data.get('contacts', [])
            
            # Revenue-based recommendations
            annual_revenue = account_details.get('annual_revenue', 0)
            if annual_revenue > 1000000:  # High-value account
                recommendations.append("Schedule quarterly executive business reviews")
                recommendations.append("Assign dedicated account manager for premium support")
            
            # Contact-based recommendations
            if len(contacts) == 0:
                recommendations.append("Identify and establish key contacts within the organization")
            elif len(contacts) < 3:
                recommendations.append("Expand contact network to include decision makers")
            
            # Notes-based recommendations
            high_priority_notes = [n for n in notes if n.get('note_priority') == 'High']
            if high_priority_notes:
                recommendations.append("Address high-priority issues immediately")
                recommendations.append("Schedule follow-up meetings to resolve outstanding items")
            
            # Transaction-based recommendations
            if transactions:
                recent_transactions = [t for t in transactions if self._is_recent(t.get('transaction_date', ''), days=90)]
                if len(recent_transactions) < len(transactions) * 0.3:  # Less than 30% recent
                    recommendations.append("Re-engage account with new product offerings")
                    recommendations.append("Schedule product demonstration sessions")
            
            # Segment-based recommendations
            segment = account_details.get('segment', '')
            if segment == 'Premium':
                recommendations.append("Provide white-glove service and priority support")
                recommendations.append("Offer exclusive product previews and early access")
            elif segment == 'Basic':
                recommendations.append("Focus on value proposition and cost-effectiveness")
                recommendations.append("Provide self-service tools and resources")
            
            # Default recommendations if none generated
            if not recommendations:
                recommendations.extend([
                    "Schedule regular check-in meetings",
                    "Monitor account health and satisfaction",
                    "Identify upselling and cross-selling opportunities"
                ])
            
            return recommendations[:5]  # Limit to top 5 recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return ["Schedule account review meeting", "Monitor account health"]
    
    def _identify_risk_factors(self, account_data: Dict[str, Any]) -> List[str]:
        """Identify potential risk factors for the account"""
        try:
            risk_factors = []
            
            notes = account_data.get('notes', [])
            transactions = account_data.get('transactions', [])
            account_details = account_data.get('account_details', {})
            
            # Note-based risk factors
            complaint_notes = [n for n in notes if any(keyword in n.get('note_text', '').lower() 
                                                     for keyword in ['complaint', 'issue', 'problem', 'dissatisfied'])]
            if complaint_notes:
                risk_factors.append(f"Customer complaints identified ({len(complaint_notes)} notes)")
            
            unresolved_notes = [n for n in notes if n.get('note_status') != 'Resolved']
            if len(unresolved_notes) > 3:
                risk_factors.append(f"Multiple unresolved issues ({len(unresolved_notes)} items)")
            
            # Transaction-based risk factors
            if transactions:
                recent_transactions = [t for t in transactions if self._is_recent(t.get('transaction_date', ''), days=90)]
                if len(recent_transactions) < len(transactions) * 0.2:  # Less than 20% recent
                    risk_factors.append("Declining transaction activity")
                
                # Check for decreasing transaction amounts
                if len(transactions) >= 3:
                    recent_amounts = [t.get('net_amount', 0) for t in recent_transactions[:3]]
                    older_amounts = [t.get('net_amount', 0) for t in transactions[-3:]]
                    if recent_amounts and older_amounts:
                        recent_avg = sum(recent_amounts) / len(recent_amounts)
                        older_avg = sum(older_amounts) / len(older_amounts)
                        if recent_avg < older_avg * 0.7:  # 30% decrease
                            risk_factors.append("Significant decrease in transaction values")
            
            # Account status risk factors
            status = account_details.get('status', '')
            if status != 'Active':
                risk_factors.append(f"Account status: {status}")
            
            # Revenue risk factors
            annual_revenue = account_details.get('annual_revenue', 0)
            if annual_revenue == 0:
                risk_factors.append("No revenue recorded for this account")
            
            return risk_factors
            
        except Exception as e:
            logger.error(f"Error identifying risk factors: {str(e)}")
            return ["Unable to assess risk factors"]
    
    def _calculate_confidence_score(self, account_data: Dict[str, Any], ai_summary: Dict[str, Any]) -> float:
        """Calculate confidence score for the generated summary"""
        try:
            score = 0.0
            max_score = 100.0
            
            # Data completeness (40 points)
            account_details = account_data.get('account_details', {})
            if account_details:
                score += 10  # Account details available
            
            notes = account_data.get('notes', [])
            if len(notes) >= 5:
                score += 15  # Sufficient notes
            elif len(notes) >= 1:
                score += 10  # Some notes
            
            contacts = account_data.get('contacts', [])
            if len(contacts) >= 1:
                score += 10  # Contacts available
            
            transactions = account_data.get('transactions', [])
            if len(transactions) >= 3:
                score += 5  # Transaction history available
            
            # AI summary quality (30 points)
            if ai_summary and not ai_summary.get('error'):
                if ai_summary.get('executive_summary'):
                    score += 10
                if ai_summary.get('business_insights'):
                    score += 10
                if ai_summary.get('recommended_actions'):
                    score += 10
            
            # Data recency (20 points)
            recent_notes = [n for n in notes if self._is_recent(n.get('created_timestamp', ''), days=90)]
            if len(recent_notes) >= 3:
                score += 20
            elif len(recent_notes) >= 1:
                score += 10
            
            # Data diversity (10 points)
            note_types = set(n.get('note_type', '') for n in notes)
            if len(note_types) >= 3:
                score += 10
            elif len(note_types) >= 2:
                score += 5
            
            return min(score / max_score, 1.0)  # Normalize to 0-1
            
        except Exception as e:
            logger.error(f"Error calculating confidence score: {str(e)}")
            return 0.5  # Default moderate confidence
    
    def _is_recent(self, date_str: str, days: int = 90) -> bool:
        """Check if a date is within the specified number of days"""
        try:
            if not date_str:
                return False
            
            from datetime import datetime, timedelta
            
            if isinstance(date_str, str):
                # Try to parse the date string
                try:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except:
                    return False
            else:
                date_obj = date_str
            
            cutoff_date = datetime.now() - timedelta(days=days)
            return date_obj >= cutoff_date
            
        except Exception as e:
            logger.error(f"Error checking date recency: {str(e)}")
            return False
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get the current status of the service and its components"""
        try:
            status = {
                'service_initialized': True,
                'model_name': self.model_name,
                'temperature': self.temperature,
                'max_tokens': self.max_tokens,
                'components': {
                    'data_aggregator': 'initialized',
                    'notes_processor': 'initialized',
                    'summary_chain': 'initialized' if self.summary_chain.llm else 'not_initialized',
                    'vectorstore_manager': 'initialized'
                },
                'database_connection': 'unknown',
                'openai_api': 'unknown'
            }
            
            # Check database connection
            try:
                if self.data_aggregator.connect():
                    status['database_connection'] = 'connected'
                    self.data_aggregator.disconnect()
                else:
                    status['database_connection'] = 'failed'
            except:
                status['database_connection'] = 'error'
            
            # Check OpenAI API
            if self.summary_chain.api_key:
                status['openai_api'] = 'configured'
            else:
                status['openai_api'] = 'not_configured'
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting service status: {str(e)}")
            return {
                'service_initialized': False,
                'error': str(e)
            }
