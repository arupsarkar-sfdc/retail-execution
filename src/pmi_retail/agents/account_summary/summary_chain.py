"""
Account Summary Chain
LangChain-based account summary generation using OpenAI
"""

import os
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
from .modern_text_formatter import ModernTextFormatter

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
        self.text_formatter = None
        
        self._initialize_llm()
        self._initialize_embeddings()
        self._initialize_text_formatter()
    
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
    
    def _initialize_text_formatter(self):
        """Initialize Modern Text Formatter"""
        try:
            if not self.api_key:
                logger.error("OpenAI API key not found. Cannot initialize text formatter.")
                return
            
            self.text_formatter = ModernTextFormatter(
                model_name=self.model_name, 
                temperature=0.1
            )
            logger.info("✅ Modern Text Formatter initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing Modern Text Formatter: {str(e)}")
            self.text_formatter = None
    
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
            # Enhanced parsing with better text formatting
            sections = {
                'executive_summary': '',
                'business_insights': [],
                'relationship_status': '',
                'revenue_opportunities': [],
                'risk_factors': [],
                'recommended_actions': [],
                'key_metrics': []
            }
            
            # Split response into lines and process
            lines = response_text.split('\n')
            current_section = None
            current_content = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Identify section headers (case insensitive)
                line_upper = line.upper()
                if 'EXECUTIVE SUMMARY' in line_upper:
                    # Save previous section content
                    if current_section and current_content:
                        sections[current_section] = self._format_section_content(current_section, current_content)
                    current_section = 'executive_summary'
                    current_content = []
                elif 'BUSINESS INSIGHTS' in line_upper:
                    if current_section and current_content:
                        sections[current_section] = self._format_section_content(current_section, current_content)
                    current_section = 'business_insights'
                    current_content = []
                elif 'RELATIONSHIP STATUS' in line_upper:
                    if current_section and current_content:
                        sections[current_section] = self._format_section_content(current_section, current_content)
                    current_section = 'relationship_status'
                    current_content = []
                elif 'REVENUE OPPORTUNITIES' in line_upper:
                    if current_section and current_content:
                        sections[current_section] = self._format_section_content(current_section, current_content)
                    current_section = 'revenue_opportunities'
                    current_content = []
                elif 'RISK FACTORS' in line_upper:
                    if current_section and current_content:
                        sections[current_section] = self._format_section_content(current_section, current_content)
                    current_section = 'risk_factors'
                    current_content = []
                elif 'RECOMMENDED ACTIONS' in line_upper:
                    if current_section and current_content:
                        sections[current_section] = self._format_section_content(current_section, current_content)
                    current_section = 'recommended_actions'
                    current_content = []
                elif 'KEY METRICS' in line_upper:
                    if current_section and current_content:
                        sections[current_section] = self._format_section_content(current_section, current_content)
                    current_section = 'key_metrics'
                    current_content = []
                else:
                    # This is content for the current section
                    if current_section:
                        current_content.append(line)
            
            # Save the last section
            if current_section and current_content:
                sections[current_section] = self._format_section_content(current_section, current_content)
            
            # Add metadata
            sections['account_id'] = account_data.get('account_id', 'Unknown')
            sections['generated_at'] = datetime.now().isoformat()
            sections['raw_response'] = response_text
            
            return sections
            
        except Exception as e:
            logger.error(f"Error parsing summary response: {str(e)}")
            return {
                'account_id': account_data.get('account_id', 'Unknown'),
                'executive_summary': self._clean_text(response_text),
                'generated_at': datetime.now().isoformat(),
                'parse_error': str(e)
            }
    
    def _format_section_content(self, section_name: str, content_lines: List[str]) -> Any:
        """Format content based on section type"""
        if section_name in ['executive_summary', 'relationship_status']:
            # Join lines with proper spacing and clean up text
            text = ' '.join(content_lines)
            return self._clean_text(text)
        else:
            # For list sections, extract bullet points
            items = []
            for line in content_lines:
                # Remove bullet points and clean up
                cleaned_line = line.lstrip('•-*').strip()
                if cleaned_line:
                    items.append(self._clean_text(cleaned_line))
            return items
    
    def _clean_text(self, text: str) -> str:
        """Clean and format text for better readability using modern LLM approach"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Use modern LLM-based text formatter if available
        if self.text_formatter:
            try:
                return self.text_formatter.format_with_llm(text)
            except Exception as e:
                logger.warning(f"LLM text formatting failed, falling back to regex: {e}")
        
        # Fallback to regex-based approach
        text = self._separate_concatenated_words(text)
        text = self._fix_number_spacing(text)
        text = self._normalize_capitalization(text)
        
        return text.strip()
    
    def _separate_concatenated_words(self, text: str) -> str:
        """Separate concatenated words using advanced NLP techniques"""
        import re
        
        # Step 1: Fix already broken words first
        text = self._fix_broken_words(text)
        
        # Step 2: Handle obvious patterns (camelCase, numbers, etc.)
        text = self._handle_obvious_patterns(text)
        
        # Step 3: Use advanced word boundary detection
        text = self._advanced_word_boundary_detection(text)
        
        # Step 4: Clean up any remaining issues
        text = self._cleanup_spacing(text)
        
        return text
    
    def _fix_broken_words(self, text: str) -> str:
        """Fix words that are already broken incorrectly"""
        import re
        
        # Common broken word patterns that need to be rejoined
        broken_patterns = [
            # Common business terms that get broken
            (r'\bin\s+depe\s+nd\s+ent\b', 'independent'),
            (r'\bJacks\s+on\s+ville\b', 'Jacksonville'),
            (r'\bc\s+on\s+sistent\b', 'consistent'),
            (r'\btra\s+ns\s+acti\s+on\b', 'transaction'),
            (r'\bengage\s+ment\b', 'engagement'),
            (r'\bca\s+mp\s+aigns\b', 'campaigns'),
            (r'\bactiv\s+ity\b', 'activity'),
            (r'\bparticipation\b', 'participation'),
            (r'\bcommunication\b', 'communication'),
            (r'\brelationship\b', 'relationship'),
            (r'\bsatisfaction\b', 'satisfaction'),
            (r'\bfrequency\b', 'frequency'),
            (r'\bquality\b', 'quality'),
            (r'\bindicator\b', 'indicator'),
            (r'\bticket\b', 'ticket'),
            (r'\bsupport\b', 'support'),
            (r'\bresolution\b', 'resolution'),
            (r'\bvendor\b', 'vendor'),
            (r'\bability\b', 'ability'),
            (r'\bissue\b', 'issue'),
            (r'\bpromptly\b', 'promptly'),
            
            # Common adjectives
            (r'\bpre\s+mium\b', 'premium'),
            (r'\bstand\s+ard\b', 'standard'),
            (r'\bbas\s+ic\b', 'basic'),
            (r'\bad\s+vanced\b', 'advanced'),
            (r'\bprof\s+essional\b', 'professional'),
            (r'\bcom\s+mercial\b', 'commercial'),
            (r'\bret\s+ail\b', 'retail'),
            (r'\bwholes\s+ale\b', 'wholesale'),
            (r'\bcor\s+porate\b', 'corporate'),
            (r'\benter\s+prise\b', 'enterprise'),
            
            # Common verbs
            (r'\bbas\s+ed\b', 'based'),
            (r'\bloc\s+ated\b', 'located'),
            (r'\boper\s+ating\b', 'operating'),
            (r'\bserv\s+ing\b', 'serving'),
            (r'\bfoc\s+used\b', 'focused'),
            (r'\bwork\s+ing\b', 'working'),
            (r'\bprov\s+iding\b', 'providing'),
            (r'\boffer\s+ing\b', 'offering'),
            (r'\bdeliver\s+ing\b', 'delivering'),
            (r'\bmanag\s+ing\b', 'managing'),
            (r'\brun\s+ning\b', 'running'),
            (r'\blead\s+ing\b', 'leading'),
            (r'\bmonitor\s+ing\b', 'monitoring'),
            (r'\btrack\s+ing\b', 'tracking'),
            (r'\bmeasur\s+ing\b', 'measuring'),
            (r'\banalyz\s+ing\b', 'analyzing'),
            (r'\bevalu\s+ating\b', 'evaluating'),
            (r'\bassess\s+ing\b', 'assessing'),
            (r'\breview\s+ing\b', 'reviewing'),
            (r'\bexamin\s+ing\b', 'examining'),
            (r'\bstud\s+y\s+ing\b', 'studying'),
            (r'\bresearch\s+ing\b', 'researching'),
            (r'\binvestig\s+ating\b', 'investigating'),
            (r'\bexplor\s+ing\b', 'exploring'),
            (r'\bdiscover\s+ing\b', 'discovering'),
            (r'\bidentif\s+y\s+ing\b', 'identifying'),
            (r'\brecogniz\s+ing\b', 'recognizing'),
            (r'\bunderstand\s+ing\b', 'understanding'),
            (r'\bcomprehend\s+ing\b', 'comprehending'),
            (r'\blearn\s+ing\b', 'learning'),
            (r'\bknow\s+ing\b', 'knowing'),
            (r'\brealiz\s+ing\b', 'realizing'),
            (r'\backnowledg\s+ing\b', 'acknowledging'),
            (r'\baccept\s+ing\b', 'accepting'),
            (r'\bagree\s+ing\b', 'agreeing'),
            (r'\bsupport\s+ing\b', 'supporting'),
            (r'\bendors\s+ing\b', 'endorsing'),
            (r'\brecommend\s+ing\b', 'recommending'),
            (r'\bsuggest\s+ing\b', 'suggesting'),
            (r'\bpropos\s+ing\b', 'proposing'),
            (r'\badvis\s+ing\b', 'advising'),
            (r'\bconsult\s+ing\b', 'consulting'),
            (r'\bguid\s+ing\b', 'guiding'),
            (r'\bhelp\s+ing\b', 'helping'),
            (r'\bassist\s+ing\b', 'assisting'),
            (r'\bfacilit\s+ating\b', 'facilitating'),
            (r'\benabl\s+ing\b', 'enabling'),
            (r'\bempower\s+ing\b', 'empowering'),
            (r'\bencourag\s+ing\b', 'encouraging'),
            (r'\bmotiv\s+ating\b', 'motivating'),
            (r'\binspir\s+ing\b', 'inspiring'),
            (r'\bengag\s+ing\b', 'engaging'),
            (r'\binvolv\s+ing\b', 'involving'),
            (r'\bparticip\s+ating\b', 'participating'),
            (r'\bcontribut\s+ing\b', 'contributing'),
            (r'\badd\s+ing\b', 'adding'),
            (r'\bbring\s+ing\b', 'bringing'),
            (r'\bpresent\s+ing\b', 'presenting'),
            (r'\bshow\s+ing\b', 'showing'),
            (r'\bdemonstr\s+ating\b', 'demonstrating'),
            (r'\bdisplay\s+ing\b', 'displaying'),
            (r'\bexhibit\s+ing\b', 'exhibiting'),
            (r'\breveal\s+ing\b', 'revealing'),
            (r'\bexpos\s+ing\b', 'exposing'),
            (r'\buncover\s+ing\b', 'uncovering'),
            (r'\bfind\s+ing\b', 'finding'),
            (r'\bloc\s+ating\b', 'locating'),
            (r'\bdetect\s+ing\b', 'detecting'),
            (r'\bnotic\s+ing\b', 'noticing'),
            (r'\bobserv\s+ing\b', 'observing'),
            (r'\bwatch\s+ing\b', 'watching'),
            (r'\bfollow\s+ing\b', 'following'),
            (r'\bpursu\s+ing\b', 'pursuing'),
            (r'\bchas\s+ing\b', 'chasing'),
            (r'\bseek\s+ing\b', 'seeking'),
            (r'\bsearch\s+ing\b', 'searching'),
            (r'\blook\s+ing\b', 'looking'),
            (r'\bhunt\s+ing\b', 'hunting'),
            
            # Common nouns
            (r'\bloc\s+ation\b', 'location'),
            (r'\breg\s+ion\b', 'region'),
            (r'\bare\s+a\b', 'area'),
            (r'\bterrit\s+ory\b', 'territory'),
            (r'\bdist\s+rict\b', 'district'),
            (r'\bzon\s+e\b', 'zone'),
            (r'\bind\s+ustry\b', 'industry'),
            (r'\bsec\s+tor\b', 'sector'),
            (r'\bseg\s+ment\b', 'segment'),
            (r'\bcat\s+egory\b', 'category'),
            (r'\bcamp\s+a\s+ign\b', 'campaign'),
            (r'\bengag\s+ement\b', 'engagement'),
            (r'\bactiv\s+ity\b', 'activity'),
            (r'\bparticip\s+ation\b', 'participation'),
            (r'\bcomm\s+unication\b', 'communication'),
            (r'\brel\s+ationship\b', 'relationship'),
            (r'\bsat\s+isfaction\b', 'satisfaction'),
            (r'\bfreq\s+uency\b', 'frequency'),
            (r'\bqual\s+ity\b', 'quality'),
            (r'\bind\s+icator\b', 'indicator'),
            (r'\btick\s+et\b', 'ticket'),
            (r'\bsup\s+port\b', 'support'),
            (r'\bres\s+olution\b', 'resolution'),
            (r'\bven\s+dor\b', 'vendor'),
            (r'\bab\s+ility\b', 'ability'),
            (r'\bis\s+sue\b', 'issue'),
            (r'\bprompt\s+ly\b', 'promptly'),
        ]
        
        # Apply the broken word fixes
        for pattern, replacement in broken_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _handle_obvious_patterns(self, text: str) -> str:
        """Handle obvious concatenation patterns"""
        import re
        
        # Pattern 1: camelCase (lowercase + uppercase)
        text = re.sub(r'([a-z]+)([A-Z][a-z]*)', r'\1 \2', text)
        
        # Pattern 2: word + number
        text = re.sub(r'([a-zA-Z]+)(\d+)', r'\1 \2', text)
        
        # Pattern 3: number + word
        text = re.sub(r'(\d+)([a-zA-Z]+)', r'\1 \2', text)
        
        # Pattern 4: punctuation boundaries
        text = re.sub(r'([a-zA-Z])([.,!?;:])', r'\1\2', text)
        text = re.sub(r'([.,!?;:])([a-zA-Z])', r'\1 \2', text)
        
        return text
    
    def _advanced_word_boundary_detection(self, text: str) -> str:
        """Advanced word boundary detection using linguistic patterns"""
        import re
        
        # Split text into words and process each
        words = text.split()
        processed_words = []
        
        for word in words:
            # Skip if word is already properly separated or too short
            if ' ' in word or len(word) <= 3:
                processed_words.append(word)
                continue
            
            # Use advanced splitting for longer words
            if len(word) > 8:  # More conservative threshold
                split_word = self._intelligent_word_splitting(word)
                processed_words.append(split_word)
            else:
                processed_words.append(word)
        
        return ' '.join(processed_words)
    
    def _intelligent_word_splitting(self, word: str) -> str:
        """Intelligent word splitting using linguistic analysis"""
        import re
        
        # First, try to identify common word boundaries using linguistic patterns
        word = self._apply_linguistic_patterns(word)
        
        # If still concatenated, use syllable-based splitting
        if len(word) > 12 and ' ' not in word:
            word = self._syllable_based_splitting(word)
        
        return word
    
    def _apply_linguistic_patterns(self, word: str) -> str:
        """Apply linguistic patterns to identify word boundaries"""
        import re
        
        # Common English word patterns with proper boundaries
        patterns = [
            # Common prefixes
            (r'^(un|re|pre|post|over|under|out|up|down|off|on|in|out|up|down)([a-z]+)', r'\1 \2'),
            
            # Common suffixes
            (r'([a-z]+)(ing|ed|er|est|ly|tion|sion|ness|ment|able|ible|ful|less|ity|ive|ous|ary|ory)$', r'\1 \2'),
            
            # Common business terms (more specific)
            (r'([a-z]+)(account|customer|business|company|market|product|service|revenue|transaction|value|average|total|annual|monthly|weekly|daily)([a-z]*)', r'\1 \2 \3'),
            
            # Common adjectives and descriptors
            (r'([a-z]+)(premium|standard|basic|advanced|professional|commercial|retail|wholesale|independent|chain|franchise|corporate|enterprise)([a-z]*)', r'\1 \2 \3'),
            
            # Common verbs
            (r'([a-z]+)(based|located|operating|serving|focused|working|providing|offering|delivering|supplying|distributing|manufacturing|producing|developing|creating|building|establishing|maintaining|managing|running|leading|directing|controlling|monitoring|tracking|measuring|analyzing|evaluating|assessing|reviewing|examining|studying|researching|investigating|exploring|discovering|identifying|recognizing|understanding|comprehending|learning|knowing|realizing|acknowledging|accepting|agreeing|supporting|endorsing|recommending|suggesting|proposing|advising|consulting|guiding|helping|assisting|facilitating|enabling|empowering|encouraging|motivating|inspiring|engaging|involving|participating|contributing|adding|bringing|presenting|showing|demonstrating|displaying|exhibiting|revealing|exposing|uncovering|finding|locating|detecting|noticing|observing|watching|following|pursuing|chasing|seeking|searching|looking|hunting)([a-z]*)', r'\1 \2 \3'),
            
            # Common nouns
            (r'([a-z]+)(location|region|area|territory|district|zone|industry|sector|segment|category|campaign|engagement|activity|participation|communication|relationship|satisfaction|frequency|quality|indicator|ticket|support|resolution|vendor|ability|issue|promptly)([a-z]*)', r'\1 \2 \3'),
            
            # Common prepositions and articles
            (r'([a-z]+)(the|and|or|but|in|on|at|to|for|of|with|by|a|an|from|into|onto|upon|within|without|through|during|before|after|above|below|between|among|around|near|far|inside|outside|beside|behind|beyond|underneath|throughout|despite|although|however|therefore|moreover|furthermore|nevertheless)([a-z]*)', r'\1 \2 \3'),
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, word, re.IGNORECASE):
                word = re.sub(pattern, replacement, word, flags=re.IGNORECASE)
                break
        
        return word
    
    def _syllable_based_splitting(self, word: str) -> str:
        """Syllable-based splitting for very long concatenated words"""
        import re
        
        # Simple syllable detection based on vowel patterns
        # This is a heuristic approach for English words
        
        # Find vowel patterns
        vowels = 'aeiouAEIOU'
        vowel_positions = [i for i, char in enumerate(word) if char in vowels]
        
        if len(vowel_positions) < 2:
            return word  # Can't split if too few vowels
        
        # Try to split at natural syllable boundaries
        # Look for consonant-vowel patterns that often indicate syllable boundaries
        syllable_boundaries = []
        
        for i in range(1, len(word) - 1):
            # If we have a consonant followed by a vowel, it might be a syllable boundary
            if (word[i] not in vowels and word[i+1] in vowels and 
                i > 2 and i < len(word) - 2):  # Don't split too close to edges
                syllable_boundaries.append(i + 1)
        
        # Apply the most promising splits
        if syllable_boundaries:
            # Choose the middle boundary for a reasonable split
            split_point = syllable_boundaries[len(syllable_boundaries) // 2]
            word = word[:split_point] + ' ' + word[split_point:]
        
        return word
    
    def _cleanup_spacing(self, text: str) -> str:
        """Clean up spacing issues"""
        import re
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Fix spacing around punctuation
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        text = re.sub(r'([.,!?;:])\s*([a-zA-Z])', r'\1 \2', text)
        
        # Fix spacing around parentheses and quotes
        text = re.sub(r'\s*([()])\s*', r'\1', text)
        text = re.sub(r'\s*(["\'])\s*', r'\1', text)
        
        return text.strip()
    
    def _fix_number_spacing(self, text: str) -> str:
        """Fix spacing around numbers"""
        import re
        
        # Fix numbers attached to words
        text = re.sub(r'(\d+)([a-zA-Z])', r'\1 \2', text)
        text = re.sub(r'([a-zA-Z])(\d+)', r'\1 \2', text)
        
        # Fix currency and percentage formatting
        text = re.sub(r'(\d+)([.,])(\d+)', r'\1\2\3', text)  # Keep decimal points
        text = re.sub(r'(\$)(\d+)', r'\1\2', text)  # Keep currency symbols attached
        
        return text
    
    def _normalize_capitalization(self, text: str) -> str:
        """Normalize capitalization for better readability"""
        # Ensure proper sentence capitalization
        sentences = text.split('. ')
        if len(sentences) > 1:
            sentences = [sentences[0]] + [s.capitalize() for s in sentences[1:]]
            text = '. '.join(sentences)
        
        # Fix common capitalization issues
        text = text.replace(' i ', ' I ')
        text = text.replace(' i.', ' I.')
        text = text.replace(' i,', ' I,')
        
        return text
