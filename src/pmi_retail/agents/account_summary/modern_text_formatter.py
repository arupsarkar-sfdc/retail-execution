"""
Modern LLM Text Formatting Solution
Uses prompt engineering and proper tokenization handling like Claude/GPT-4
"""

import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.callbacks import StreamlitCallbackHandler
import tiktoken
import re
import logging

logger = logging.getLogger(__name__)

class ModernTextFormatter:
    """
    Handles text formatting using modern LLM techniques:
    1. Proper system prompts for formatting instructions
    2. Token-aware processing
    3. Self-correction through the LLM
    4. Context-aware formatting
    """
    
    def __init__(self, model_name="gpt-4", temperature=0.1):
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            max_tokens=2000
        )
        
        # Get tokenizer for the model
        try:
            self.tokenizer = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback for models not in tiktoken
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # System prompt that instructs the LLM on proper formatting
        self.formatting_system_prompt = """You are a text formatting specialist. Your task is to:

1. Fix any broken words or awkward line breaks in the provided text
2. Ensure proper spacing and punctuation
3. Maintain the original meaning and structure
4. Output clean, readable text suitable for business reports
5. Do NOT change the factual content, only fix formatting issues
6. Ensure all words are complete and properly spelled
7. Fix any tokenization artifacts or broken word boundaries
8. Preserve numbers, dates, and currency formatting
9. Maintain proper sentence structure and capitalization

Return ONLY the corrected text without any explanations or additional commentary."""

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using the model's tokenizer"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed: {e}")
            # Fallback: rough estimation
            return len(text.split()) * 1.3
    
    def chunk_text_by_tokens(self, text: str, max_tokens: int = 3000) -> list:
        """
        Split text into chunks that respect token limits and word boundaries
        """
        if self.count_tokens(text) <= max_tokens:
            return [text]
        
        # Split by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if self.count_tokens(test_chunk) <= max_tokens:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks
    
    def format_with_llm(self, broken_text: str) -> str:
        """
        Use the LLM itself to fix formatting issues
        This is how modern LLMs like Claude handle it internally
        """
        try:
            # Check if text needs formatting (has obvious issues)
            if not self._needs_formatting(broken_text):
                return broken_text
            
            messages = [
                SystemMessage(content=self.formatting_system_prompt),
                HumanMessage(content=f"Fix the formatting in this text:\n\n{broken_text}")
            ]
            
            response = self.llm(messages)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error in LLM formatting: {str(e)}")
            return broken_text  # Return original if formatting fails
    
    def _needs_formatting(self, text: str) -> bool:
        """
        Detect if text has formatting issues that need fixing
        Uses pattern matching to identify common tokenization problems
        """
        issues = [
            # Broken words (consonant + space + short fragment + space + vowel/consonant)
            r'\b[bcdfghjklmnpqrstvwxyz]+\s+[a-z]{1,3}\s+[a-z]+\b',
            # Multiple single characters with spaces
            r'\b[a-z]\s+[a-z]\s+[a-z]\b',
            # Broken contractions
            r'\b\w+\s+\'[a-z]+\b',
            # Broken numbers/currency
            r'\$\s+\d+|\d+\s*,\s*\d+',
            # Common word endings separated
            r'\b\w+\s+(tion|sion|ment|ing|ed|er|est|ly|al|ic|ous|ful)\b',
            # Specific patterns from your screenshots
            r'\bin\s+depe\s+nd\s+ent\b',
            r'\bJacks\s+on\s+ville\b',
            r'\bc\s+on\s+sistent\b',
            r'\btra\s+ns\s+acti\s+on\b',
            r'\bengage\s+ment\b',
            r'\bca\s+mp\s+aigns\b',
            # NEW: Concatenated words without spaces (like "Theaccounthasatotalof")
            r'\b[a-z]+[A-Z][a-z]+\b',  # camelCase concatenation
            r'\b[a-z]+\d+[a-z]+\b',    # word + number + word concatenation
            r'\b\d+[a-z]+\b',          # number + word concatenation
            r'\b[a-z]+\d+\b',          # word + number concatenation
            # NEW: Specific concatenated patterns from Executive Summary
            r'\bTheaccounthasatotalof\b',
            r'\btransactionswithanaveragetransactionvalueof\b',
            r'\baccountisengaged\b',
            r'\bmarketingcampaigns\b',
            r'\btotalbudget\b',
            r'\bannualrevenue\b',
            r'\btransactionvalue\b',
            r'\bactivecampaigns\b',
            # NEW: Period followed immediately by capital letter (no space)
            r'\.\s*[A-Z]',             # period followed by capital letter
            # NEW: Long concatenated words (more than 15 characters without spaces)
            r'\b[a-zA-Z]{15,}\b',      # very long words likely concatenated
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in issues)
    
    def process_long_text(self, text: str) -> str:
        """
        Process long text by chunking and formatting each piece
        """
        chunks = self.chunk_text_by_tokens(text)
        formatted_chunks = []
        
        for chunk in chunks:
            formatted_chunk = self.format_with_llm(chunk)
            formatted_chunks.append(formatted_chunk)
        
        return " ".join(formatted_chunks)


class SmartStreamlitFormatter:
    """
    Streamlit-specific formatter that handles real-time text processing
    """
    
    def __init__(self):
        self.formatter = ModernTextFormatter()
        
    def format_and_display(self, text: str, container=None):
        """
        Format text and display in Streamlit with proper handling
        """
        if container is None:
            container = st
            
        # Show original if there's an issue
        if not text or len(text.strip()) == 0:
            container.write("No content to display.")
            return
        
        # Format the text using LLM
        with st.spinner("Formatting text..."):
            formatted_text = self.formatter.format_with_llm(text)
        
        # Display formatted text
        container.markdown(formatted_text)
        
        # Optional: Show a comparison
        with st.expander("Show original vs formatted"):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Original")
                st.text(text)
            with col2:
                st.subheader("Formatted")
                st.text(formatted_text)


# Enhanced prompt templates for generating properly formatted content
class FormattingPrompts:
    """
    Prompt templates that encourage proper formatting from the start
    """
    
    @staticmethod
    def get_account_summary_prompt(account_data: dict) -> str:
        return f"""Generate a professional executive summary for the following account. 
Ensure your response is well-formatted with proper word spacing and complete sentences.

Account Data: {account_data}

Please provide:
1. Executive Summary (2-3 sentences)
2. Key Business Insights (3-4 bullet points)  
3. Relationship Status (1-2 sentences)

Format your response as clean, readable text suitable for a business report. 
Ensure all words are complete and properly spaced."""
    
    @staticmethod
    def get_relationship_status_prompt(account_data: dict) -> str:
        return f"""Analyze the relationship status for this account and provide insights.
Format your response as professional, well-structured text.

Account Data: {account_data}

Provide analysis on:
- Overall satisfaction level
- Engagement frequency  
- Communication quality
- Trust indicators

Ensure your response uses complete words and proper formatting."""


# Alternative: Direct integration into your existing code
class EnhancedLangchainFormatter:
    """
    Integration with your existing Langchain setup
    """
    
    def __init__(self, llm):
        self.llm = llm
        self.formatter = ModernTextFormatter()
    
    def generate_and_format(self, prompt: str, format_output: bool = True):
        """
        Generate content and optionally format it
        """
        # Generate content
        response = self.llm([HumanMessage(content=prompt)])
        raw_content = response.content
        
        # Format if needed
        if format_output and self.formatter._needs_formatting(raw_content):
            return self.formatter.format_with_llm(raw_content)
        
        return raw_content


# Simple integration class for your existing code
class StreamlitTextFormatter:
    """
    Simple formatter for direct integration into your Streamlit app
    """
    
    def __init__(self, model_name="gpt-4", temperature=0.1):
        self.formatter = ModernTextFormatter(model_name, temperature)
    
    def format_text(self, text: str) -> str:
        """
        Format text using LLM-based approach
        """
        if not text or not text.strip():
            return text
        
        return self.formatter.format_with_llm(text)
    
    def format_text_safe(self, text: str) -> str:
        """
        Format text with error handling - returns original if formatting fails
        """
        try:
            return self.format_text(text)
        except Exception as e:
            logger.error(f"Text formatting failed: {e}")
            return text  # Return original text if formatting fails
