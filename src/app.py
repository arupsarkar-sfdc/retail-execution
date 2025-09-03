"""
Main Streamlit Application
PDF Chat QA with OpenAI, FAISS, and LangChain
"""

import os
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path

# Import custom components
from pmi_retail.agents.components.pdf_processor import PDFProcessor
from pmi_retail.agents.components.vectorstore import VectorStoreManager
from pmi_retail.agents.components.chat_chain import ChatChainManager
from pmi_retail.agents.account_summary import AccountSummaryService

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
        st.info(ai_summary['executive_summary'])
    
    # Business Insights
    if ai_summary.get('business_insights'):
        st.markdown("### 💡 Business Insights")
        for insight in ai_summary['business_insights']:
            st.markdown(f"• {insight}")
    
    # Relationship Status
    if ai_summary.get('relationship_status'):
        st.markdown("### 🤝 Relationship Status")
        st.info(ai_summary['relationship_status'])
    
    # Revenue Opportunities
    if ai_summary.get('revenue_opportunities'):
        st.markdown("### 💰 Revenue Opportunities")
        for opportunity in ai_summary['revenue_opportunities']:
            st.markdown(f"• {opportunity}")
    
    # Risk Factors
    if ai_summary.get('risk_factors'):
        st.markdown("### ⚠️ Risk Factors")
        for risk in ai_summary['risk_factors']:
            st.markdown(f"• {risk}")
    
    # Recommended Actions
    if ai_summary.get('recommended_actions'):
        st.markdown("### 📋 Recommended Actions")
        for action in ai_summary['recommended_actions']:
            st.markdown(f"• {action}")
    
    # Key Insights from Notes
    key_insights = summary_data.get('key_insights', [])
    if key_insights:
        st.markdown("### 🔍 Key Insights from Notes")
        for insight in key_insights:
            st.markdown(f"• {insight}")
    
    # System Recommendations
    recommendations = summary_data.get('recommendations', [])
    if recommendations:
        st.markdown("### 🎯 System Recommendations")
        for rec in recommendations:
            st.markdown(f"• {rec}")
    
    # System Risk Assessment
    risk_factors = summary_data.get('risk_factors', [])
    if risk_factors:
        st.markdown("### ⚠️ System Risk Assessment")
        for risk in risk_factors:
            st.markdown(f"• {risk}")
    
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
{summary_data.get('summary', {}).get('executive_summary', 'N/A')}

## Business Insights
{chr(10).join([f"- {insight}" for insight in summary_data.get('summary', {}).get('business_insights', [])])}

## Recommendations
{chr(10).join([f"- {rec}" for rec in summary_data.get('recommendations', [])])}
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
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Upload PDF", "💬 Chat", "📊 Account Summary", "🔧 Advanced"])
    
    with tab1:
        render_pdf_upload_section(config)
    
    with tab2:
        render_chat_section(config)
    
    with tab3:
        render_account_summary_section(config)
    
    with tab4:
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
