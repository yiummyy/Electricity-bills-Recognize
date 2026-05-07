import json
import logging
import time
import os
# Set HF Mirror environment variable BEFORE importing sentence_transformers
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from typing import List, Dict, Any, Optional
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer, CrossEncoder
from app.core.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class RecursiveCharacterTextSplitter:
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += self.chunk_size - self.chunk_overlap
            
        return chunks

class EmbeddingService:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
            
        self.embedding_model_path = settings.EMBEDDING_MODEL_PATH
        self.rerank_model_path = settings.RERANK_MODEL_PATH
        self.index_path = "vector_index.faiss"
        self.meta_path = "vector_meta.pkl"
        
        self.embedding_model = None
        self.rerank_model = None
        self.vector_index = None
        self.documents = []  # List[Dict]
        self.bm25 = None
        self.dimension = 0
        
        # Load default models
        self._load_embedding_model(self.embedding_model_path)
        self._load_rerank_model(self.rerank_model_path)
        
        # Load index from disk if exists
        self._load_index_from_disk()
        
        self.initialized = True

    def _load_embedding_model(self, path: str):
        try:
            logger.info(f"Loading embedding model from {path}...")
            if os.path.exists(path):
                self.embedding_model = SentenceTransformer(path)
            else:
                logger.warning(f"Local model path {path} not found. Trying to download/load 'BAAI/bge-small-zh-v1.5' from Mirror...")
                self.embedding_model = SentenceTransformer('BAAI/bge-small-zh-v1.5')

            self.dimension = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"Embedding model loaded. Dimension: {self.dimension}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}. Embedding features will be unavailable.")
            self.embedding_model = None
            self.dimension = 0

    def _load_rerank_model(self, path: str):
        try:
            if path:
                logger.info(f"Loading rerank model from {path}...")
                if os.path.exists(path):
                    self.rerank_model = CrossEncoder(path)
                else:
                    # Optional: load default if configured path invalid
                    logger.warning(f"Rerank model path {path} invalid.")
            else:
                logger.info("No rerank model configured.")
        except Exception as e:
            logger.error(f"Failed to load rerank model: {e}")

    def switch_model(self, model_path: str):
        """
        Switch embedding model at runtime.
        """
        try:
            logger.info(f"Switching embedding model to {model_path}...")
            self._load_embedding_model(model_path)
            # Re-initialize index since dimension might change
            self._init_index()
            # Clear documents as they need re-embedding
            self.documents = []
            logger.info("Embedding model switched successfully. Index cleared.")
        except Exception as e:
            logger.error(f"Failed to switch model: {e}")
            raise

    def _load_index_from_disk(self):
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            try:
                self.vector_index = faiss.read_index(self.index_path)
                with open(self.meta_path, 'rb') as f:
                    import pickle
                    self.documents = pickle.load(f)
                logger.info(f"Loaded index from disk. {self.vector_index.ntotal} vectors.")
            except Exception as e:
                logger.error(f"Failed to load index: {e}")
                self._init_index()
        else:
            self._init_index()

    def _init_index(self):
        # Create a new FAISS index (FlatL2 or HNSW)
        if self.dimension > 0:
            self.vector_index = faiss.IndexFlatL2(self.dimension)
            logger.info("Initialized new FAISS index.")

    def add_documents(self, texts: List[str], metadatas: List[Dict] = None):
        if not texts:
            return

        if self.embedding_model is None:
            logger.error("Embedding model not loaded. Cannot add documents.")
            return

        if metadatas is None:
            metadatas = [{} for _ in texts]
            
        # Generate embeddings
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        
        # Add to FAISS
        self.vector_index.add(embeddings)
        
        # Store metadata
        for i, text in enumerate(texts):
            doc = {
                "text": text,
                "metadata": metadatas[i]
            }
            self.documents.append(doc)
            
        logger.info(f"Added {len(texts)} documents to index. Total: {self.vector_index.ntotal}")
        
        # Persist? (Optional, maybe on shutdown or periodically)
        # self._save_index()

    def search(self, query: str, top_k=5, rerank=False) -> Dict:
        if self.embedding_model is None or self.vector_index is None:
            logger.error("Embedding model or index not initialized. Cannot search.")
            return {"query": query, "results": [], "latency_ms": 0, "error": "embedding service unavailable"}

        start_time = time.time()

        # 1. Vector Search
        query_vec = self.embedding_model.encode([query], convert_to_numpy=True)
        distances, indices = self.vector_index.search(query_vec, top_k * 2 if rerank else top_k)
        
        candidates = []
        for i, idx in enumerate(indices[0]):
            if idx == -1: continue
            doc = self.documents[idx]
            candidates.append({
                "text": doc["text"],
                "metadata": doc["metadata"],
                "score": float(distances[0][i])
            })
            
        # 2. Rerank (Optional)
        if rerank and self.rerank_model and candidates:
            pairs = [[query, c["text"]] for c in candidates]
            rerank_scores = self.rerank_model.predict(pairs)
            for i, c in enumerate(candidates):
                c["rerank_score"] = float(rerank_scores[i])
            # Sort by rerank score
            candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
            
        total_latency = (time.time() - start_time) * 1000
        
        return {
            "query": query,
            "results": candidates,
            "latency_ms": total_latency
        }
        
    def get_status(self):
        return {
            "embedding_model": str(self.embedding_model) if self.embedding_model else "not loaded (error)",
            "rerank_model": str(self.rerank_model) if self.rerank_model else "none",
            "index_size": self.vector_index.ntotal if self.vector_index else 0,
            "dimension": self.dimension,
            "documents": len(self.documents)
        }

embedding_service = EmbeddingService()
