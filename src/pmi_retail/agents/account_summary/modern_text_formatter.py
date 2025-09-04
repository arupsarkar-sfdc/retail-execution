"""
Reliable Text Formatter - Rewritten for Consistency
Focuses on reliability over complexity with proper error handling
"""

import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import re
import time
import logging
from typing import Optional, Dict, Any

# Configure logging to show in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # This ensures logs go to console
    ]
)
logger = logging.getLogger(__name__)


class ReliableTextFormatter:
    """
    A reliable text formatter that consistently fixes LLM output issues.
    Designed for production use with proper error handling and retries.
    """
    
    def __init__(self, model_name: str = "gpt-4", api_key: Optional[str] = None):
        """
        Initialize the formatter with consistent settings
        
        Args:
            model_name: OpenAI model to use for formatting
            api_key: OpenAI API key (optional if set in environment)
        """
        self.model_name = model_name
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        
        try:
            self.llm = ChatOpenAI(
                model_name=model_name,
                temperature=0.0,  # Zero temperature for maximum consistency
                max_tokens=4000,
                openai_api_key=api_key,
                request_timeout=30
            )
            logger.info(f"Initialized formatter with model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize ChatOpenAI: {e}")
            raise
        
        # Simple, reliable system prompt
        self.system_prompt = """You are a professional text formatting specialist. Your only job is to fix formatting issues in business text.

FORMATTING RULES:
1. Add spaces between concatenated words (e.g., "Theaccounthas" → "The account has")
2. Fix broken words with extra spaces (e.g., "indepen dent" → "independent")
3. Add proper spacing after punctuation (e.g., "revenue.The" → "revenue. The")
4. Fix spacing around numbers and currency (e.g., "492.00The" → "492.00. The")
5. Ensure proper sentence capitalization and structure

IMPORTANT:
- Keep ALL factual information exactly the same (numbers, names, dates, amounts)
- Only fix spacing, punctuation, and word boundaries
- Do not change the meaning or add new information
- Do not remove any content
- Return only the corrected text with no explanations

If the text is already properly formatted, return it unchanged."""

    def format_text(self, text: str, show_progress: bool = False) -> str:
        """
        Format text with reliable error handling and retries
        
        Args:
            text: Text to format
            show_progress: Show Streamlit progress indicator
            
        Returns:
            Formatted text or original text if formatting fails
        """
        if not text or not text.strip():
            return text
        
        logger.info(f"🔍 Formatting text (length: {len(text)} chars): {text[:100]}...")
        
        # Quick check - if text looks fine, return as-is
        if self._text_looks_good(text):
            logger.debug("Text appears well-formatted, skipping LLM call")
            return text
        
        # Show progress if requested
        progress_placeholder = None
        if show_progress and 'streamlit' in str(type(st)):
            progress_placeholder = st.empty()
            progress_placeholder.info("🔧 Formatting text...")
        
        try:
            formatted_text = self._format_with_retries(text)
            
            # Clear progress indicator
            if progress_placeholder:
                progress_placeholder.empty()
            
            # Validate the result
            if self._is_valid_result(text, formatted_text):
                logger.info("Text formatting successful")
                return formatted_text
            else:
                logger.warning("Formatted text failed validation, returning original")
                return text
                
        except Exception as e:
            logger.error(f"Text formatting failed completely: {e}")
            if progress_placeholder:
                progress_placeholder.error("❌ Formatting failed, using original text")
                time.sleep(2)
                progress_placeholder.empty()
            return text
    
    def _text_looks_good(self, text: str) -> bool:
        """
        Quick heuristic check if text needs formatting
        Only catches obvious issues to avoid unnecessary API calls
        """
        issues = [
            r'[0-9][a-z]',      # number + letter (00and)
            r'[a-z][0-9]',      # letter + number (and260)  
            r'\.[A-Z]',         # period + capital (.The)
            r'[a-z][A-Z]',      # lower + upper
            r'\b[a-zA-Z]{15,}\b' # very long words
        ]
        # Check if text needs formatting
        needs_formatting = any(re.search(pattern, text) for pattern in issues)
        
        if needs_formatting:
            logger.info("🔧 Text formatting issues detected - will apply LLM formatting")
        else:
            logger.info("✅ Text appears well-formatted, skipping LLM call")
        
        return not needs_formatting
    
    def _format_with_retries(self, text: str) -> str:
        """
        Attempt formatting with retry logic
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Formatting attempt {attempt + 1}/{self.max_retries}")
                
                messages = [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=f"Fix the formatting issues in this text:\n\n{text}")
                ]
                
                response = self.llm(messages)
                formatted_text = response.content.strip()
                
                if formatted_text:
                    return formatted_text
                else:
                    raise ValueError("LLM returned empty response")
                    
            except Exception as e:
                last_error = e
                logger.warning(f"Formatting attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2  # Exponential backoff
        
        # All retries failed
        raise Exception(f"All formatting attempts failed. Last error: {last_error}")
    
    def _is_valid_result(self, original: str, formatted: str) -> bool:
        """
        Validate that formatting didn't break the content
        """
        if not formatted or len(formatted.strip()) == 0:
            return False
        
        # Result shouldn't be drastically shorter (content loss)
        if len(formatted) < len(original) * 0.7:
            logger.warning("Formatted text is much shorter than original")
            return False
        
        # Result shouldn't be drastically longer (hallucination)
        if len(formatted) > len(original) * 1.5:
            logger.warning("Formatted text is much longer than original")
            return False
        
        # Check that key numbers are preserved (more lenient validation)
        # Extract major numbers (currency amounts, percentages, etc.)
        original_major_numbers = re.findall(r'\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?', original)
        formatted_major_numbers = re.findall(r'\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?', formatted)
        
        # Allow some flexibility in number formatting (spacing changes are OK)
        if len(original_major_numbers) > 0 and len(formatted_major_numbers) == 0:
            logger.warning("All major numbers were lost during formatting")
            return False
        
        # Check that the formatted text actually looks better (has proper spacing)
        has_proper_spacing = bool(re.search(r'[a-z]\s+[A-Z]', formatted))  # Word boundaries
        has_concatenation_issues = bool(re.search(r'[a-z][A-Z]', formatted))  # Still has concatenation
        
        # If it still has concatenation issues, it might not be properly formatted
        if has_concatenation_issues and not has_proper_spacing:
            logger.warning("Formatted text still has concatenation issues")
            return False
        
        return True


class StreamlitTextFormatter:
    """
    Streamlit-specific wrapper with UI integration
    """
    
    def __init__(self, model_name: str = "gpt-4"):
        """Initialize with caching for Streamlit"""
        self.model_name = model_name
        self._formatter = None
    
    @property
    def formatter(self) -> ReliableTextFormatter:
        """Lazy initialization of formatter (for Streamlit caching)"""
        if self._formatter is None:
            self._formatter = ReliableTextFormatter(self.model_name)
        return self._formatter
    
    def format_and_display(self, text: str, container=None) -> str:
        """
        Format text and display in Streamlit with user feedback
        
        Args:
            text: Text to format
            container: Streamlit container to display in
            
        Returns:
            Formatted text
        """
        if container is None:
            container = st
        
        if not text or not text.strip():
            container.warning("⚠️ No text provided for formatting")
            return ""
        
        # Format the text
        formatted_text = self.formatter.format_text(text, show_progress=True)
        
        # Display result
        if formatted_text != text:
            container.success("✅ Text formatting completed")
            container.markdown(formatted_text)
            
            # Show comparison option
            with container.expander("🔍 Compare Original vs Formatted"):
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Original")
                    st.text_area("", text, height=150, disabled=True, key="orig")
                with col2:
                    st.subheader("Formatted")
                    st.text_area("", formatted_text, height=150, disabled=True, key="fmt")
        else:
            container.info("ℹ️ Text was already properly formatted")
            container.markdown(formatted_text)
        
        return formatted_text
    
    def format_text_simple(self, text: str) -> str:
        """Simple formatting without UI feedback"""
        return self.formatter.format_text(text, show_progress=False)
    
    def format_text_safe(self, text: str) -> str:
        """
        Format text with error handling - returns original if formatting fails
        """
        try:
            return self.format_text_simple(text)
        except Exception as e:
            logger.error(f"Text formatting failed: {e}")
            return text  # Return original text if formatting fails


# Cached formatter for Streamlit apps
@st.cache_resource
def get_cached_formatter(model_name: str = "gpt-4") -> StreamlitTextFormatter:
    """
    Get a cached formatter instance for Streamlit apps
    This prevents re-initialization on every run
    """
    return StreamlitTextFormatter(model_name)


class EnhancedAccountSummaryGenerator:
    """
    Enhanced account summary generator with reliable formatting
    """
    
    def __init__(self, summary_llm, model_name: str = "gpt-4"):
        """
        Initialize with existing LLM for summary generation
        
        Args:
            summary_llm: Your existing LangChain LLM for generating summaries
            model_name: Model name for the formatter
        """
        self.summary_llm = summary_llm
        self.formatter = ReliableTextFormatter(model_name)
    
    def generate_formatted_summary(self, account_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate account summary with automatic formatting
        
        Args:
            account_data: Dictionary containing account information
            
        Returns:
            Dictionary with 'raw' and 'formatted' summary text
        """
        # Create summary prompt
        prompt = self._create_summary_prompt(account_data)
        
        # Generate raw summary
        try:
            response = self.summary_llm([HumanMessage(content=prompt)])
            raw_summary = response.content
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return {
                'raw': f"Error generating summary: {e}",
                'formatted': f"Error generating summary: {e}",
                'success': False
            }
        
        # Format the summary
        formatted_summary = self.formatter.format_text(raw_summary)
        
        return {
            'raw': raw_summary,
            'formatted': formatted_summary,
            'success': True,
            'formatting_applied': raw_summary != formatted_summary
        }
    
    def _create_summary_prompt(self, account_data: Dict[str, Any]) -> str:
        """Create a well-structured prompt for summary generation"""
        return f"""Generate a professional executive summary for this retail account.

Account Details:
- Name: {account_data.get('name', 'Unknown')}
- Location: {account_data.get('location', 'Unknown')}
- Annual Revenue: ${account_data.get('revenue', 0):,.2f}
- Total Transactions: {account_data.get('transactions', 0)}
- Account Type: {account_data.get('type', 'Unknown')}
- Segment: {account_data.get('segment', 'Unknown')}

Please provide:
1. A 2-3 sentence executive summary
2. 3-4 key business insights
3. Relationship status assessment

Format your response professionally for a business report. Use proper spacing and complete sentences."""


# Quick integration function for existing code
def quick_format_fix(text: str) -> str:
    """
    Quick formatting fix for immediate integration
    
    Usage:
        # In your existing Streamlit app
        raw_summary = your_existing_llm_call()
        clean_summary = quick_format_fix(raw_summary)
        st.markdown(clean_summary)
    """
    try:
        formatter = ReliableTextFormatter()
        return formatter.format_text(text)
    except Exception as e:
        logger.error(f"Quick formatting failed: {e}")
        return text  # Return original on error


# Backward compatibility aliases
ModernTextFormatter = ReliableTextFormatter  # For existing code compatibility
