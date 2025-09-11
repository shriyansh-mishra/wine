from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Iterable, List, Dict, Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

from .config import (
	DOC_PATH,
	EMBEDDING_MODEL,
	GOOGLE_API_KEY,
	VECTOR_DIR,
)


def load_pdf(path: Path) -> List:
	loader = PyPDFLoader(str(path))
	return loader.load()


def chunk_documents(documents: Iterable, chunk_size: int = 1000, chunk_overlap: int = 150) -> List:
	splitter = RecursiveCharacterTextSplitter(
		chunk_size=chunk_size,
		chunk_overlap=chunk_overlap,
		separators=["\n\n", "\n", " "]
	)
	return splitter.split_documents(list(documents))


def build_embeddings() -> GoogleGenerativeAIEmbeddings:
	if not GOOGLE_API_KEY:
		raise RuntimeError("GOOGLE_API_KEY is required for embeddings")
	return GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)


def ingest_pdf_to_chroma(pdf_path: Path | None = None) -> str:
	path = Path(pdf_path) if pdf_path else DOC_PATH
	if not path.exists():
		raise FileNotFoundError(f"Document not found: {path}")

	documents = load_pdf(path)
	chunks = chunk_documents(documents)
	embeddings = build_embeddings()

	# Create embeddings for all chunks
	print("Creating embeddings...")
	chunk_texts = [chunk.page_content for chunk in chunks]
	chunk_embeddings = embeddings.embed_documents(chunk_texts)
	
	# Prepare data for storage
	chunk_data = []
	for i, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings)):
		chunk_data.append({
			"id": i,
			"text": chunk.page_content,
			"metadata": chunk.metadata,
			"embedding": embedding
		})
	
	# Save to disk as JSON (no async issues)
	VECTOR_DIR.mkdir(exist_ok=True)
	with open(VECTOR_DIR / "chunks.json", "w", encoding="utf-8") as f:
		json.dump(chunk_data, f, indent=2, ensure_ascii=False)

	return f"Ingested {len(chunks)} chunks into simple file storage"


__all__ = ["ingest_pdf_to_chroma"]


