from __future__ import annotations

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document

from .config import EMBEDDING_MODEL, VECTOR_DIR


def _embeddings() -> GoogleGenerativeAIEmbeddings:
	return GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)


def cosine_similarity(a: List[float], b: List[float]) -> float:
	"""Calculate cosine similarity between two vectors"""
	a_np = np.array(a)
	b_np = np.array(b)
	return np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np))


def retrieve(query: str, k: int = 10) -> List[Document]:
	# Load chunks from JSON file
	chunks_file = VECTOR_DIR / "chunks.json"
	if not chunks_file.exists():
		return []
	
	with open(chunks_file, "r", encoding="utf-8") as f:
		chunk_data = json.load(f)
	
	# Get query embedding
	embeddings = _embeddings()
	query_embedding = embeddings.embed_query(query)
	
	# Calculate similarities
	similarities = []
	for chunk in chunk_data:
		similarity = cosine_similarity(query_embedding, chunk["embedding"])
		similarities.append((similarity, chunk))
	
	# Sort by similarity and get top k
	similarities.sort(key=lambda x: x[0], reverse=True)
	top_chunks = similarities[:k]
	
	# Convert to Document objects
	documents = []
	for _, chunk in top_chunks:
		doc = Document(
			page_content=chunk["text"],
			metadata=chunk["metadata"]
		)
		documents.append(doc)
	
	return documents


__all__ = ["retrieve"]


