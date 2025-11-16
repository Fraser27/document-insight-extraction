"""
Text Chunking Module

This module provides functionality to split text into chunks with overlap
for optimal embedding generation and retrieval.
"""
import logging
from typing import List, Dict
import re
from decimal import Decimal
logger = logging.getLogger(__name__)


class TextChunker:
    """Split text into chunks with configurable size and overlap."""
    
    def __init__(self, chunk_size: int = 5000, chunk_overlap: int = 819):
        """
        Initialize text chunker.
        
        Args:
            chunk_size: Maximum number of tokens per chunk (default: 8192)
            chunk_overlap: Number of tokens to overlap between chunks (default: 819, ~10%)
        """
        self.logger = logging.getLogger(__name__)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Approximate tokens per character (rough estimate: 1 token ≈ 4 characters)
        self.chars_per_token = 4
        self.max_chars = chunk_size * self.chars_per_token
        self.overlap_chars = chunk_overlap * self.chars_per_token
    
    def chunk_text(
        self,
        text: str,
        page_range: str,
        doc_id: str
    ) -> List[Dict[str, any]]:
        """
        Split text into chunks with overlap and metadata.
        
        Args:
            text: Text to chunk
            page_range: Page range for this text (e.g., "1-10")
            doc_id: Document identifier
            
        Returns:
            List of chunk dictionaries:
            [
                {
                    "text": "chunk text...",
                    "metadata": {
                        "docId": "doc-id",
                        "pageRange": "1-10",
                        "chunkIndex": 0
                    }
                },
                ...
            ]
        """
        if not text or not text.strip():
            self.logger.warning("Empty text provided for chunking")
            return []
        
        # Use recursive character splitter
        chunks = self._recursive_split(text)
        
        # Add metadata to each chunk
        chunk_dicts = []
        for idx, chunk_text in enumerate(chunks):
            chunk_dicts.append({
                "text": chunk_text,
                "metadata": {
                    "docId": doc_id,
                    "pageRange": page_range,
                    "chunkIndex": idx
                }
            })
        
        print(
            f"Created {len(chunk_dicts)} chunks from {len(text)} characters "
            f"(page range: {page_range})"
        )
        
        return chunk_dicts
    
    def _recursive_split(self, text: str) -> List[str]:
        """
        Recursively split text using multiple separators.
        
        This implements a recursive character text splitter that tries to split
        on natural boundaries (paragraphs, sentences, words) before resorting
        to character-level splitting.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        # Separators in order of preference (try larger units first)
        separators = [
            "\n\n",  # Paragraph breaks
            "\n",    # Line breaks
            ". ",    # Sentence endings
            "! ",    # Exclamation sentences
            "? ",    # Question sentences
            "; ",    # Semicolons
            ", ",    # Commas
            " ",     # Words
            ""       # Characters (last resort)
        ]
        
        return self._split_text_recursive(text, separators)
    
    def _split_text_recursive(
        self,
        text: str,
        separators: List[str]
    ) -> List[str]:
        """
        Recursively split text using the provided separators.
        
        Args:
            text: Text to split
            separators: List of separators to try in order
            
        Returns:
            List of text chunks
        """
        chunks = []
        
        # Base case: if text is small enough, return it
        if len(text) <= self.max_chars:
            return [text] if text else []
        
        # Try each separator
        for separator in separators:
            if separator == "":
                # Last resort: split by characters
                return self._split_by_characters(text)
            
            # Check if separator exists in text
            if separator in text:
                # Split by this separator
                splits = text.split(separator)
                
                # Reconstruct chunks with overlap
                current_chunk = ""
                for split in splits:
                    # Add separator back (except for empty separator)
                    split_with_sep = split + separator if separator else split
                    
                    # Check if adding this split would exceed chunk size
                    if len(current_chunk) + len(split_with_sep) <= self.max_chars:
                        current_chunk += split_with_sep
                    else:
                        # Save current chunk if not empty
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        
                        # Start new chunk with overlap
                        if chunks and self.overlap_chars > 0:
                            # Get overlap from previous chunk
                            overlap_text = chunks[-1][-self.overlap_chars:]
                            current_chunk = overlap_text + split_with_sep
                        else:
                            current_chunk = split_with_sep
                        
                        # If single split is too large, recursively split it
                        if len(current_chunk) > self.max_chars:
                            # Recursively split with remaining separators
                            remaining_separators = separators[separators.index(separator) + 1:]
                            sub_chunks = self._split_text_recursive(
                                current_chunk,
                                remaining_separators
                            )
                            chunks.extend(sub_chunks[:-1])
                            current_chunk = sub_chunks[-1] if sub_chunks else ""
                
                # Add final chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                return chunks
        
        # Fallback: split by characters
        return self._split_by_characters(text)
    
    def _split_by_characters(self, text: str) -> List[str]:
        """
        Split text by characters as a last resort.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.max_chars
            chunk = text[start:end]
            chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.overlap_chars if self.overlap_chars > 0 else end
        
        return chunks
    
    def estimate_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in text.
        
        This is a rough approximation: 1 token ≈ 4 characters.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        return len(text) // self.chars_per_token
