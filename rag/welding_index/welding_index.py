"""
Generic Data Preprocessing Job

This script processes documentation data using LangChain's RecursiveCharacterTextSplitter
for intelligent chunking that preserves context and semantic boundaries.
It can be applied to any documentation source, not just MetaMask.
"""

import os
import json
import re
import logging
import argparse
from typing import List, Dict, Any, Tuple
import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np
from tqdm import tqdm
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_MODEL_NAME = "cointegrated/rubert-tiny2"  # Russian BERT model

class DocumentationPreprocessor:
    def __init__(self, 
                 data_dir: str,
                 output_dir: str,
                 model_name: str = DEFAULT_MODEL_NAME,
                 chunk_size: int = DEFAULT_CHUNK_SIZE,
                 chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
        """
        Initialize the generic documentation preprocessor.
        
        Args:
            data_dir: Directory containing the scraped data
            output_dir: Directory to save processed data for ChromaDB
            model_name: Name of the embedding model to use
            chunk_size: Size of text chunks in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.articles_dir = os.path.join(data_dir, "articles")
        self.images_dir = os.path.join(data_dir, "images")
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Initialize embedding model
        logger.info(f"Loading embedding model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.eval()
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""]
        )
    
    def load_articles(self) -> List[Dict[str, Any]]:
        """
        Load all article JSON files from the articles directory.
        
        Returns:
            List of article dictionaries
        """
        articles = []
        
        if not os.path.exists(self.articles_dir):
            logger.error(f"Articles directory not found: {self.articles_dir}")
            return articles
            
        article_files = [f for f in os.listdir(self.articles_dir) if f.endswith('.json')]
        
        logger.info(f"Found {len(article_files)} article files")
        
        for file_name in article_files:
            try:
                with open(os.path.join(self.articles_dir, file_name), 'r', encoding='utf-8') as f:
                    article = json.load(f)
                    articles.append(article)
            except Exception as e:
                logger.error(f"Error loading article file {file_name}: {e}")
        
        return articles
    
    def preprocess_text_for_splitting(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Preprocess text before splitting to preserve image markers.
        
        Args:
            text: The text to preprocess
            
        Returns:
            Tuple of (preprocessed text, placeholder mapping)
        """
        # Find all image markers in the text
        image_markers = re.findall(r'\[\[IMAGE:[^\]]+\]\]', text)
        
        # Replace image markers with placeholders to avoid splitting them
        placeholder_map = {}
        for i, marker in enumerate(image_markers):
            placeholder = f"__IMAGE_MARKER_{i}__"
            placeholder_map[placeholder] = marker
            text = text.replace(marker, placeholder)
        
        return text, placeholder_map
    
    def restore_placeholders(self, text: str, placeholder_map: Dict[str, str]) -> str:
        """
        Restore image markers from placeholders.
        
        Args:
            text: The text with placeholders
            placeholder_map: Mapping from placeholders to original markers
            
        Returns:
            Text with restored markers
        """
        for placeholder, marker in placeholder_map.items():
            text = text.replace(placeholder, marker)
        return text
    
    def split_into_chunks(self, text: str) -> List[str]:
        """
        Split text into chunks using LangChain's text splitter.
        
        Args:
            text: The text to split
            
        Returns:
            List of text chunks
        """
        # Preprocess text to preserve image markers
        preprocessed_text, placeholder_map = self.preprocess_text_for_splitting(text)
        
        # Split the text
        chunks = self.text_splitter.split_text(preprocessed_text)
        logger.debug(f"Split into {len(chunks)} chunks")
        
        # Restore image markers in chunks
        restored_chunks = [self.restore_placeholders(chunk, placeholder_map) for chunk in chunks]
        
        return restored_chunks
    
    def process_chunk_images(self, chunk: str, article_id: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        Process image markers in a chunk.
        
        Args:
            chunk: Text chunk with image markers
            article_id: ID of the article
            
        Returns:
            Tuple of (processed text, list of image info dictionaries)
        """
        # Find all image markers in the format [[IMAGE:path|title]]
        marker_pattern = r'\[\[IMAGE:([^|]+)\|([^\]]+)\]\]'
        image_markers = re.findall(marker_pattern, chunk)
        
        images = []
        for img_path, img_title in image_markers:
            images.append({
                "path": img_path,
                "title": img_title,
                "article_id": article_id
            })
        
        # Replace markers with standardized format for ChromaDB
        processed_chunk = re.sub(
            marker_pattern,
            r'[IMAGE: \2]',  # Replace with [IMAGE: title]
            chunk
        )
        
        return processed_chunk, images
    
    def create_embedding(self, text: str) -> List[float]:
        """
        Create embedding for a text using the specified model.
        
        Args:
            text: Text to create embedding for
            
        Returns:
            Embedding vector as a list of floats
        """
        # Tokenize and get model output
        inputs = self.tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Use CLS token embedding as the representation
        embeddings = outputs.last_hidden_state[:, 0, :].numpy()
        return embeddings[0].tolist()
    
    def process_articles(self):
        """
        Process all articles, create chunks and embeddings.
        """
        articles = self.load_articles()
        logger.info(f"Processing {len(articles)} articles")
        
        # Prepare data structure for ChromaDB
        chroma_data = {
            "ids": [],
            "embeddings": [],
            "metadatas": [],
            "documents": []
        }
        
        image_mapping = {}
        
        for article in tqdm(articles, desc="Processing articles"):
            article_id = article["id"]
            article_title = article["title"]
            article_text = article["content_text"]
            
            # Split article into chunks
            chunks = self.split_into_chunks(article_text)
            logger.info(f"Article '{article_title}' split into {len(chunks)} chunks")
            
            # Process each chunk
            for chunk_idx, chunk in enumerate(chunks):
                # Process image markers
                processed_chunk, images = self.process_chunk_images(chunk, article_id)
                
                # Create unique ID for the chunk
                chunk_id = f"{article_id}_chunk_{chunk_idx}"
                
                # Create embedding
                embedding = self.create_embedding(processed_chunk)
                
                # Add to ChromaDB data
                chroma_data["ids"].append(chunk_id)
                chroma_data["embeddings"].append(embedding)
                chroma_data["metadatas"].append({
                    "article_id": article_id,
                    "article_title": article_title,
                    "chunk_index": chunk_idx,
                    "has_images": len(images) > 0
                })
                chroma_data["documents"].append(processed_chunk)
                
                # Store image information
                if images:
                    image_mapping[chunk_id] = images
        
        # Save ChromaDB data
        output_file = os.path.join(self.output_dir, "chroma_data.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chroma_data, f, ensure_ascii=False, indent=2)
        
        # Save image mapping
        image_mapping_file = os.path.join(self.output_dir, "image_mapping.json")
        with open(image_mapping_file, 'w', encoding='utf-8') as f:
            json.dump(image_mapping, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Processed {len(chroma_data['ids'])} chunks with embeddings")
        logger.info(f"Data saved to {output_file} and {image_mapping_file}")
    
    def run(self):
        """Main execution method."""
        logger.info(f"Starting documentation processing for vector DB. Data dir: {self.data_dir}")
        self.process_articles()
        logger.info("Data processing completed")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Process documentation data for RAG system")
    parser.add_argument("--data-dir", required=True, help="Directory containing scraped data")
    parser.add_argument("--output-dir", required=True, help="Directory to save processed data")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="Name of the embedding model")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, 
                        help="Size of text chunks in characters")
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP, 
                        help="Overlap between chunks in characters")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    processor = DocumentationPreprocessor(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        model_name=args.model,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    
    processor.run()