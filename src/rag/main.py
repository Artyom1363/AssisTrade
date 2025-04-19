"""
This module serves as the main entry point for the documentation RAG system.
It handles query processing, embedding generation, document retrieval, and interaction
with external APIs to generate responses.
"""

import os
import json
import logging
import argparse
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from langchain_gigachat.chat_models import GigaChat
from langchain.schema import HumanMessage, SystemMessage
import requests
from fastapi import FastAPI, HTTPException, Body, Query, Depends
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np

# Import from other modules (assuming they're installed as packages or in PYTHONPATH)
from src import ChromaDBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL_NAME = "cointegrated/rubert-tiny2"  # Russian BERT model

# Initialize FastAPI app
app = FastAPI(title="Documentation RAG API")

# Pydantic models
class QueryRequest(BaseModel):
    query: str
    max_results: int = 3
    temperature: float = 0.7

class QueryResponse(BaseModel):
    answer: str
    relevant_chunks: List[str]
    images: List[Dict[str, str]]

class AppConfig(BaseModel):
    vector_data_dir: str
    persist_dir: str
    collection_name: str
    data_dir: str
    model_name: str = DEFAULT_MODEL_NAME
    api_key: Optional[str] = None

load_dotenv()

def get_app_config():
    """Get application configuration."""
    return app.state.config


class DocumentationRAG:
    def __init__(self, config: AppConfig):
        """
        Initialize the Documentation RAG system.
        
        Args:
            config: Application configuration
        """
        self.config = config
        
        self.llm = GigaChat(
            credentials=config.api_key,
            model='GigaChat',
            verify_ssl_certs=False
        )
        # Load embedding model
        logger.info(f"Loading embedding model: {config.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(config.model_name)
        self.model = AutoModel.from_pretrained(config.model_name)
        self.model.eval()
        # Initialize ChromaDB
        self.db_manager = ChromaDBManager(
            vector_data_dir=config.vector_data_dir,
            persist_dir=config.persist_dir,
            collection_name=config.collection_name
        )
        
        # Load image path mapping
        self.image_base_dir = os.path.join(config.data_dir, "images")
        
        logger.info("Documentation RAG system initialized")
    
    def create_query_embedding(self, query: str) -> List[float]:
        """
        Create embedding for a query using the embedding model.
        
        Args:
            query: Query text
            
        Returns:
            Embedding vector as a list of floats
        """
        # Tokenize and get model output
        inputs = self.tokenizer(query, return_tensors='pt', padding=True, truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Use CLS token embedding as the representation
        embeddings = outputs.last_hidden_state[:, 0, :].numpy()
        return embeddings[0].tolist()
    
    def query_vector_db(self, query: str, n_results: int = 3) -> Dict[str, Any]:
        """
        Query the vector database for documents similar to the query.
        
        Args:
            query: Query text
            n_results: Number of results to return
            
        Returns:
            Dictionary with query results
        """
        # Create query embedding
        query_embedding = self.create_query_embedding(query)
        
        # Query ChromaDB
        results = self.db_manager.query_similar(query_embedding, n_results)
        
        return results
    
    def generate_response(self, query: str, context: List[str], images: List[Dict[str, str]], 
                           temperature: float = 0.7) -> str:
        """
        Generate response using API with retrieved context.
        
        Args:
            query: Original user query
            context: List of relevant text chunks
            images: List of relevant images
            temperature: Temperature for API response generation
            
        Returns:
            Generated response text
        """
        # Prepare context for the API
        context_text = "\n\n".join(context)
        
        # Add image references to the context if present
        if images:
            image_references = "\n\nRelevant images:\n"
            for i, img in enumerate(images):
                image_references += f"[Image {i+1}]: {img['title']}\n"
            context_text += image_references
        
        # Prepare the prompt
        prompt = f"""
        You are an assistant helping with documentation questions.
        Base your answer on the following information:
        
        {context_text}
        
        User question: {query}
        
        Provide a concise, clear answer. If the information doesn't fully answer the question, 
        acknowledge the limitations. If mentioning images, refer to them as [Image X].
        """

        messages = [
            SystemMessage(content=(
                """
                Ты - специализированный ассистент по MetaMask, который отвечает на вопросы пользователей на русском языке. 
                Ты получаешь вопрос пользователя и релевантные фрагменты из документации MetaMask на английском языке. 
                Твоя задача - предоставить точный, полезный и понятный ответ на русском языке, основываясь на предоставленных фрагментах документации.
                """
            )),
            HumanMessage(content=prompt)
        ]
        try:

            response = self.llm(messages)
            return response.content
        except Exception as e:
            logger.error(f"Error in API request: {e}")
            
            # Fallback simple response if API fails
            return self._generate_fallback_response(query, context, images)
    
    def _generate_fallback_response(self, query: str, context: List[str], images: List[Dict[str, str]]) -> str:
        """
        Generate a simple fallback response when API is not available.
        
        Args:
            query: User query
            context: Retrieved context chunks
            images: Retrieved images
            
        Returns:
            Simple generated response
        """
        # Create a simple response from the retrieved information
        response_parts = [
            f"Based on the documentation, here's information about your question on '{query}':",
            "\n\n"
        ]
        
        # Add snippets from each context chunk
        for i, chunk in enumerate(context):
            # Take first 150 characters of each chunk
            snippet = chunk[:150] + "..." if len(chunk) > 150 else chunk
            response_parts.append(f"Information {i+1}: {snippet}\n")
        
        # Add image references
        if images:
            response_parts.append("\nRelevant images found in the documentation:\n")
            for i, img in enumerate(images):
                response_parts.append(f"[Image {i+1}]: {img['title']}\n")
        
        return "".join(response_parts)
    
    def process_query(self, query: str, max_results: int = 3, temperature: float = 0.7) -> Dict[str, Any]:
        """
        Process a user query and generate a response.
        
        Args:
            query: User query text
            max_results: Maximum number of relevant chunks to retrieve
            temperature: Temperature for response generation
            
        Returns:
            Dictionary with answer, relevant chunks, and images
        """
        # 1. Query vector DB to find relevant chunks
        db_results = self.query_vector_db(query, max_results)
        if not db_results["chunks"]["ids"][0]:
            return {
                "answer": "I couldn't find relevant information in the documentation. Please try rephrasing your question.",
                "relevant_chunks": [],
                "images": []
            }
        
        # 2. Extract relevant chunks and images
        chunks = db_results["chunks"]["documents"][0]
        images = db_results["images"]
        
        # 3. Generate response
        answer = self.generate_response(query, chunks, images, temperature)
        
        # 4. Process image paths to make them accessible
        processed_images = []
        for img in images:
            processed_images.append({
                "path": img["path"],
                "title": img["title"]
            })
        
        # 5. Format the response
        response = {
            "answer": answer,
            "relevant_chunks": chunks,
            "images": processed_images
        }
        
        return response


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(
    request: QueryRequest,
    config: AppConfig = Depends(get_app_config)
):
    """
    Endpoint to query the RAG system.
    
    Args:
        request: Query request with query text and parameters
        
    Returns:
        JSON response with answer, relevant chunks, and images
    """
    try:
        rag_system = DocumentationRAG(config)
        result = rag_system.process_query(
            query=request.query,
            max_results=request.max_results,
            temperature=request.temperature
        )
        return result
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.get("/health")
async def health_check(config: AppConfig = Depends(get_app_config)):
    """Health check endpoint."""
    try:
        db_manager = ChromaDBManager(
            vector_data_dir=config.vector_data_dir,
            persist_dir=config.persist_dir,
            collection_name=config.collection_name
        )
        item_count = db_manager.count_items()
        return {"status": "healthy", "vector_db_items": item_count}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/info")
async def api_info(config: AppConfig = Depends(get_app_config)):
    """Return information about the API configuration."""
    return {
        "collection_name": config.collection_name,
        "embedding_model": config.model_name
    }


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run Documentation RAG API server")
    parser.add_argument("--vector-data-dir", required=True, help="Directory with vector data")
    parser.add_argument("--persist-dir", required=True, help="Directory to persist ChromaDB")
    parser.add_argument("--collection-name", default="documentation", help="Name of ChromaDB collection")
    parser.add_argument("--data-dir", required=True, help="Directory with original data")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME, help="Name of embedding model")
    parser.add_argument("--api-key", help="API key for external LLM service")
    parser.add_argument("--host", default="0.0.0.0", help="Host to run API server on")
    parser.add_argument("--port", type=int, default=8000, help="Port to run API server on")
    return parser.parse_args()


def setup_app(args):
    """Set up FastAPI application with configuration."""
    api_key = os.getenv('GIGACHAT_API_KEY')
    model_name = os.getenv('GIGACHAT_MODEL_NAME')
    config = AppConfig(
        vector_data_dir=args.vector_data_dir,
        persist_dir=args.persist_dir,
        collection_name=args.collection_name,
        data_dir=args.data_dir,
        api_key=api_key
    )
    
    app.state.config = config
    logger.info(f"Application configured with collection: {config.collection_name}")
    
    return app


if __name__ == "__main__":
    import uvicorn
    
    args = parse_args()
    app = setup_app(args)
    
    # Run FastAPI app
    logger.info(f"Starting API server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)