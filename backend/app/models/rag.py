from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class DocumentChunk(BaseModel):
    id: str
    text: str
    metadata: Dict = Field(default_factory=dict)
    score: float = 0.0

class RAGQuery(BaseModel):
    query: str
    top_k: int = 5
    rerank: bool = True

class RAGRequest(BaseModel):
    query: str
    top_k: int = 5
    rerank: bool = True

class RAGResponse(BaseModel):
    query: str
    answer: str
    context: List[DocumentChunk]
    latency_ms: float
