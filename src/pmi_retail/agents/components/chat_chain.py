"""
Chat Chain Component
Handles LangChain QA chain creation and chat functionality with OpenAI
"""

from typing import Dict, Any, List, Optional
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.schema import Document
import os


class ChatChainManager:
    """Manages LangChain QA chains and chat functionality with OpenAI"""
    
    def __init__(self, 
                 model_name: str = "gpt-3.5-turbo",
                 api_key: str = None,
                 temperature: float = 0.1,
                 max_tokens: int = 1000):
        """
        Initialize Chat Chain Manager
        
        Args:
            model_name: OpenAI model name
            api_key: OpenAI API key (if None, uses environment variable)
            temperature: Model temperature for response generation
            max_tokens: Maximum tokens in response
        """
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = None
        self.qa_chain = None
        self.conversational_chain = None
        self.memory = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize OpenAI LLM"""
        try:
            if not self.api_key:
                st.error("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
                return
            
            self.llm = ChatOpenAI(
                model=self.model_name,
                openai_api_key=self.api_key,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Test the LLM
            test_response = self.llm.invoke("Hello")
            if test_response:
                st.success(f"OpenAI LLM initialized with model: {self.model_name}")
        except Exception as e:
            st.error(f"Error initializing OpenAI LLM: {str(e)}")
            if "api key" in str(e).lower():
                st.error("Please check your OpenAI API key")
            elif "quota" in str(e).lower():
                st.error("OpenAI API quota exceeded")
            elif "rate limit" in str(e).lower():
                st.error("OpenAI API rate limit exceeded")
            self.llm = None
    
    def create_simple_qa_chain(self, retriever, return_source_documents: bool = True):
        """
        Create a simple RetrievalQA chain
        
        Args:
            retriever: Vectorstore retriever
            return_source_documents: Whether to return source documents
            
        Returns:
            RetrievalQA chain or None if error
        """
        if not self.llm:
            st.error("OpenAI LLM not initialized")
            return None
        
        try:
            # Custom prompt template optimized for OpenAI models
            prompt_template = """You are a helpful assistant that answers questions based on the provided context. 
            Use the following pieces of context to answer the question at the end. 
            If you don't know the answer based on the context, just say that you don't know, don't try to make up an answer.
            
            Context:
            {context}
            
            Question: {question}
            
            Answer: """
            
            PROMPT = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )
            
            # Create RetrievalQA chain
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                chain_type_kwargs={"prompt": PROMPT},
                return_source_documents=return_source_documents
            )
            
            st.success("Simple QA chain created successfully")
            return self.qa_chain
            
        except Exception as e:
            st.error(f"Error creating QA chain: {str(e)}")
            return None
    
    def create_conversational_chain(self, retriever):
        """
        Create a ConversationalRetrievalChain with memory
        
        Args:
            retriever: Vectorstore retriever
            
        Returns:
            ConversationalRetrievalChain or None if error
        """
        if not self.llm:
            st.error("OpenAI LLM not initialized")
            return None
        
        try:
            # Initialize memory
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
            
            # Custom prompt for conversational QA - optimized for OpenAI
            custom_template = """Given the following conversation and a follow up question, 
            rephrase the follow up question to be a standalone question, in its original language.
            Make sure to avoid using any unclear pronouns.
            
            Chat History:
            {chat_history}
            Follow Up Input: {question}
            Standalone question:"""
            
            CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(custom_template)
            
            # QA prompt optimized for OpenAI models
            qa_template = """You are an AI assistant for question-answering tasks. 
            Use the following pieces of retrieved context to answer the question. 
            If you don't know the answer based on the context, say that you don't know. 
            Keep the answer concise but comprehensive.
            
            Context: {context}
            Question: {question}
            Answer: """
            
            QA_PROMPT = PromptTemplate(
                template=qa_template,
                input_variables=["context", "question"]
            )
            
            # Create conversational chain
            self.conversational_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=retriever,
                memory=self.memory,
                condense_question_prompt=CONDENSE_QUESTION_PROMPT,
                combine_docs_chain_kwargs={"prompt": QA_PROMPT},
                return_source_documents=True,
                verbose=False
            )
            
            st.success("Conversational chain created successfully")
            return self.conversational_chain
            
        except Exception as e:
            st.error(f"Error creating conversational chain: {str(e)}")
            return None
    
    def ask_question(self, question: str, chain_type: str = "simple") -> Dict[str, Any]:
        """
        Ask a question using the specified chain
        
        Args:
            question: Question to ask
            chain_type: "simple" or "conversational"
            
        Returns:
            Dictionary with answer and source documents
        """
        try:
            if chain_type == "simple" and self.qa_chain:
                with st.spinner("Getting answer from OpenAI..."):
                    result = self.qa_chain({"query": question})
                return {
                    "answer": result.get("result", "No answer generated"),
                    "source_documents": result.get("source_documents", []),
                    "success": True
                }
            
            elif chain_type == "conversational" and self.conversational_chain:
                with st.spinner("Getting answer from OpenAI..."):
                    result = self.conversational_chain({"question": question})
                return {
                    "answer": result.get("answer", "No answer generated"),
                    "source_documents": result.get("source_documents", []),
                    "success": True
                }
            
            else:
                return {
                    "answer": "No chain available for the specified type",
                    "source_documents": [],
                    "success": False
                }
                
        except Exception as e:
            error_msg = str(e)
            st.error(f"Error asking question: {error_msg}")
            
            # Handle specific OpenAI errors
            if "rate limit" in error_msg.lower():
                st.error("OpenAI API rate limit exceeded. Please wait and try again.")
            elif "quota" in error_msg.lower():
                st.error("OpenAI API quota exceeded. Please check your usage.")
            elif "api key" in error_msg.lower():
                st.error("Invalid OpenAI API key. Please check your configuration.")
            
            return {
                "answer": f"Error: {error_msg}",
                "source_documents": [],
                "success": False
            }
    
    def get_chat_history(self) -> List[Dict[str, str]]:
        """
        Get chat history from conversational memory
        
        Returns:
            List of chat history messages
        """
        if not self.memory:
            return []
        
        try:
            # Extract messages from memory
            messages = self.memory.chat_memory.messages
            history = []
            
            for i in range(0, len(messages), 2):
                if i + 1 < len(messages):
                    history.append({
                        "question": messages[i].content,
                        "answer": messages[i + 1].content
                    })
            
            return history
            
        except Exception as e:
            st.error(f"Error retrieving chat history: {str(e)}")
            return []
    
    def clear_memory(self):
        """Clear conversational memory"""
        if self.memory:
            self.memory.clear()
            st.success("Chat history cleared")
        else:
            st.warning("No memory to clear")
    
    def update_llm_settings(self, 
                           model_name: str = None, 
                           temperature: float = None,
                           max_tokens: int = None) -> bool:
        """
        Update LLM settings
        
        Args:
            model_name: New model name (optional)
            temperature: New temperature (optional)
            max_tokens: New max tokens (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if model_name:
                self.model_name = model_name
            if temperature is not None:
                self.temperature = temperature
            if max_tokens is not None:
                self.max_tokens = max_tokens
            
            # Reinitialize LLM
            self._initialize_llm()
            
            # Reset chains (they need to be recreated with new LLM)
            self.qa_chain = None
            self.conversational_chain = None
            
            if self.llm:
                st.success("OpenAI LLM settings updated. Please recreate chains.")
                return True
            return False
            
        except Exception as e:
            st.error(f"Error updating LLM settings: {str(e)}")
            return False
    
    def get_chain_info(self) -> Dict[str, Any]:
        """
        Get information about current chains and LLM
        
        Returns:
            Dictionary with chain information
        """
        return {
            "llm_model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "llm_status": "Active" if self.llm else "Not initialized",
            "simple_qa_chain": "Active" if self.qa_chain else "Not created",
            "conversational_chain": "Active" if self.conversational_chain else "Not created",
            "memory_status": "Active" if self.memory else "Not initialized",
            "chat_history_length": len(self.get_chat_history()) if self.memory else 0,
            "api_key_set": bool(self.api_key)
        }
    
    def test_llm_connection(self) -> bool:
        """
        Test OpenAI LLM connection
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.llm:
            return False
        
        try:
            response = self.llm.invoke("Say 'Hello' if you can hear me.")
            return bool(response and response.content and "hello" in response.content.lower())
        except Exception as e:
            st.error(f"OpenAI LLM connection test failed: {str(e)}")
            return False
    
    def estimate_cost(self, question: str, context_length: int = 1000) -> Dict[str, Any]:
        """
        Estimate the cost for a question
        
        Args:
            question: The question to ask
            context_length: Estimated context length in tokens
            
        Returns:
            Dictionary with cost estimation
        """
        try:
            # Rough token estimation (1 token ≈ 4 characters)
            question_tokens = len(question) / 4
            total_input_tokens = question_tokens + context_length
            
            # OpenAI pricing (as of 2024) - input/output per 1K tokens
            pricing = {
                "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
                "gpt-4": {"input": 0.03, "output": 0.06},
                "gpt-4-turbo": {"input": 0.01, "output": 0.03},
                "gpt-4o": {"input": 0.005, "output": 0.015},
                "gpt-4o-mini": {"input": 0.00015, "output": 0.0006}
            }
            
            model_pricing = pricing.get(self.model_name, pricing["gpt-3.5-turbo"])
            
            input_cost = (total_input_tokens / 1000) * model_pricing["input"]
            # Estimate output tokens (usually less than max_tokens)
            estimated_output_tokens = min(self.max_tokens, 200)
            output_cost = (estimated_output_tokens / 1000) * model_pricing["output"]
            
            total_cost = input_cost + output_cost
            
            return {
                "estimated_input_tokens": int(total_input_tokens),
                "estimated_output_tokens": estimated_output_tokens,
                "estimated_cost_usd": round(total_cost, 6),
                "model": self.model_name
            }
            
        except Exception as e:
            return {"error": str(e)}