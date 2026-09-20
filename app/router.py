import time
from typing import Dict, Any, List
import numpy as np
from fastembed import TextEmbedding
from app.config import settings

# 1. Initialize the embedding model (quantized ONNX, ~60MB on CPU)
embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

# 2. Canonical task anchors defining high-complexity tasks
REASONING_SEEDS = [
    "Write a recursive algorithm with dynamic programming memoization.",
    "Derive the mathematical proof for gradient descent convergence.",
    "Debug this concurrency deadlock in an asynchronous event loop.",
    "Analyze the architectural trade-offs of event-driven microservices.",
    "Optimize this distributed database query plan for high throughput."
]

def _compute_centroid(seeds: List[str]) -> np.ndarray:
    vectors = list(embedder.embed(seeds))
    centroid = np.mean(vectors, axis=0)
    return centroid / np.linalg.norm(centroid)

# Precompute and normalize centroid on startup
REASONING_CENTROID = _compute_centroid(REASONING_SEEDS)

def route_query(prompt: str) -> Dict[str, Any]:
    start_time = time.perf_counter()
    
    # Generate and normalize embedding
    query_vector = list(embedder.embed([prompt]))[0]
    norm = np.linalg.norm(query_vector)
    if norm > 0:
        query_vector = query_vector / norm
    
    # Cosine similarity via dot product of normalized vectors
    similarity_score = float(np.dot(query_vector, REASONING_CENTROID))
    latency_ms = (time.perf_counter() - start_time) * 1000.0
    
    target_tier = (
        "REASONING_TIER" 
        if similarity_score >= settings.ROUTING_SIMILARITY_THRESHOLD 
        else "FAST_TIER"
    )
    
    return {
        "target_tier": target_tier,
        "similarity_score": round(similarity_score, 4),
        "threshold": settings.ROUTING_SIMILARITY_THRESHOLD,
        "latency_ms": round(latency_ms, 2)
    }
