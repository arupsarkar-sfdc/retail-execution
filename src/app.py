"""
Main Streamlit Application
PDF Chat QA with OpenAI, FAISS, and LangChain
"""

import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

# Import custom components
from pmi_retail.agents.components.pdf_processor import PDFProcessor
from pmi_retail.agents.components.vectorstore import VectorStoreManager
from pmi_retail.agents.components.chat_chain import ChatChainManager
from pmi_retail.agents.account_summary import AccountSummaryService
from pmi_retail.segmentation import RealTimeSegmentationEngine, SegmentationAgent
from pmi_retail.cross_sell import CrossSellOptimizationEngine, CrossSellAgent
from pmi_retail.database.snowflake.connection import SnowflakeManager

# Load environment variables
load_dotenv()

# Configuration
st.set_page_config(
    page_title="Chat QA with OpenAI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
def initialize_session_state():
    """Initialize session state variables"""
    if 'pdf_processor' not in st.session_state:
        st.session_state.pdf_processor = None
    if 'vectorstore_manager' not in st.session_state:
        st.session_state.vectorstore_manager = None
    if 'chat_manager' not in st.session_state:
        st.session_state.chat_manager = None
    if 'documents' not in st.session_state:
        st.session_state.documents = None
    if 'vectorstore_ready' not in st.session_state:
        st.session_state.vectorstore_ready = False
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'processing_status' not in st.session_state:
        st.session_state.processing_status = {}
    if 'account_summary_service' not in st.session_state:
        st.session_state.account_summary_service = None
    if 'account_list' not in st.session_state:
        st.session_state.account_list = []
    if 'last_account_summary' not in st.session_state:
        st.session_state.last_account_summary = None
    if 'segmentation_engine' not in st.session_state:
        st.session_state.segmentation_engine = None
    if 'segmentation_agent' not in st.session_state:
        st.session_state.segmentation_agent = None
    if 'segmentation_data' not in st.session_state:
        st.session_state.segmentation_data = None
    if 'cross_sell_engine' not in st.session_state:
        st.session_state.cross_sell_engine = None
    if 'cross_sell_agent' not in st.session_state:
        st.session_state.cross_sell_agent = None
    if 'cross_sell_data' not in st.session_state:
        st.session_state.cross_sell_data = None

def render_sidebar():
    """Render sidebar with configuration options"""
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # OpenAI API Key
        st.subheader("🔑 OpenAI Settings")
        
        api_key = st.text_input(
            "OpenAI API Key",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password",
            help="Enter your OpenAI API key"
        )
        
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        # API Key status
        if api_key:
            st.success("✅ API Key Set")
        else:
            st.error("❌ API Key Required")
            st.markdown("Get your API key from [OpenAI](https://platform.openai.com/api-keys)")
        
        st.divider()
        
        # Model Selection
        st.subheader("🤖 Model Settings")
        
        # Embedding Model
        embedding_model = st.selectbox(
            "Embedding Model",
            [
                "text-embedding-3-small",
                "text-embedding-3-large", 
                "text-embedding-ada-002"
            ],
            index=0,
            help="Choose the OpenAI embedding model"
        )
        
        # LLM Model
        llm_model = st.selectbox(
            "LLM Model",
            [
                "gpt-3.5-turbo",
                "gpt-4o-mini",
                "gpt-4o",
                "gpt-4-turbo",
                "gpt-4"
            ],
            index=0,
            help="Choose the OpenAI language model"
        )
        
        # LLM Temperature
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.1,
            help="Control randomness of responses"
        )
        
        # Max Tokens
        max_tokens = st.slider(
            "Max Tokens",
            min_value=100,
            max_value=2000,
            value=1000,
            step=100,
            help="Maximum tokens in response"
        )
        
        st.divider()
        
        # PDF Processing Settings
        st.subheader("📄 PDF Processing")
        
        chunk_size = st.slider(
            "Chunk Size",
            min_value=500,
            max_value=2000,
            value=1000,
            step=100,
            help="Size of text chunks for processing"
        )
        
        chunk_overlap = st.slider(
            "Chunk Overlap",
            min_value=50,
            max_value=500,
            value=200,
            step=50,
            help="Overlap between text chunks"
        )
        
        st.divider()
        
        # Retrieval Settings
        st.subheader("🔍 Retrieval Settings")
        
        k_docs = st.slider(
            "Number of Retrieved Documents",
            min_value=1,
            max_value=10,
            value=4,
            help="Number of relevant documents to retrieve"
        )
        
        chain_type = st.radio(
            "Chain Type",
            ["simple", "conversational"],
            index=0,
            help="Simple: Stateless QA, Conversational: With memory"
        )
        
        return {
            "api_key": api_key,
            "embedding_model": embedding_model,
            "llm_model": llm_model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "k_docs": k_docs,
            "chain_type": chain_type
        }

def render_status_panel():
    """Render system status panel"""
    st.subheader("📊 System Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.session_state.pdf_processor:
            st.success("✅ PDF Processor Ready")
        else:
            st.error("❌ PDF Processor Not Ready")
    
    with col2:
        if st.session_state.vectorstore_ready:
            st.success("✅ Vectorstore Ready")
        else:
            st.warning("⚠️ Vectorstore Not Ready")
    
    with col3:
        if st.session_state.chat_manager and st.session_state.chat_manager.llm:
            st.success("✅ Chat Ready")
        else:
            st.error("❌ Chat Not Ready")
    
    with col4:
        if st.session_state.account_summary_service:
            st.success("✅ Account Summary Ready")
        else:
            st.warning("⚠️ Account Summary Not Ready")
    
    # Add a second row for additional services
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        if st.session_state.segmentation_engine:
            st.success("✅ Segmentation Ready")
        else:
            st.warning("⚠️ Segmentation Not Ready")
    
    with col6:
        if st.session_state.segmentation_data:
            st.success("✅ Segmentation Data Loaded")
        else:
            st.info("ℹ️ No Segmentation Data")
    
    with col7:
        if st.session_state.cross_sell_engine:
            st.success("✅ Cross-Sell Ready")
        else:
            st.warning("⚠️ Cross-Sell Not Ready")
    
    with col8:
        if st.session_state.cross_sell_data:
            st.success("✅ Cross-Sell Data Loaded")
        else:
            st.info("ℹ️ No Cross-Sell Data")

def render_pdf_upload_section(config):
    """Render PDF upload and processing section"""
    st.header("📄 Upload & Process PDF")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type="pdf",
        help="Upload a PDF document to chat with"
    )
    
    if uploaded_file is not None:
        st.success(f"📁 Uploaded: {uploaded_file.name}")
        
        # Initialize or update PDF processor
        if (not st.session_state.pdf_processor or 
            st.session_state.pdf_processor.chunk_size != config["chunk_size"] or
            st.session_state.pdf_processor.chunk_overlap != config["chunk_overlap"]):
            
            st.session_state.pdf_processor = PDFProcessor(
                chunk_size=config["chunk_size"],
                chunk_overlap=config["chunk_overlap"]
            )
        
        # Process button
        if st.button("🔄 Process PDF", type="primary"):
            if not config["api_key"]:
                st.error("Please set your OpenAI API key first!")
                return
                
            with st.spinner("Processing PDF..."):
                # Process PDF
                documents = st.session_state.pdf_processor.process_pdf_upload(uploaded_file)
                
                if documents:
                    st.session_state.documents = documents
                    
                    # Show document stats
                    stats = st.session_state.pdf_processor.get_document_stats(documents)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Chunks", stats["total_chunks"])
                    with col2:
                        st.metric("Words", stats["total_words"])
                    with col3:
                        st.metric("Characters", stats["total_characters"])
                    with col4:
                        st.metric("Avg Chunk Size", stats["avg_chunk_size"])
                    
                    st.success("✅ PDF processed successfully!")
                    
                    # Initialize vectorstore manager
                    st.session_state.vectorstore_manager = VectorStoreManager(
                        model_name=config["embedding_model"],
                        api_key=config["api_key"]
                    )
                    
                    # Show cost estimation
                    if st.session_state.vectorstore_manager.embeddings:
                        cost_info = st.session_state.vectorstore_manager.estimate_cost(documents)
                        if "error" not in cost_info:
                            st.info(f"💰 Estimated cost: ${cost_info['estimated_cost_usd']:.4f} for {cost_info['estimated_tokens']} tokens")
                    
                    # Create vectorstore
                    if st.session_state.vectorstore_manager.embeddings:
                        vectorstore = st.session_state.vectorstore_manager.create_vectorstore(documents)
                        
                        if vectorstore:
                            st.session_state.vectorstore_ready = True
                            
                            # Initialize chat manager
                            st.session_state.chat_manager = ChatChainManager(
                                model_name=config["llm_model"],
                                api_key=config["api_key"],
                                temperature=config["temperature"],
                                max_tokens=config["max_tokens"]
                            )
                            
                            # Create appropriate chain
                            if st.session_state.chat_manager.llm:
                                retriever = st.session_state.vectorstore_manager.get_retriever(
                                    search_kwargs={"k": config["k_docs"]}
                                )
                                
                                if config["chain_type"] == "simple":
                                    st.session_state.chat_manager.create_simple_qa_chain(retriever)
                                else:
                                    st.session_state.chat_manager.create_conversational_chain(retriever)
                                
                                st.success("🎉 System ready for chat!")
                else:
                    st.error("Failed to process PDF")
        
        # Show current status
        if st.session_state.documents:
            st.info(f"✅ PDF processed with {len(st.session_state.documents)} chunks")

def render_chat_section(config):
    """Render chat interface"""
    st.header("💬 Chat with PDF")
    
    if not st.session_state.vectorstore_ready:
        st.info("Please upload and process a PDF first to start chatting!")
        return
    
    # Check if we need to recreate the chain based on the selected type
    if st.session_state.chat_manager and st.session_state.vectorstore_manager:
        current_chain_type = config["chain_type"]
        
        # Check if the appropriate chain exists for the selected type
        needs_recreation = False
        if current_chain_type == "simple" and not st.session_state.chat_manager.qa_chain:
            needs_recreation = True
        elif current_chain_type == "conversational" and not st.session_state.chat_manager.conversational_chain:
            needs_recreation = True
        
        if needs_recreation:
            with st.spinner(f"Creating {current_chain_type} chain..."):
                retriever = st.session_state.vectorstore_manager.get_retriever(
                    search_kwargs={"k": config["k_docs"]}
                )
                
                if current_chain_type == "simple":
                    st.session_state.chat_manager.create_simple_qa_chain(retriever)
                    st.success("✅ Simple QA chain created!")
                else:
                    st.session_state.chat_manager.create_conversational_chain(retriever)
                    st.success("✅ Conversational chain created!")
    
    # Chat input
    question = st.text_input(
        "Ask a question about the PDF:",
        placeholder="What is this document about?",
        key="question_input"
    )
    
    # Send button
    col1, col2 = st.columns([1, 4])
    with col1:
        send_clicked = st.button("🚀 Send", type="primary")
    with col2:
        if config["chain_type"] == "conversational":
            if st.button("🗑️ Clear History"):
                if st.session_state.chat_manager:
                    st.session_state.chat_manager.clear_memory()
                st.session_state.chat_history = []
                st.rerun()
    
    # Process question
    if send_clicked and question and st.session_state.chat_manager:
        # Show cost estimation
        if st.session_state.chat_manager:
            cost_info = st.session_state.chat_manager.estimate_cost(question)
            if "error" not in cost_info:
                st.info(f"💰 Estimated cost: ${cost_info['estimated_cost_usd']:.4f}")
        
        result = st.session_state.chat_manager.ask_question(
            question, 
            chain_type=config["chain_type"]
        )
        
        if result["success"]:
            # Add to chat history
            st.session_state.chat_history.append({
                "question": question,
                "answer": result["answer"],
                "sources": result["source_documents"]
            })
            
            # Clear input and refresh
            st.rerun()
        else:
            st.error(f"Error: {result['answer']}")
    
    # Display chat history
    if st.session_state.chat_history:
        st.subheader("💬 Chat History")
        
        # Reverse order to show newest first
        for i, chat in enumerate(reversed(st.session_state.chat_history)):
            with st.expander(f"Q: {chat['question'][:60]}...", expanded=(i == 0)):
                st.markdown("**Question:**")
                st.write(chat['question'])
                
                st.markdown("**Answer:**")
                st.write(chat['answer'])
                
                # Show sources
                if chat.get('sources'):
                    st.markdown("**Sources:**")
                    for j, doc in enumerate(chat['sources'][:2]):
                        with st.container():
                            st.markdown(f"**Source {j+1}:**")
                            st.text(doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content)

def render_account_summary_section(config):
    """Render Account Summary section"""
    st.header("📊 AI-Powered Account Summary")
    st.markdown("Generate comprehensive AI-powered summaries for your accounts using OpenAI and Snowflake data.")
    
    # Initialize Account Summary Service if needed
    if not st.session_state.account_summary_service:
        if config["api_key"]:
            with st.spinner("Initializing Account Summary Service..."):
                try:
                    st.session_state.account_summary_service = AccountSummaryService(
                        model_name=config["llm_model"],
                        temperature=config["temperature"],
                        max_tokens=config["max_tokens"]
                    )
                    st.success("✅ Account Summary Service initialized!")
                except Exception as e:
                    st.error(f"Failed to initialize Account Summary Service: {e}")
                    return
        else:
            st.error("Please set your OpenAI API key first!")
            return
    
    # Load account list
    if not st.session_state.account_list:
        with st.spinner("Loading account list..."):
            try:
                accounts = st.session_state.account_summary_service.get_account_list()
                st.session_state.account_list = accounts
            except Exception as e:
                st.error(f"Failed to load accounts: {e}")
                return
    
    if not st.session_state.account_list:
        st.warning("No accounts found. Please check your database connection.")
        return
    
    # Account selection
    st.subheader("📋 Select Account")
    
    # Create account options for selectbox
    account_options = {}
    for account in st.session_state.account_list:
        display_name = f"{account['account_name']} ({account['account_id']}) - {account['segment']}"
        account_options[display_name] = account['account_id']
    
    selected_display = st.selectbox(
        "Choose an account to analyze:",
        options=list(account_options.keys()),
        help="Select an account to generate an AI-powered summary",
        key="account_selector"
    )
    
    if selected_display:
        selected_account_id = account_options[selected_display]
        
        # Generate summary button
        st.subheader("🚀 Generate Summary")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            generate_clicked = st.button("🤖 Generate AI Summary", type="primary", use_container_width=True)
        
        with col2:
            if st.button("🔄 Refresh Account List", use_container_width=True):
                st.session_state.account_list = []
                st.rerun()
        
        if generate_clicked:
            with st.spinner("Generating AI-powered account summary..."):
                try:
                    # Generate summary
                    summary_data = st.session_state.account_summary_service.generate_account_summary(selected_account_id)
                    
                    if 'error' in summary_data:
                        st.error(f"Error: {summary_data['error']}")
                    else:
                        # Store in session state
                        st.session_state.last_account_summary = summary_data
                        st.success("✅ Account summary generated successfully!")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Failed to generate summary: {e}")
        
        # Display results if available
        if st.session_state.last_account_summary:
            st.markdown("---")
            display_account_summary_results(st.session_state.last_account_summary)

def clean_text_for_display(text: str) -> str:
    """Clean and format text for better display in Streamlit using reliable LLM approach"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Try to use LLM-based formatting if available
    try:
        from pmi_retail.agents.account_summary.modern_text_formatter import StreamlitTextFormatter
        formatter = StreamlitTextFormatter()
        return formatter.format_text_safe(text)
    except Exception as e:
        st.warning(f"LLM formatting unavailable, using fallback: {e}")
        # Fallback to regex-based approach
        text = separate_concatenated_words(text)
        text = fix_number_spacing(text)
        text = normalize_capitalization(text)
        return text.strip()

def separate_concatenated_words(text: str) -> str:
    """Separate concatenated words using advanced NLP techniques"""
    import re
    
    # Step 1: Fix already broken words first
    text = fix_broken_words(text)
    
    # Step 2: Handle obvious patterns (camelCase, numbers, etc.)
    text = handle_obvious_patterns(text)
    
    # Step 3: Use advanced word boundary detection
    text = advanced_word_boundary_detection(text)
    
    # Step 4: Clean up any remaining issues
    text = cleanup_spacing(text)
    
    return text

def fix_broken_words(text: str) -> str:
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

def handle_obvious_patterns(text: str) -> str:
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

def advanced_word_boundary_detection(text: str) -> str:
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
            split_word = intelligent_word_splitting(word)
            processed_words.append(split_word)
        else:
            processed_words.append(word)
    
    return ' '.join(processed_words)

def intelligent_word_splitting(word: str) -> str:
    """Intelligent word splitting using linguistic analysis"""
    import re
    
    # First, try to identify common word boundaries using linguistic patterns
    word = apply_linguistic_patterns(word)
    
    # If still concatenated, use syllable-based splitting
    if len(word) > 12 and ' ' not in word:
        word = syllable_based_splitting(word)
    
    return word

def apply_linguistic_patterns(word: str) -> str:
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

def syllable_based_splitting(word: str) -> str:
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

def cleanup_spacing(text: str) -> str:
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

def fix_number_spacing(text: str) -> str:
    """Fix spacing around numbers"""
    import re
    
    # Fix numbers attached to words
    text = re.sub(r'(\d+)([a-zA-Z])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z])(\d+)', r'\1 \2', text)
    
    # Fix currency and percentage formatting
    text = re.sub(r'(\d+)([.,])(\d+)', r'\1\2\3', text)  # Keep decimal points
    text = re.sub(r'(\$)(\d+)', r'\1\2', text)  # Keep currency symbols attached
    
    return text

def normalize_capitalization(text: str) -> str:
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

def display_account_summary_results(summary_data):
    """Display the generated account summary results"""
    st.subheader(f"📊 Account Summary: {summary_data.get('account_name', 'Unknown')}")
    
    # Metadata metrics
    metadata = summary_data.get('metadata', {})
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Confidence Score", f"{metadata.get('confidence_score', 0):.1%}")
    
    with col2:
        st.metric("Total Notes", metadata.get('total_notes', 0))
    
    with col3:
        st.metric("Total Contacts", metadata.get('total_contacts', 0))
    
    with col4:
        st.metric("Total Transactions", metadata.get('total_transactions', 0))
    
    # AI Summary sections
    ai_summary = summary_data.get('summary', {})
    
    # Executive Summary
    if ai_summary.get('executive_summary'):
        st.markdown("### 🎯 Executive Summary")
        exec_summary = clean_text_for_display(ai_summary['executive_summary'])
        st.info(exec_summary)
    
    # Business Insights
    if ai_summary.get('business_insights'):
        st.markdown("### 💡 Business Insights")
        for insight in ai_summary['business_insights']:
            cleaned_insight = clean_text_for_display(insight)
            st.markdown(f"• {cleaned_insight}")
    
    # Relationship Status
    if ai_summary.get('relationship_status'):
        st.markdown("### 🤝 Relationship Status")
        relationship_status = clean_text_for_display(ai_summary['relationship_status'])
        st.info(relationship_status)
    
    # Revenue Opportunities
    if ai_summary.get('revenue_opportunities'):
        st.markdown("### 💰 Revenue Opportunities")
        for opportunity in ai_summary['revenue_opportunities']:
            cleaned_opportunity = clean_text_for_display(opportunity)
            st.markdown(f"• {cleaned_opportunity}")
    
    # Risk Factors
    if ai_summary.get('risk_factors'):
        st.markdown("### ⚠️ Risk Factors")
        for risk in ai_summary['risk_factors']:
            cleaned_risk = clean_text_for_display(risk)
            st.markdown(f"• {cleaned_risk}")
    
    # Recommended Actions
    if ai_summary.get('recommended_actions'):
        st.markdown("### 📋 Recommended Actions")
        for action in ai_summary['recommended_actions']:
            cleaned_action = clean_text_for_display(action)
            st.markdown(f"• {cleaned_action}")
    
    # Key Insights from Notes
    key_insights = summary_data.get('key_insights', [])
    if key_insights:
        st.markdown("### 🔍 Key Insights from Notes")
        for insight in key_insights:
            cleaned_insight = clean_text_for_display(insight)
            st.markdown(f"• {cleaned_insight}")
    
    # System Recommendations
    recommendations = summary_data.get('recommendations', [])
    if recommendations:
        st.markdown("### 🎯 System Recommendations")
        for rec in recommendations:
            cleaned_rec = clean_text_for_display(rec)
            st.markdown(f"• {cleaned_rec}")
    
    # System Risk Assessment
    risk_factors = summary_data.get('risk_factors', [])
    if risk_factors:
        st.markdown("### ⚠️ System Risk Assessment")
        for risk in risk_factors:
            cleaned_risk = clean_text_for_display(risk)
            st.markdown(f"• {cleaned_risk}")
    
    # Export options
    st.markdown("### 📤 Export Options")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 Export as JSON", use_container_width=True):
            import json
            from datetime import datetime
            json_data = json.dumps(summary_data, indent=2, default=str)
            st.download_button(
                label="Download JSON",
                data=json_data,
                file_name=f"account_summary_{summary_data.get('account_id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col2:
        if st.button("📊 Export as Markdown", use_container_width=True):
            # Create markdown report
            from datetime import datetime
            markdown_content = f"""# Account Summary Report

## Account Information
- **Account ID:** {summary_data.get('account_id', 'N/A')}
- **Account Name:** {summary_data.get('account_name', 'N/A')}
- **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary
{clean_text_for_display(summary_data.get('summary', {}).get('executive_summary', 'N/A'))}

## Business Insights
{chr(10).join([f"- {clean_text_for_display(insight)}" for insight in summary_data.get('summary', {}).get('business_insights', [])])}

## Recommendations
{chr(10).join([f"- {clean_text_for_display(rec)}" for rec in summary_data.get('recommendations', [])])}
"""
            
            st.download_button(
                label="Download Markdown",
                data=markdown_content,
                file_name=f"account_summary_{summary_data.get('account_id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )

def render_advanced_features():
    """Render advanced features section"""
    with st.expander("🔧 Advanced Features"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("System Information")
            if st.session_state.vectorstore_manager:
                stats = st.session_state.vectorstore_manager.get_vectorstore_stats()
                st.json(stats)
        
        with col2:
            st.subheader("Chain Information")
            if st.session_state.chat_manager:
                chain_info = st.session_state.chat_manager.get_chain_info()
                st.json(chain_info)
        
        # Test connections
        st.subheader("Connection Tests")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Test LLM Connection"):
                if st.session_state.chat_manager:
                    if st.session_state.chat_manager.test_llm_connection():
                        st.success("✅ LLM connection successful")
                    else:
                        st.error("❌ LLM connection failed")
        
        with col2:
            if st.button("Test Embeddings"):
                if st.session_state.vectorstore_manager and st.session_state.vectorstore_manager.embeddings:
                    try:
                        test_result = st.session_state.vectorstore_manager.embeddings.embed_query("test")
                        st.success("✅ Embeddings working")
                    except Exception as e:
                        st.error(f"❌ Embeddings failed: {str(e)}")
        
        # Account Summary Service Status
        if st.session_state.account_summary_service:
            st.subheader("Account Summary Service Status")
            status = st.session_state.account_summary_service.get_service_status()
            st.json(status)

def render_segmentation_section(config):
    """Render customer segmentation section"""
    st.header("🎯 Real-Time Customer Segmentation & Propensity Scoring")
    st.markdown("Advanced RFM analysis, behavioral segmentation, and campaign targeting powered by Snowflake data.")
    
    # Initialize segmentation services
    if not st.session_state.segmentation_engine:
        with st.spinner("Initializing segmentation engine..."):
            try:
                sf_manager = SnowflakeManager()
                if sf_manager.connect():
                    st.session_state.segmentation_engine = RealTimeSegmentationEngine(sf_manager)
                    st.session_state.segmentation_agent = SegmentationAgent(sf_manager)
                    st.success("✅ Segmentation engine initialized successfully!")
                else:
                    st.error("❌ Failed to connect to Snowflake")
                    return
            except Exception as e:
                st.error(f"❌ Error initializing segmentation engine: {str(e)}")
                return
    
    # Segmentation controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        lookback_days = st.slider("Analysis Period (Days)", min_value=30, max_value=730, value=365, step=30)
    
    with col2:
        if st.button("🔄 Generate Segments", type="primary"):
            with st.spinner("Generating comprehensive segmentation analysis..."):
                try:
                    st.session_state.segmentation_data = st.session_state.segmentation_engine.generate_comprehensive_segments(lookback_days)
                    st.success("✅ Segmentation analysis completed!")
                except Exception as e:
                    st.error(f"❌ Error generating segments: {str(e)}")
    
    with col3:
        if st.button("💾 Save to Snowflake"):
            if st.session_state.segmentation_data:
                with st.spinner("Saving to Snowflake..."):
                    try:
                        success = st.session_state.segmentation_engine.save_segments_to_snowflake(st.session_state.segmentation_data)
                        if success:
                            st.success("✅ Data saved to Snowflake!")
                        else:
                            st.error("❌ Failed to save to Snowflake")
                    except Exception as e:
                        st.error(f"❌ Error saving to Snowflake: {str(e)}")
            else:
                st.warning("⚠️ No segmentation data to save")
    
    # Display results if available
    if st.session_state.segmentation_data:
        display_segmentation_results(st.session_state.segmentation_data)
    else:
        st.info("👆 Click 'Generate Segments' to start the analysis")

def display_segmentation_results(segmentation_data):
    """Display segmentation analysis results"""
    
    # Overview metrics
    if 'rfm_analysis' in segmentation_data:
        rfm_df = segmentation_data['rfm_analysis']
        
        st.subheader("📊 Segmentation Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Accounts", f"{len(rfm_df):,}")
        
        with col2:
            total_revenue = rfm_df['MONETARY_VALUE'].sum()
            st.metric("Total Revenue", f"${total_revenue:,.0f}")
        
        with col3:
            avg_rfm = rfm_df['RFM_SCORE_NUMERIC'].mean()
            st.metric("Avg RFM Score", f"{avg_rfm:.2f}")
        
        with col4:
            unique_segments = rfm_df['BEHAVIORAL_SEGMENT'].nunique()
            st.metric("Segments Identified", unique_segments)
        
        # Segment distribution
        st.subheader("🎯 Behavioral Segment Distribution")
        
        if 'segment_summary' in segmentation_data:
            segment_summary = segmentation_data['segment_summary']
            
            # Create a bar chart
            import plotly.express as px
            
            fig = px.bar(
                segment_summary, 
                x='BEHAVIORAL_SEGMENT', 
                y='ACCOUNT_COUNT',
                title="Account Distribution by Segment",
                color='ACCOUNT_COUNT',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Segment details table
            st.subheader("📋 Segment Details")
            st.dataframe(
                segment_summary[['BEHAVIORAL_SEGMENT', 'ACCOUNT_COUNT', 'AVG_MONETARY_VALUE', 'TOTAL_MONETARY_VALUE', 'SEGMENT_PRIORITY']],
                use_container_width=True
            )
        
        # RFM Analysis
        st.subheader("📈 RFM Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Recency distribution
            import plotly.express as px
            fig_recency = px.histogram(rfm_df, x='RECENCY_DAYS', title="Recency Distribution (Days)")
            st.plotly_chart(fig_recency, use_container_width=True)
        
        with col2:
            # Frequency distribution
            fig_frequency = px.histogram(rfm_df, x='FREQUENCY', title="Frequency Distribution")
            st.plotly_chart(fig_frequency, use_container_width=True)
        
        # 3D RFM Scatter Plot
        st.subheader("🎯 3D RFM Visualization")
        
        import plotly.graph_objects as go
        
        fig_3d = go.Figure(data=[go.Scatter3d(
            x=rfm_df['RECENCY_DAYS'],
            y=rfm_df['FREQUENCY'],
            z=rfm_df['MONETARY_VALUE'],
            mode='markers',
            marker=dict(
                size=8,
                color=rfm_df['RFM_SCORE_NUMERIC'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="RFM Score")
            ),
            text=rfm_df['ACCOUNT_NAME'],
            hovertemplate='<b>%{text}</b><br>' +
                          'Recency: %{x} days<br>' +
                          'Frequency: %{y}<br>' +
                          'Monetary: $%{z:,.0f}<br>' +
                          '<extra></extra>'
        )])
        
        fig_3d.update_layout(
            title="3D RFM Analysis",
            scene=dict(
                xaxis_title="Recency (Days)",
                yaxis_title="Frequency",
                zaxis_title="Monetary Value ($)"
            )
        )
        
        st.plotly_chart(fig_3d, use_container_width=True)
        
        # Product Propensity Analysis
        if 'product_propensity' in segmentation_data and len(segmentation_data['product_propensity']) > 0:
            st.subheader("🎯 Product Propensity Analysis")
            
            propensity_df = segmentation_data['product_propensity']
            
            # Propensity metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Combinations", f"{len(propensity_df):,}")
            
            with col2:
                avg_propensity = propensity_df['PROPENSITY_SCORE'].mean()
                st.metric("Avg Propensity Score", f"{avg_propensity:.1f}")
            
            with col3:
                high_propensity = len(propensity_df[propensity_df['PROPENSITY_SCORE'] > 80])
                st.metric("High Propensity (>80)", f"{high_propensity:,}")
            
            with col4:
                max_propensity = propensity_df['PROPENSITY_SCORE'].max()
                st.metric("Highest Score", f"{max_propensity:.1f}")
            
            # Top propensity scores
            st.subheader("🏆 Top Product Propensity Scores")
            
            # Get top 20 propensity scores
            top_propensity = propensity_df.nlargest(20, 'PROPENSITY_SCORE')
            
            # Display as a table
            st.dataframe(
                top_propensity[['ACCOUNT_NAME', 'CATEGORY', 'BRAND', 'PROPENSITY_SCORE', 'CATEGORY_AFFINITY_SCORE', 'RECENCY_SCORE', 'FREQUENCY_SCORE']],
                use_container_width=True
            )
            
            # Propensity score distribution
            st.subheader("📊 Propensity Score Distribution")
            
            import plotly.express as px
            
            fig_propensity = px.histogram(
                propensity_df, 
                x='PROPENSITY_SCORE', 
                title="Distribution of Product Propensity Scores",
                nbins=20
            )
            fig_propensity.update_layout(xaxis_title="Propensity Score", yaxis_title="Count")
            st.plotly_chart(fig_propensity, use_container_width=True)
            
            # Category analysis
            st.subheader("📈 Top Categories by Propensity")
            
            category_propensity = propensity_df.groupby('CATEGORY').agg({
                'PROPENSITY_SCORE': ['mean', 'count'],
                'ACCOUNT_ID': 'nunique'
            }).round(2)
            
            # Flatten column names
            category_propensity.columns = ['Avg_Propensity', 'Total_Combinations', 'Unique_Accounts']
            category_propensity = category_propensity.reset_index()
            category_propensity = category_propensity.sort_values('Avg_Propensity', ascending=False)
            
            st.dataframe(category_propensity.head(10), use_container_width=True)
        
        # Business Opportunities
        st.subheader("💰 Business Opportunities")
        
        if st.button("🔍 Identify High-Value Opportunities"):
            with st.spinner("Analyzing opportunities..."):
                try:
                    opportunities = st.session_state.segmentation_agent.identify_high_value_opportunities()
                    
                    if 'opportunities' in opportunities:
                        opp_data = opportunities['opportunities']
                        
                        # At-risk customers
                        if opp_data.get('at_risk_high_value'):
                            st.subheader("⚠️ At-Risk High-Value Customers")
                            at_risk_df = pd.DataFrame(opp_data['at_risk_high_value'])
                            st.dataframe(at_risk_df, use_container_width=True)
                        
                        # New customer potential
                        if opp_data.get('promising_new_customers'):
                            st.subheader("🌟 Promising New Customers")
                            new_cust_df = pd.DataFrame(opp_data['promising_new_customers'])
                            st.dataframe(new_cust_df, use_container_width=True)
                        
                        # Expansion opportunities
                        if opp_data.get('champions_for_expansion'):
                            st.subheader("🚀 Champions for Expansion")
                            expansion_df = pd.DataFrame(opp_data['champions_for_expansion'])
                            st.dataframe(expansion_df, use_container_width=True)
                        
                        # Recommendations
                        if 'recommendations' in opportunities:
                            st.subheader("📋 Strategic Recommendations")
                            for rec in opportunities['recommendations']:
                                st.info(f"**{rec['priority']} Priority - {rec['category']}**: {rec['action']}")
                                st.caption(f"Expected Impact: {rec['expected_impact']} | Timeline: {rec['timeline']}")
                    
                except Exception as e:
                    st.error(f"❌ Error analyzing opportunities: {str(e)}")
        
        # Campaign Targeting
        st.subheader("🎯 Campaign Targeting")
        
        campaign_type = st.selectbox(
            "Select Campaign Type",
            ["promotional", "premium", "retention", "acquisition"]
        )
        
        if st.button("🎯 Generate Campaign Targeting"):
            with st.spinner("Generating campaign targeting recommendations..."):
                try:
                    targeting = st.session_state.segmentation_agent.generate_campaign_targeting_recommendations(campaign_type)
                    
                    if 'primary_targets' in targeting:
                        st.subheader(f"🎯 {campaign_type.title()} Campaign Targeting")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Primary Targets")
                            primary_df = pd.DataFrame(targeting['primary_targets'])
                            st.dataframe(primary_df, use_container_width=True)
                        
                        with col2:
                            st.subheader("Secondary Targets")
                            secondary_df = pd.DataFrame(targeting['secondary_targets'])
                            st.dataframe(secondary_df, use_container_width=True)
                        
                        # Targeting summary
                        if 'targeting_summary' in targeting:
                            summary = targeting['targeting_summary']
                            st.info(f"**Total Reach**: {summary['total_reach']} accounts ({summary['primary_count']} primary + {summary['secondary_count']} secondary)")
                    
                except Exception as e:
                    st.error(f"❌ Error generating campaign targeting: {str(e)}")

def render_cross_sell_section(config):
    """Render cross-sell optimization section"""
    st.header("🛒 Cross-Sell Optimization & Market Basket Analysis")
    st.markdown("Advanced product recommendations, market basket analysis, and promotional optimization powered by Snowflake data.")
    
    # Initialize cross-sell services
    if not st.session_state.cross_sell_engine:
        with st.spinner("Initializing cross-sell engine..."):
            try:
                sf_manager = SnowflakeManager()
                if sf_manager.connect():
                    st.session_state.cross_sell_engine = CrossSellOptimizationEngine(sf_manager)
                    st.session_state.cross_sell_agent = CrossSellAgent(sf_manager)
                    st.success("✅ Cross-sell engine initialized successfully!")
                else:
                    st.error("❌ Failed to connect to Snowflake")
                    return
            except Exception as e:
                st.error(f"❌ Error initializing cross-sell engine: {str(e)}")
                return
    
    # Cross-sell controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        lookback_days = st.slider("Analysis Period (Days)", min_value=30, max_value=730, value=365, step=30, key="cross_sell_lookback")
    
    with col2:
        if st.button("🔄 Generate Cross-Sell Analysis", type="primary", key="cross_sell_generate"):
            with st.spinner("Generating cross-sell analysis..."):
                try:
                    st.session_state.cross_sell_data = st.session_state.cross_sell_engine.generate_comprehensive_cross_sell_analysis(lookback_days)
                    st.success("✅ Cross-sell analysis completed!")
                except Exception as e:
                    st.error(f"❌ Error generating cross-sell analysis: {str(e)}")
    
    with col3:
        if st.button("💾 Save to Snowflake", key="cross_sell_save"):
            if st.session_state.cross_sell_data:
                with st.spinner("Saving to Snowflake..."):
                    try:
                        success = st.session_state.cross_sell_engine.save_cross_sell_results_to_snowflake(st.session_state.cross_sell_data)
                        if success:
                            st.success("✅ Data saved to Snowflake!")
                        else:
                            st.error("❌ Failed to save to Snowflake")
                    except Exception as e:
                        st.error(f"❌ Error saving to Snowflake: {str(e)}")
            else:
                st.warning("⚠️ No cross-sell data to save")
    
    # Display results if available
    if st.session_state.cross_sell_data:
        display_cross_sell_results(st.session_state.cross_sell_data)
    else:
        st.info("👆 Click 'Generate Cross-Sell Analysis' to start the analysis")

def display_cross_sell_results(cross_sell_data):
    """Display cross-sell analysis results"""
    
    # Overview metrics
    if 'association_rules' in cross_sell_data:
        basket_df = cross_sell_data['association_rules']
        
        st.subheader("📊 Cross-Sell Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Product Combinations", f"{len(basket_df):,}")
        
        with col2:
            avg_confidence = basket_df['CONFIDENCE'].mean() if 'CONFIDENCE' in basket_df.columns else 0
            st.metric("Avg Confidence", f"{avg_confidence:.2f}")
        
        with col3:
            high_confidence = len(basket_df[basket_df['CONFIDENCE'] > 0.5]) if 'CONFIDENCE' in basket_df.columns else 0
            st.metric("High Confidence (>50%)", f"{high_confidence:,}")
        
        with col4:
            total_support = basket_df['SUPPORT'].sum() if 'SUPPORT' in basket_df.columns else 0
            st.metric("Total Support", f"{total_support:.3f}")
        
        # Market basket analysis
        st.subheader("🛍️ Market Basket Analysis")
        
        if 'CONFIDENCE' in basket_df.columns:
            # Convert numeric columns to proper dtypes
            numeric_columns = ['SUPPORT', 'CONFIDENCE', 'LIFT']
            for col in numeric_columns:
                if col in basket_df.columns:
                    basket_df[col] = pd.to_numeric(basket_df[col], errors='coerce')
            
            # Top associations
            st.subheader("🏆 Top Product Associations")
            
            # Get top 20 associations
            top_associations = basket_df.nlargest(20, 'CONFIDENCE')
            
            # Display as a table
            display_columns = ['PRODUCT_A_CATEGORY', 'PRODUCT_A_BRAND', 'PRODUCT_B_CATEGORY', 'PRODUCT_B_BRAND', 'SUPPORT', 'CONFIDENCE', 'LIFT']
            available_columns = [col for col in display_columns if col in top_associations.columns]
            st.dataframe(
                top_associations[available_columns],
                use_container_width=True
            )
            
            # Association rules visualization
            st.subheader("📈 Association Rules Visualization")
            
            import plotly.express as px
            
            fig_associations = px.scatter(
                top_associations.head(15),
                x='SUPPORT',
                y='CONFIDENCE',
                size='LIFT',
                hover_data=['PRODUCT_A_CATEGORY', 'PRODUCT_A_BRAND', 'PRODUCT_B_CATEGORY', 'PRODUCT_B_BRAND'],
                title="Product Association Rules (Support vs Confidence)"
            )
            fig_associations.update_layout(xaxis_title="Support", yaxis_title="Confidence")
            st.plotly_chart(fig_associations, use_container_width=True)
    
    # Product affinity analysis
    if 'affinity_matrix_shape' in cross_sell_data:
        st.subheader("🎯 Product Affinity Analysis")
        
        affinity_shape = cross_sell_data['affinity_matrix_shape']
        
        # Affinity metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Matrix Dimensions", f"{affinity_shape[0]}x{affinity_shape[1]}")
        
        with col2:
            st.metric("Total Products", f"{affinity_shape[0]:,}")
        
        with col3:
            st.metric("Affinity Pairs", f"{affinity_shape[0] * affinity_shape[1]:,}")
        
        with col4:
            st.metric("Analysis Status", "✅ Complete")
        
        st.info("💡 Product affinity matrix calculated based on association rules and transaction patterns")
    
    # Promotional analysis
    if 'promotional_analysis' in cross_sell_data:
        st.subheader("🎯 Promotional Analysis")
        
        promo_df = cross_sell_data['promotional_analysis']
        
        if len(promo_df) > 0:
            # Convert numeric columns to proper dtypes
            numeric_columns = ['PROMOTIONAL_IMPACT', 'REVENUE_IMPACT']
            for col in numeric_columns:
                if col in promo_df.columns:
                    promo_df[col] = pd.to_numeric(promo_df[col], errors='coerce')
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Promotional Campaigns", f"{len(promo_df):,}")
            
            with col2:
                avg_impact = promo_df['PROMOTIONAL_IMPACT'].mean() if 'PROMOTIONAL_IMPACT' in promo_df.columns else 0
                st.metric("Avg Impact", f"{avg_impact:.2f}")
            
            with col3:
                total_revenue = promo_df['REVENUE_IMPACT'].sum() if 'REVENUE_IMPACT' in promo_df.columns else 0
                st.metric("Revenue Impact", f"${total_revenue:,.2f}")
            
            with col4:
                st.metric("Analysis Period", "90 days")
            
            # Display promotional data
            st.subheader("📊 Promotional Performance")
            st.dataframe(promo_df, use_container_width=True)
        else:
            st.info("ℹ️ No promotional data available for the selected period")
    
    # Cross-sell opportunities
    if 'opportunity_summary' in cross_sell_data:
        st.subheader("💡 Cross-Sell Opportunities")
        
        opp_df = cross_sell_data['opportunity_summary']
        
        if len(opp_df) > 0:
            # Convert numeric columns to proper dtypes
            numeric_columns = ['REVENUE_POTENTIAL']
            for col in numeric_columns:
                if col in opp_df.columns:
                    opp_df[col] = pd.to_numeric(opp_df[col], errors='coerce')
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Opportunities", f"{len(opp_df):,}")
            
            with col2:
                avg_potential = opp_df['REVENUE_POTENTIAL'].mean() if 'REVENUE_POTENTIAL' in opp_df.columns else 0
                st.metric("Avg Revenue Potential", f"${avg_potential:,.2f}")
            
            with col3:
                total_potential = opp_df['REVENUE_POTENTIAL'].sum() if 'REVENUE_POTENTIAL' in opp_df.columns else 0
                st.metric("Total Revenue Potential", f"${total_potential:,.2f}")
            
            with col4:
                st.metric("Priority Level", "High")
            
            # Display opportunities
            st.subheader("🏆 Top Cross-Sell Opportunities")
            st.dataframe(opp_df, use_container_width=True)
        else:
            st.info("ℹ️ No cross-sell opportunities identified")
    
    # Segment insights
    if 'segment_insights' in cross_sell_data:
        st.subheader("📈 Segment Insights")
        
        insights = cross_sell_data['segment_insights']
        
        if insights:
            for segment, data in insights.items():
                with st.expander(f"Segment: {segment}"):
                    st.write(f"**Strategy:** {data.get('strategy', 'N/A')}")
                    st.write(f"**Focus:** {data.get('focus', 'N/A')}")
                    st.write(f"**Priority:** {data.get('priority', 'N/A')}")
    
    # Account-specific recommendations (using agent)
    st.subheader("🎯 Account-Specific Recommendations")
    
    account_id = st.text_input("Enter Account ID for Recommendations", placeholder="e.g., ACC0001")
    
    if st.button("🔍 Get Recommendations", key="get_account_recs"):
        if account_id:
            with st.spinner("Generating account-specific recommendations..."):
                try:
                    recommendations = st.session_state.cross_sell_agent.analyze_account_cross_sell_opportunities(account_id)
                    
                    if 'recommendations' in recommendations and recommendations['recommendations']:
                        st.success(f"✅ Found {len(recommendations['recommendations'])} recommendations for {account_id}")
                        
                        # Display account info
                        if 'account_name' in recommendations:
                            st.info(f"**Account:** {recommendations['account_name']} | **Segment:** {recommendations.get('segment', 'N/A')}")
                        
                        for i, rec in enumerate(recommendations['recommendations'][:10], 1):
                            with st.expander(f"Recommendation {i}: {rec.get('recommended_category', 'Unknown Category')} - {rec.get('recommended_brand', 'Unknown Brand')}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write(f"**Recommended Category:** {rec.get('recommended_category', 'N/A')}")
                                    st.write(f"**Recommended Brand:** {rec.get('recommended_brand', 'N/A')}")
                                    st.write(f"**Trigger Category:** {rec.get('trigger_category', 'N/A')}")
                                    st.write(f"**Confidence:** {rec.get('confidence', 0):.3f}")
                                
                                with col2:
                                    st.write(f"**Lift:** {rec.get('lift', 0):.2f}")
                                    st.write(f"**Support:** {rec.get('support', 0):.3f}")
                                    st.write(f"**Final Score:** {rec.get('final_score', 0):.1f}")
                                    st.write(f"**Avg Basket Value:** ${rec.get('avg_basket_value', 0):,.2f}")
                                
                                # Display suggested products if available
                                if 'suggested_products' in rec and rec['suggested_products']:
                                    st.write("**Suggested Products:**")
                                    for product in rec['suggested_products'][:3]:  # Show top 3 products
                                        st.write(f"• {product.get('PRODUCT_NAME', 'N/A')} - ${product.get('UNIT_PRICE', 0):,.2f}")
                        
                        # Display active promotions if available
                        if 'active_promotions' in recommendations and recommendations['active_promotions']:
                            st.subheader("🎯 Active Promotions")
                            for promo in recommendations['active_promotions'][:3]:  # Show top 3 promotions
                                st.write(f"• **{promo.get('CAMPAIGN_NAME', 'N/A')}** - {promo.get('DISCOUNT_PERCENTAGE', 0)}% off")
                    else:
                        st.warning(f"⚠️ No recommendations found for account {account_id}")
                        
                except Exception as e:
                    st.error(f"❌ Error generating recommendations: {str(e)}")
        else:
            st.warning("⚠️ Please enter an Account ID")

def main():
    """Main application function"""
    # Initialize session state
    initialize_session_state()
    
    # App header
    st.title("📚 Agentic AI with OpenAI & FAISS")
    st.markdown("Upload a PDF and chat with its content using OpenAI's powerful language models!")
    
    # Render sidebar and get configuration
    config = render_sidebar()
    
    # Status panel
    render_status_panel()
    
    # Main content
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📄 Upload PDF", "💬 Chat", "📊 Account Summary", "🎯 Customer Segmentation", "🛒 Cross-Sell Optimization", "🔧 Advanced"])
    
    with tab1:
        render_pdf_upload_section(config)
    
    with tab2:
        render_chat_section(config)
    
    with tab3:
        render_account_summary_section(config)
    
    with tab4:
        render_segmentation_section(config)
    
    with tab5:
        render_cross_sell_section(config)
    
    with tab6:
        render_advanced_features()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    **Built with:** Streamlit • LangChain • FAISS • OpenAI • UV Package Manager • Snowflake
    
    **Features:**
    - 📄 PDF Document Chat with AI
    - 📊 AI-Powered Account Summary Generation
    - 🔍 Advanced Analytics and Insights
    
    **Requirements:**
    - OpenAI API key
    - Snowflake database connection
    - Internet connection for API calls
    - Python environment managed with UV
    """)

if __name__ == "__main__":
    main()
