from __future__ import annotations

from typing import Any, Dict, List
import re

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI

from .config import MODEL_NAME
from .rag import retrieve
from .tools import current_weather, web_search


class AgentState(dict):
	query: str
	mode: str 
	result: Dict[str, Any]
	context: List[str]


def llm() -> ChatGoogleGenerativeAI:
	return ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.2)


def router(state: AgentState) -> str:
	q = state["query"].lower()
	
	if any(w in q for w in ["weather", "temperature", "forecast"]):
		return "weather"
	
	# Wine-related questions (use RAG)
	wine_keywords = [
		"wine", "grape", "vineyard", "winery", "cabernet", "merlot", "sauvignon", 
		"chardonnay", "pinot", "malbec", "fermentation", "tasting", "vintage",
		"poetry", "rhythm", "cliff lede", "napa", "stags leap", "variety", "varieties"
	]
	if any(keyword in q for keyword in wine_keywords):
		return "rag"
	
	return "search"


def _normalize_text(text: str) -> str:
	return re.sub(r"\s+", " ", text).strip()


def node_rag(state: AgentState) -> AgentState:
	query = state["query"]
	if any(word in query.lower() for word in ["variety", "varieties", "types", "kinds", "produce", "make"]):
		search_query = "Rhythm Vineyard plantings include Cabernet Sauvignon Merlot Cabernet Franc Petit Verdot Malbec Sauvignon Blanc Sémillon"
	else:
		search_query = query
	
	docs = retrieve(search_query, k=10)
	context = [
		f"Source[{i+1}] p{d.metadata.get('page', '?')}: {_normalize_text(d.page_content)}"
		for i, d in enumerate(docs)
	]
	prompt = (
		"You are a helpful assistant for a Napa Valley wine business. Answer strictly based on the provided context. "
		"Cite sources as [1], [2], ... corresponding to the excerpts. If unknown, say you don't know.\n\n"
		f"Question: {state['query']}\n\n"
		"Context:\n" + "\n\n".join(context)
	)
	resp = llm().invoke(prompt)
	return {**state, "mode": "rag", "context": context, "result": {"answer": resp.content, "citations": context}}


def node_search(state: AgentState) -> AgentState:
	results = web_search(state["query"], max_results=5)
	
	# Format results more cleanly
	formatted_results = []
	for i, r in enumerate(results):
		formatted_results.append(f"[{i+1}] {r['title']}\n   URL: {r['url']}\n   Summary: {r['snippet']}\n")
	
	summary_prompt = (
		"Based on the web search results below, provide a clear and well-formatted answer to the user's question. "
		"Use proper formatting with line breaks and bullet points where appropriate. "
		"Cite sources using [1], [2], etc. Keep the response concise but informative.\n\n"
		f"Question: {state['query']}\n\n"
		"Search Results:\n" + "\n".join(formatted_results)
	)
	resp = llm().invoke(summary_prompt)
	return {**state, "mode": "search", "context": [], "result": {"answer": resp.content, "links": results}}


def node_weather(state: AgentState) -> AgentState:
	data = current_weather()
	answer = (
		f"Weather for {data['city']}: {data['temperature']}°C, {data['conditions']}. "
		f"Humidity {data['humidity']}%, wind {data['wind_speed']} m/s."
	)
	return {**state, "mode": "weather", "context": [], "result": {"answer": answer, "raw": data}}


def build_graph() -> StateGraph:
	graph = StateGraph(AgentState)
	graph.add_node("rag", node_rag)
	graph.add_node("search", node_search)
	graph.add_node("weather", node_weather)
	
	graph.add_conditional_edges(
		START,
		router,  
		{
			"rag": "rag",
			"search": "search", 
			"weather": "weather"
		}
	)
	
	graph.add_edge("rag", END)
	graph.add_edge("search", END)
	graph.add_edge("weather", END)
	return graph.compile(checkpointer=MemorySaver())


__all__ = ["build_graph"]


