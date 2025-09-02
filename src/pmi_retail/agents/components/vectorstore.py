"""
Vectorstore Component
Handles FAISS vectorstore creation and management with OpenAI embeddings
"""

import os
from typing import List, Optional, Dict, Any
import streamlit as st
from langchain.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document


class VectorStoreManager:
    """Manages FAISS vectorstore operations with OpenAI embeddings"""
    
    def __init__(self, 
                 model_name: str = "text-embedding-3-small", 
                 api_key: str = None):
        """
        Initialize VectorStore Manager
        
        Args:
            model_name: OpenAI embedding model name
            api_key: OpenAI API key (if None, uses environment variable)
        """
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.embeddings = None
        self.vectorstore = None
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Initialize OpenAI embeddings"""
        try:
            if not self.api_key:
                st.error("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
                return
            
            self.embeddings = OpenAIEmbeddings(
                model=self.model_name,
                openai_api_key=self.api_key
            )
            
            # Test the embedding to ensure it works
            test_result = self.embeddings.embed_query("test")
            if test_result:
                st.success(f"OpenAI embeddings initialized with model: {self.model_name}")
        except Exception as e:
            st.error(f"Error initializing OpenAI embeddings: {str(e)}")
            st.error("Please check your OpenAI API key and internet connection")
            self.embeddings = None
    
    def create_vectorstore(self, documents: List[Document]) -> Optional[FAISS]:
        """
        Create FAISS vectorstore from documents
        
        Args:
            documents: List of Document objects to vectorize
            
        Returns:
            FAISS vectorstore or None if error
        """
        if not self.embeddings:
            st.error("OpenAI embeddings not initialized. Cannot create vectorstore.")
            return None
        
        if not documents:
            st.error("No documents provided for vectorstore creation")
            return None
        
        try:
            # Create FAISS vectorstore
            with st.spinner(f"Creating embeddings for {len(documents)} documents..."):
                self.vectorstore = FAISS.from_documents(
                    documents=documents,
                    embedding=self.embeddings
                )
            
            st.success(f"Vectorstore created with {len(documents)} documents")
            return self.vectorstore
            
        except Exception as e:
            st.error(f"Error creating vectorstore: {str(e)}")
            if "rate limit" in str(e).lower():
                st.error("OpenAI API rate limit exceeded. Please wait and try again.")
            elif "quota" in str(e).lower():
                st.error("OpenAI API quota exceeded. Please check your usage.")
            return None
    
    def add_documents(self, documents: List[Document]) -> bool:
        """
        Add documents to existing vectorstore
        
        Args:
            documents: List of Document objects to add
            
        Returns:
            True if successful, False otherwise
        """
        if not self.vectorstore:
            st.error("No vectorstore exists. Create one first.")
            return False
        
        try:
            with st.spinner(f"Adding {len(documents)} documents to vectorstore..."):
                self.vectorstore.add_documents(documents)
            st.success(f"Added {len(documents)} documents to vectorstore")
            return True
            
        except Exception as e:
            st.error(f"Error adding documents: {str(e)}")
            return False
    
    def similarity_search(self, 
                         query: str, 
                         k: int = 4, 
                         score_threshold: float = None) -> List[Document]:
        """
        Perform similarity search
        
        Args:
            query: Search query
            k: Number of documents to return
            score_threshold: Minimum similarity score
            
        Returns:
            List of relevant documents
        """
        if not self.vectorstore:
            st.error("No vectorstore available for search")
            return []
        
        try:
            if score_threshold:
                # Search with score threshold
                docs_with_scores = self.vectorstore.similarity_search_with_score(
                    query, k=k
                )
                docs = [doc for doc, score in docs_with_scores if score >= score_threshold]
            else:
                # Regular similarity search
                docs = self.vectorstore.similarity_search(query, k=k)
            
            return docs
            
        except Exception as e:
            st.error(f"Error during similarity search: {str(e)}")
            return []
    
    def similarity_search_with_scores(self, 
                                    query: str, 
                                    k: int = 4) -> List[tuple]:
        """
        Perform similarity search with scores
        
        Args:
            query: Search query
            k: Number of documents to return
            
        Returns:
            List of (document, score) tuples
        """
        if not self.vectorstore:
            st.error("No vectorstore available for search")
            return []
        
        try:
            docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=k)
            return docs_with_scores
            
        except Exception as e:
            st.error(f"Error during similarity search with scores: {str(e)}")
            return []
    
    def get_retriever(self, 
                     search_type: str = "similarity", 
                     search_kwargs: Dict[str, Any] = None):
        """
        Get retriever for the vectorstore
        
        Args:
            search_type: Type of search ("similarity", "mmr", etc.)
            search_kwargs: Additional search parameters
            
        Returns:
            Retriever object or None if error
        """
        if not self.vectorstore:
            st.error("No vectorstore available")
            return None
        
        try:
            search_kwargs = search_kwargs or {"k": 4}
            retriever = self.vectorstore.as_retriever(
                search_type=search_type,
                search_kwargs=search_kwargs
            )
            return retriever
            
        except Exception as e:
            st.error(f"Error creating retriever: {str(e)}")
            return None
    
    def save_vectorstore(self, file_path: str) -> bool:
        """
        Save vectorstore to disk
        
        Args:
            file_path: Path to save the vectorstore
            
        Returns:
            True if successful, False otherwise
        """
        if not self.vectorstore:
            st.error("No vectorstore to save")
            return False
        
        try:
            self.vectorstore.save_local(file_path)
            st.success(f"Vectorstore saved to {file_path}")
            return True
            
        except Exception as e:
            st.error(f"Error saving vectorstore: {str(e)}")
            return False
    
    def load_vectorstore(self, file_path: str) -> bool:
        """
        Load vectorstore from disk
        
        Args:
            file_path: Path to load the vectorstore from
            
        Returns:
            True if successful, False otherwise
        """
        if not self.embeddings:
            st.error("OpenAI embeddings not initialized")
            return False
        
        try:
            self.vectorstore = FAISS.load_local(
                file_path, 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            st.success(f"Vectorstore loaded from {file_path}")
            return True
            
        except Exception as e:
            st.error(f"Error loading vectorstore: {str(e)}")
            return False
    
    def get_vectorstore_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current vectorstore
        
        Returns:
            Dictionary with vectorstore statistics
        """
        if not self.vectorstore:
            return {"status": "No vectorstore available"}
        
        try:
            # Get the number of vectors
            index = self.vectorstore.index
            num_vectors = index.ntotal if hasattr(index, 'ntotal') else "Unknown"
            
            # Get embedding dimension
            embedding_dim = "Unknown"
            if self.embeddings:
                try:
                    test_embedding = self.embeddings.embed_query("test")
                    embedding_dim = len(test_embedding)
                except:
                    pass
            
            return {
                "status": "Active",
                "model_name": self.model_name,
                "num_vectors": num_vectors,
                "embedding_dimension": embedding_dim,
                "api_key_set": bool(self.api_key)
            }
            
        except Exception as e:
            return {"status": f"Error getting stats: {str(e)}"}
    
    def change_model(self, new_model_name: str) -> bool:
        """
        Change the embedding model (requires recreating vectorstore)
        
        Args:
            new_model_name: New OpenAI model name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.model_name = new_model_name
            self._initialize_embeddings()
            
            if self.embeddings:
                # Note: Existing vectorstore becomes incompatible
                self.vectorstore = None
                st.warning("Model changed. Please recreate vectorstore with new model.")
                return True
            return False
            
        except Exception as e:
            st.error(f"Error changing model: {str(e)}")
            return False
    
    def estimate_cost(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Estimate the cost for embedding documents
        
        Args:
            documents: List of documents to estimate cost for
            
        Returns:
            Dictionary with cost estimation
        """
        if not documents:
            return {"error": "No documents provided"}
        
        try:
            # Calculate total tokens (approximate)
            total_text = " ".join([doc.page_content for doc in documents])
            
            # Rough estimation: 1 token ≈ 4 characters
            estimated_tokens = len(total_text) / 4
            
            # OpenAI embedding pricing (as of 2024)
            pricing = {
                "text-embedding-3-small": 0.00002 / 1000,  # $0.00002 per 1K tokens
                "text-embedding-3-large": 0.00013 / 1000,  # $0.00013 per 1K tokens
                "text-embedding-ada-002": 0.0001 / 1000,   # $0.0001 per 1K tokens
            }
            
            cost_per_token = pricing.get(self.model_name, pricing["text-embedding-3-small"])
            estimated_cost = estimated_tokens * cost_per_token
            
            return {
                "estimated_tokens": int(estimated_tokens),
                "estimated_cost_usd": round(estimated_cost, 6),
                "model": self.model_name,
                "num_documents": len(documents)
            }
            
        except Exception as e:
            return {"error": str(e)}