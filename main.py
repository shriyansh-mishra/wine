from __future__ import annotations

import os
from typing import Dict

from agent.ingest import ingest_pdf_to_chroma
from agent.graph import build_graph


def main():
	mode = os.getenv("MODE", "chat")
	if mode == "ingest":
		print(ingest_pdf_to_chroma())
		return

	graph = build_graph()
	print("Conversational Concierge ready. Type 'exit' to quit.")
	
	# Create a config with thread_id for the checkpointer
	config = {"configurable": {"thread_id": "main_chat"}}
	
	while True:
		q = input("You: ").strip()
		if q.lower() in {"exit", "quit"}:
			break
		state: Dict = {"query": q}
		result = graph.invoke(state, config=config)
		answer = result.get("result", {}).get("answer", "(no answer)")
		print(f"Agent: {answer}")


if __name__ == "__main__":
    main()
