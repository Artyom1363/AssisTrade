import os
import json
import logging
import argparse
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChromaDBManager:
    def __init__(self, 
                 vector_data_dir: str,
                 persist_dir: str,
                 collection_name: str = "documentation"):
        """
        Initialize ChromaDB manager.
        
        Args:
            vector_data_dir: Directory containing the vector database data
            persist_dir: Directory to persist ChromaDB data
            collection_name: Name of the ChromaDB collection
        """
        self.vector_data_dir = vector_data_dir
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        
        # Create persistence directory if it doesn't exist
        if not os.path.exists(persist_dir):
            os.makedirs(persist_dir)
            
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_dir)
        logger.info(f"ChromaDB client initialized with persistence at {persist_dir}")
        
        # Image mapping for retrieving images related to chunks
        self.image_mapping = self._load_image_mapping()
    
    def _load_image_mapping(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Load image mapping from JSON file.
        
        Returns:
            Dictionary mapping chunk IDs to image information
        """
        image_mapping_file = os.path.join(self.vector_data_dir, "image_mapping.json")
        
        if not os.path.exists(image_mapping_file):
            logger.warning(f"Image mapping file not found: {image_mapping_file}")
            return {}
        
        try:
            with open(image_mapping_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading image mapping: {e}")
            return {}
    
    def _load_chroma_data(self) -> Dict[str, Any]:
        """
        Load ChromaDB data from JSON file.
        
        Returns:
            Dictionary with ChromaDB data
        """
        chroma_data_file = os.path.join(self.vector_data_dir, "chroma_data.json")
        
        if not os.path.exists(chroma_data_file):
            raise FileNotFoundError(f"ChromaDB data file not found: {chroma_data_file}")
        
        try:
            with open(chroma_data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading ChromaDB data: {e}")
            raise
    
    def get_collection(self) -> chromadb.Collection:
        """
        Get the ChromaDB collection. Creates it if it doesn't exist.
        
        Returns:
            ChromaDB collection
        """
        try:
            return self.client.get_collection(name=self.collection_name)
        except ValueError:
            logger.warning(f"Collection {self.collection_name} not found, setting up...")
            return self.setup_collection()
        except Exception as e:
            logger.warning(f"Unexpected error when getting collection: {str(e)}")
            return self.setup_collection()

    def setup_collection(self, recreate: bool = False) -> chromadb.Collection:
        """
        Set up ChromaDB collection with data from preprocessing job.
        
        Args:
            recreate: Whether to recreate the collection if it already exists
            
        Returns:
            ChromaDB collection
        """
        # Check if collection already exists
        try:
            collection = self.client.get_collection(name=self.collection_name)
            
            if recreate:
                logger.info(f"Recreating collection: {self.collection_name}")
                try:
                    self.client.delete_collection(name=self.collection_name)
                    collection = self.client.create_collection(name=self.collection_name)
                except Exception as e:
                    logger.error(f"Error deleting and recreating collection: {e}")
                    # Try to use existing collection if deletion fails
                    collection = self.client.get_collection(name=self.collection_name)
            else:
                logger.info(f"Collection already exists: {self.collection_name}")
                return collection
                    
        except ValueError:
            # Collection doesn't exist, create it
            logger.info(f"Collection {self.collection_name} doesn't exist, creating...")
            try:
                collection = self.client.create_collection(name=self.collection_name)
            except Exception as e:
                logger.error(f"Error creating collection: {e}")
                raise RuntimeError(f"Failed to create collection: {e}")
        except Exception as e:
            logger.error(f"Unexpected error when checking collection: {e}")
            try:
                # Try to create collection anyway
                logger.info(f"Attempting to create collection {self.collection_name} after error")
                collection = self.client.create_collection(name=self.collection_name)
            except Exception as inner_e:
                logger.error(f"Error creating collection after prior error: {inner_e}")
                raise RuntimeError(f"Failed to create collection: {inner_e}")
        
        # Load data
        try:
            chroma_data = self._load_chroma_data()
            
            if not chroma_data or not chroma_data.get("ids"):
                logger.warning("No data available to populate ChromaDB")
                return collection
            
            # Add data to collection
            logger.info(f"Adding {len(chroma_data['ids'])} items to collection")
            
            # Add in batches to prevent memory issues
            batch_size = 100
            total_items = len(chroma_data["ids"])
            
            for i in range(0, total_items, batch_size):
                end_idx = min(i + batch_size, total_items)
                
                batch_ids = chroma_data["ids"][i:end_idx]
                batch_embeddings = chroma_data["embeddings"][i:end_idx]
                batch_metadatas = chroma_data["metadatas"][i:end_idx]
                batch_documents = chroma_data["documents"][i:end_idx]
                
                try:
                    collection.add(
                        ids=batch_ids,
                        embeddings=batch_embeddings,
                        metadatas=batch_metadatas,
                        documents=batch_documents
                    )
                    
                    logger.info(f"Added batch {i//batch_size + 1}/{(total_items-1)//batch_size + 1} to ChromaDB")
                except Exception as e:
                    logger.error(f"Error adding batch to collection: {e}")
                    # Continue with next batch
            
            logger.info(f"Collection setup complete with {total_items} items")
        except FileNotFoundError:
            logger.warning(f"No data file found, creating empty collection {self.collection_name}")
        except Exception as e:
            logger.error(f"Error setting up collection data: {e}")
            logger.warning("Continuing with empty collection")
        
        return collection
    
    def query_similar(self, query_embedding: List[float], n_results: int = 3) -> Dict[str, Any]:
        """
        Query the vector database for similar chunks.
        
        Args:
            query_embedding: Embedding vector for the query
            n_results: Number of results to return
            
        Returns:
            Dictionary with query results and related images
        """
        print('before collection')
        collection = self.get_collection()
        print('collection created')
        
        # Query the collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        # Extract chunk IDs from results
        chunk_ids = results["ids"][0]  # First (and only) query result
        
        # Find images related to the returned chunks
        related_images = []
        for chunk_id in chunk_ids:
            if chunk_id in self.image_mapping:
                related_images.extend(self.image_mapping[chunk_id])
        
        # Combine results with image information
        return {
            "chunks": results,
            "images": related_images
        }
    
    def count_items(self) -> int:
        """
        Count the number of items in the collection.
        
        Returns:
            Number of items in the collection
        """
        collection = self.get_collection()
        return collection.count()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Set up and manage ChromaDB for RAG system")
    parser.add_argument("--vector-data-dir", required=True, help="Directory with vector data")
    parser.add_argument("--persist-dir", required=True, help="Directory to persist ChromaDB")
    parser.add_argument("--collection-name", default="documentation", help="Name of ChromaDB collection")
    parser.add_argument("--recreate", action="store_true", help="Recreate collection if it exists")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    db_manager = ChromaDBManager(
        vector_data_dir=args.vector_data_dir,
        persist_dir=args.persist_dir,
        collection_name=args.collection_name
    )
    
    # Setup collection
    collection = db_manager.setup_collection(recreate=args.recreate)
    
    # Get item count
    count = db_manager.count_items()
    print(f"Collection '{args.collection_name}' contains {count} items")