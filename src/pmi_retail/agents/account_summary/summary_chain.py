"""
Account Summary Chain
LangChain-based account summary generation using OpenAI
"""

import os
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

try:
    from langchain_openai import ChatOpenAI
    from langchain.chains import RetrievalQA
    from langchain.prompts import PromptTemplate
    from langchain.schema import Document
    from langchain.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings
except ImportError as e:
    print(f"Error: Cannot import LangChain modules: {e}")
    print("Please install: pip install langchain langchain-openai faiss-cpu")

logger = logging.getLogger(__name__)


class AccountSummaryChain:
    """LangChain-based account summary generation using OpenAI"""
    
    def __init__(self, 
                 model_name: str = "gpt-4",
                 temperature: float = 0.1,
                 max_tokens: int = 2000,
                 api_key: Optional[str] = None):
        """
        Initialize Account Summary Chain
        
        Args:
            model_name: OpenAI model name
            temperature: Model temperature for response generation
            max_tokens: Maximum tokens in response
            api_key: OpenAI API key (if None, uses environment variable)
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        self.llm = None
        self.embeddings = None
        self.vectorstore = None
        self.qa_chain = None
        
        self._initialize_llm()
        self._initialize_embeddings()
    
    def _initialize_llm(self):
        """Initialize OpenAI LLM"""
        try:
            if not self.api_key:
                logger.error("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
                return
            
            self.llm = ChatOpenAI(
                model_name=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                openai_api_key=self.api_key
            )
            
            logger.info(f"✅ OpenAI LLM initialized with model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"❌ Error initializing OpenAI LLM: {str(e)}")
    
    def _initialize_embeddings(self):
        """Initialize OpenAI embeddings"""
        try:
            if not self.api_key:
                logger.error("OpenAI API key not found for embeddings.")
                return
            
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=self.api_key
            )
            
            logger.info("✅ OpenAI embeddings initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing OpenAI embeddings: {str(e)}")
    
    def create_vectorstore(self, documents: List[Document]) -> Optional[FAISS]:
        """
        Create FAISS vectorstore from documents
        
        Args:
            documents: List of Document objects
            
        Returns:
            FAISS vectorstore or None if error
        """
        try:
            if not documents:
                logger.warning("No documents provided for vectorstore creation")
                return None
            
            if not self.embeddings:
                logger.error("Embeddings not initialized")
                return None
            
            logger.info(f"📚 Creating vectorstore from {len(documents)} documents")
            
            self.vectorstore = FAISS.from_documents(documents, self.embeddings)
            
            logger.info("✅ Vectorstore created successfully")
            return self.vectorstore
            
        except Exception as e:
            logger.error(f"❌ Error creating vectorstore: {str(e)}")
            return None
    
    def create_qa_chain(self) -> Optional[RetrievalQA]:
        """
        Create QA chain for document retrieval
        
        Returns:
            RetrievalQA chain or None if error
        """
        try:
            if not self.llm:
                logger.error("LLM not initialized")
                return None
            
            if not self.vectorstore:
                logger.error("Vectorstore not created")
                return None
            
            # Create QA chain
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5}),
                return_source_documents=True
            )
            
            logger.info("✅ QA chain created successfully")
            return self.qa_chain
            
        except Exception as e:
            logger.error(f"❌ Error creating QA chain: {str(e)}")
            return None
    
    def create_account_summary(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive account summary using LLM
        
        Args:
            account_data: Dictionary containing all account-related data
            
        Returns:
            Dictionary containing generated summary and insights
        """
        try:
            if not self.llm:
                raise ValueError("LLM not initialized")
            
            logger.info(f"🤖 Generating AI summary for account: {account_data.get('account_id', 'Unknown')}")
            
            # Create summary prompt
            prompt = self._create_summary_prompt(account_data)
            
            # Generate summary using LLM
            response = self.llm.invoke(prompt)
            summary_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse and structure the response
            structured_summary = self._parse_summary_response(summary_text, account_data)
            
            logger.info("✅ Account summary generated successfully")
            return structured_summary
            
        except Exception as e:
            logger.error(f"❌ Error generating account summary: {str(e)}")
            return {
                'error': str(e),
                'account_id': account_data.get('account_id', 'Unknown'),
                'generated_at': datetime.now().isoformat()
            }
    
    def _create_summary_prompt(self, account_data: Dict[str, Any]) -> str:
        """Create structured prompt for account summary generation"""
        try:
            account_details = account_data.get('account_details', {})
            contacts = account_data.get('contacts', [])
            notes = account_data.get('notes', [])
            transactions = account_data.get('transactions', [])
            campaigns = account_data.get('campaigns', [])
            
            # Format account details
            account_info = self._format_account_info(account_details)
            
            # Format contacts summary
            contacts_summary = self._format_contacts_summary(contacts)
            
            # Format notes summary
            notes_summary = self._format_notes_summary(notes)
            
            # Format transactions summary
            transactions_summary = self._format_transactions_summary(transactions)
            
            # Format campaigns summary
            campaigns_summary = self._format_campaigns_summary(campaigns)
            
            # Create comprehensive prompt
            prompt = f"""
You are an expert retail account analyst with deep experience in customer relationship management and business intelligence. Generate a comprehensive, actionable account summary for the following account:

## ACCOUNT INFORMATION
{account_info}

## CONTACTS SUMMARY
{contacts_summary}

## NOTES & COMMUNICATIONS
{notes_summary}

## TRANSACTION HISTORY
{transactions_summary}

## CAMPAIGN ACTIVITY
{campaigns_summary}

## ANALYSIS REQUIREMENTS

Please provide a comprehensive analysis in the following structured format:

### 1. EXECUTIVE SUMMARY
Provide a 2-3 sentence executive summary highlighting the most important aspects of this account relationship.

### 2. BUSINESS INSIGHTS
Identify 3-5 key business insights about this account, including:
- Revenue trends and opportunities
- Customer behavior patterns
- Relationship health indicators
- Market positioning

### 3. RELATIONSHIP STATUS
Assess the current state of the customer relationship:
- Overall satisfaction level
- Engagement frequency
- Communication quality
- Trust indicators

### 4. REVENUE OPPORTUNITIES
Identify specific revenue growth opportunities:
- Upselling potential
- Cross-selling opportunities
- New product introductions
- Market expansion possibilities

### 5. RISK FACTORS
Identify potential risks or concerns:
- Customer satisfaction issues
- Competitive threats
- Operational challenges
- Financial risks

### 6. RECOMMENDED ACTIONS
Provide 3-5 specific, actionable recommendations for:
- Immediate actions (next 30 days)
- Short-term strategies (next 90 days)
- Long-term relationship building (next 6-12 months)

### 7. KEY METRICS TO TRACK
Suggest 3-5 key performance indicators to monitor for this account.

## FORMATTING REQUIREMENTS
- Use clear, professional language
- Provide specific, actionable insights
- Include relevant data points and examples
- Focus on business value and outcomes
- Keep recommendations practical and achievable

Generate a comprehensive, well-structured analysis that will help sales and account management teams make informed decisions about this customer relationship.
"""
            
            return prompt
            
        except Exception as e:
            logger.error(f"Error creating summary prompt: {str(e)}")
            return f"Generate a comprehensive account summary for account: {account_data.get('account_id', 'Unknown')}"
    
    def _format_account_info(self, account_details: Dict[str, Any]) -> str:
        """Format account details for prompt"""
        if not account_details:
            return "No account details available."
        
        info_parts = []
        info_parts.append(f"Account ID: {account_details.get('account_id', 'N/A')}")
        info_parts.append(f"Account Name: {account_details.get('account_name', 'N/A')}")
        info_parts.append(f"Account Type: {account_details.get('account_type', 'N/A')}")
        info_parts.append(f"Segment: {account_details.get('segment', 'N/A')}")
        info_parts.append(f"Annual Revenue: ${account_details.get('annual_revenue', 0):,.2f}")
        info_parts.append(f"Employee Count: {account_details.get('employee_count', 'N/A')}")
        info_parts.append(f"Status: {account_details.get('status', 'N/A')}")
        info_parts.append(f"Location: {account_details.get('city', 'N/A')}, {account_details.get('state', 'N/A')}")
        
        return "\n".join(info_parts)
    
    def _format_contacts_summary(self, contacts: List[Dict[str, Any]]) -> str:
        """Format contacts summary for prompt"""
        if not contacts:
            return "No contacts associated with this account."
        
        summary_parts = [f"Total Contacts: {len(contacts)}"]
        
        # Group by contact type
        contact_types = {}
        for contact in contacts:
            contact_type = contact.get('contact_type', 'Unknown')
            if contact_type not in contact_types:
                contact_types[contact_type] = []
            contact_types[contact_type].append(contact)
        
        for contact_type, type_contacts in contact_types.items():
            summary_parts.append(f"\n{contact_type} Contacts ({len(type_contacts)}):")
            for contact in type_contacts[:3]:  # Show first 3 of each type
                name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                job_title = contact.get('job_title', '')
                if job_title:
                    summary_parts.append(f"  - {name} ({job_title})")
                else:
                    summary_parts.append(f"  - {name}")
        
        return "\n".join(summary_parts)
    
    def _format_notes_summary(self, notes: List[Dict[str, Any]]) -> str:
        """Format notes summary for prompt"""
        if not notes:
            return "No notes available for this account."
        
        summary_parts = [f"Total Notes: {len(notes)}"]
        
        # Group by note type
        note_types = {}
        for note in notes:
            note_type = note.get('note_type', 'Unknown')
            if note_type not in note_types:
                note_types[note_type] = []
            note_types[note_type].append(note)
        
        for note_type, type_notes in note_types.items():
            summary_parts.append(f"\n{note_type} ({len(type_notes)}):")
            for note in type_notes[:2]:  # Show first 2 of each type
                subject = note.get('subject', 'No subject')
                priority = note.get('note_priority', '')
                summary_parts.append(f"  - {subject} ({priority} priority)")
        
        # Show recent high-priority notes
        high_priority_notes = [n for n in notes if n.get('note_priority') == 'High']
        if high_priority_notes:
            summary_parts.append(f"\nHigh Priority Items ({len(high_priority_notes)}):")
            for note in high_priority_notes[:3]:
                subject = note.get('subject', 'No subject')
                summary_parts.append(f"  - {subject}")
        
        return "\n".join(summary_parts)
    
    def _format_transactions_summary(self, transactions: List[Dict[str, Any]]) -> str:
        """Format transactions summary for prompt"""
        if not transactions:
            return "No transaction history available."
        
        # Calculate summary statistics
        total_amount = sum(t.get('net_amount', 0) for t in transactions)
        avg_amount = total_amount / len(transactions) if transactions else 0
        
        # Group by product category
        categories = {}
        for transaction in transactions:
            category = transaction.get('product_category', 'Unknown')
            if category not in categories:
                categories[category] = {'count': 0, 'amount': 0}
            categories[category]['count'] += 1
            categories[category]['amount'] += transaction.get('net_amount', 0)
        
        summary_parts = [
            f"Total Transactions: {len(transactions)}",
            f"Total Revenue: ${total_amount:,.2f}",
            f"Average Transaction: ${avg_amount:,.2f}"
        ]
        
        summary_parts.append("\nBy Product Category:")
        for category, stats in categories.items():
            summary_parts.append(f"  - {category}: {stats['count']} transactions, ${stats['amount']:,.2f}")
        
        return "\n".join(summary_parts)
    
    def _format_campaigns_summary(self, campaigns: List[Dict[str, Any]]) -> str:
        """Format campaigns summary for prompt"""
        if not campaigns:
            return "No campaign activity recorded."
        
        summary_parts = [f"Total Campaigns: {len(campaigns)}"]
        
        # Group by campaign type
        campaign_types = {}
        for campaign in campaigns:
            campaign_type = campaign.get('campaign_type', 'Unknown')
            if campaign_type not in campaign_types:
                campaign_types[campaign_type] = []
            campaign_types[campaign_type].append(campaign)
        
        for campaign_type, type_campaigns in campaign_types.items():
            summary_parts.append(f"\n{campaign_type} Campaigns ({len(type_campaigns)}):")
            for campaign in type_campaigns:
                name = campaign.get('campaign_name', 'Unnamed')
                status = campaign.get('status', 'Unknown')
                budget = campaign.get('budget', 0)
                summary_parts.append(f"  - {name} ({status}, Budget: ${budget:,.2f})")
        
        return "\n".join(summary_parts)
    
    def _parse_summary_response(self, response_text: str, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response into structured format"""
        try:
            # Basic parsing - in a real implementation, you might use more sophisticated parsing
            sections = {
                'executive_summary': '',
                'business_insights': [],
                'relationship_status': '',
                'revenue_opportunities': [],
                'risk_factors': [],
                'recommended_actions': [],
                'key_metrics': []
            }
            
            # Simple section extraction (this could be enhanced with more sophisticated parsing)
            lines = response_text.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Identify sections
                if 'EXECUTIVE SUMMARY' in line.upper():
                    current_section = 'executive_summary'
                elif 'BUSINESS INSIGHTS' in line.upper():
                    current_section = 'business_insights'
                elif 'RELATIONSHIP STATUS' in line.upper():
                    current_section = 'relationship_status'
                elif 'REVENUE OPPORTUNITIES' in line.upper():
                    current_section = 'revenue_opportunities'
                elif 'RISK FACTORS' in line.upper():
                    current_section = 'risk_factors'
                elif 'RECOMMENDED ACTIONS' in line.upper():
                    current_section = 'recommended_actions'
                elif 'KEY METRICS' in line.upper():
                    current_section = 'key_metrics'
                elif line.startswith('-') or line.startswith('•'):
                    # This is a list item
                    if current_section and current_section in ['business_insights', 'revenue_opportunities', 'risk_factors', 'recommended_actions', 'key_metrics']:
                        sections[current_section].append(line[1:].strip())
                elif current_section == 'executive_summary' or current_section == 'relationship_status':
                    # This is content for a text section
                    if sections[current_section]:
                        sections[current_section] += ' ' + line
                    else:
                        sections[current_section] = line
            
            # Add metadata
            sections['account_id'] = account_data.get('account_id', 'Unknown')
            sections['generated_at'] = datetime.now().isoformat()
            sections['raw_response'] = response_text
            
            return sections
            
        except Exception as e:
            logger.error(f"Error parsing summary response: {str(e)}")
            return {
                'account_id': account_data.get('account_id', 'Unknown'),
                'executive_summary': response_text,
                'generated_at': datetime.now().isoformat(),
                'parse_error': str(e)
            }
