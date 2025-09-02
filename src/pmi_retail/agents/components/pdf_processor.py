"""
PDF Processing Component
Handles PDF loading and text chunking operations
"""

import tempfile
import os
from pathlib import Path
from typing import List, Optional
import streamlit as st
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document


class PDFProcessor:
    """Handles PDF loading and text processing operations"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize PDF processor with chunking parameters
        
        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def load_pdf_from_upload(self, uploaded_file) -> Optional[List[Document]]:
        """
        Load PDF from Streamlit uploaded file
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            List of Document objects or None if error
        """
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            # Load PDF using PyPDFLoader
            loader = PyPDFLoader(tmp_file_path)
            documents = loader.load()
            
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
            return documents
            
        except Exception as e:
            st.error(f"Error loading PDF: {str(e)}")
            return None
    
    def load_pdf_from_path(self, file_path: str) -> Optional[List[Document]]:
        """
        Load PDF from file path
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of Document objects or None if error
        """
        try:
            if not Path(file_path).exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            
            return documents
            
        except Exception as e:
            st.error(f"Error loading PDF from path: {str(e)}")
            return None
    
    def split_documents(self, documents: List[Document]) -> Optional[List[Document]]:
        """
        Split documents into chunks
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of chunked Document objects or None if error
        """
        try:
            chunks = self.text_splitter.split_documents(documents)
            return chunks
            
        except Exception as e:
            st.error(f"Error splitting documents: {str(e)}")
            return None
    
    def process_pdf_upload(self, uploaded_file) -> Optional[List[Document]]:
        """
        Complete PDF processing pipeline for uploaded files
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            List of chunked Document objects or None if error
        """
        # Load PDF
        documents = self.load_pdf_from_upload(uploaded_file)
        if not documents:
            return None
        
        # Split into chunks
        chunks = self.split_documents(documents)
        if not chunks:
            return None
        
        return chunks
    
    def process_pdf_path(self, file_path: str) -> Optional[List[Document]]:
        """
        Complete PDF processing pipeline for file paths
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of chunked Document objects or None if error
        """
        # Load PDF
        documents = self.load_pdf_from_path(file_path)
        if not documents:
            return None
        
        # Split into chunks
        chunks = self.split_documents(documents)
        if not chunks:
            return None
        
        return chunks
    
    def get_document_stats(self, documents: List[Document]) -> dict:
        """
        Get statistics about processed documents
        
        Args:
            documents: List of Document objects
            
        Returns:
            Dictionary with document statistics
        """
        if not documents:
            return {}
        
        total_chars = sum(len(doc.page_content) for doc in documents)
        total_words = sum(len(doc.page_content.split()) for doc in documents)
        
        return {
            "total_chunks": len(documents),
            "total_characters": total_chars,
            "total_words": total_words,
            "avg_chunk_size": total_chars // len(documents) if documents else 0,
            "chunk_size_setting": self.chunk_size,
            "chunk_overlap_setting": self.chunk_overlap
        }
    
    def update_chunk_settings(self, chunk_size: int, chunk_overlap: int):
        """
        Update chunking parameters
        
        Args:
            chunk_size: New chunk size
            chunk_overlap: New chunk overlap
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )