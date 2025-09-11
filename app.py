import streamlit as st
import os
import asyncio
from typing import Dict, Any

from agent.graph import build_graph
from agent.ingest import ingest_pdf_to_chroma
from agent.config import DOC_PATH

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
    
# Page config
st.set_page_config(
    page_title="Wine Concierge",
    page_icon="🍷",
    layout="wide"
)

# Global styles: make weather card prominent and fixed on desktop
st.markdown(
    """
    <style>
    .weather-card {
    position: fixed;
    top: 60px;        
    right: 75px;      
    width: 280px;
    background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
    color: #e5e7eb;
    padding: 14px 16px;
    border-radius: 14px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.4);
    border: 1px solid rgba(255,255,255,0.08);
    z-index: 1000; /* always on top */
}
    .weather-card h4 { margin: 0 0 6px 0; font-weight: 700; }
    .weather-card p { margin: 0; }
    .weather-badges { font-size: 12px; color: #9ca3af; margin-top: 6px; }
    /* On small screens, let it flow normally */
    @media (max-width: 900px) {
        .weather-card { position: static; width: 100%; margin-top: 12px; }
    }

    /* Fixed footer just above the bottom chat input */
    .powered-footer {
    margin-top: 12px;       /* space after chat input */
    width: 100%;
    text-align: center;
    background: rgba(17, 24, 39, 0.85);
    color: #d1d5db;
    padding: 10px 0;
    border-radius: 10px;
    font-size: 13px;
    border: 1px solid rgba(255,255,255,0.12);
}

    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "graph" not in st.session_state:
    st.session_state.graph = None

# Sidebar for settings and ingestion
with st.sidebar:
    st.title("🍷 Wine Concierge")
    
    # Check if vector store exists
    vector_exists = os.path.exists(".vectorstore/chunks.json")
    
    if not vector_exists:
        st.warning("⚠️ PDF not ingested yet!")
        if st.button("📄 Ingest PDF", type="primary"):
            with st.spinner("Ingesting PDF..."):
                try:
                    result = ingest_pdf_to_chroma()
                    st.success(result)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.success("✅ PDF ingested")
        if st.button("🔄 Re-ingest PDF"):
            with st.spinner("Re-ingesting PDF..."):
                try:
                    result = ingest_pdf_to_chroma()
                    st.success(result)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    st.divider()
    
    # Settings
    st.subheader("⚙️ Settings")
    default_city = st.text_input("Default City", value="Napa, CA")
    
    st.divider()
    
    # Clear chat
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Main chat interface with weather in top right
col1, col2 = st.columns([3, 1])

with col1:
    st.title("🍷 Wine Business Concierge")
    st.caption("Ask about our wines, get weather updates, or search for latest news!")

# Weather display in top right
try:
    from agent.tools import current_weather
    # Use sidebar-controlled default city
    weather_data = current_weather(default_city)
    st.markdown(f"""
    <div class="weather-card">
        <h4>🌤️ {weather_data['city'].upper()[0]+weather_data['city'][1:]}</h4>
        <p style="font-size: 22px; font-weight: 800;">{weather_data['temperature']}°C</p>
        <p style="color: #d1d5db;">{weather_data['conditions'].title()}</p>
        <p class="weather-badges">💧 {weather_data['humidity']}% • 💨 {weather_data['wind_speed']} m/s</p>
    </div>
    """, unsafe_allow_html=True)
except Exception as e:
    st.error(f"Weather unavailable: {e}")

if st.session_state.graph is None and vector_exists:
    with st.spinner("Initializing agent..."):
        try:
            st.session_state.graph = build_graph()
        except Exception as e:
            st.error(f"Failed to initialize agent: {e}")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Show additional info if available
        if "metadata" in message:
            with st.expander("📋 Details"):
                if "citations" in message["metadata"]:
                    st.write("**Sources:**")
                    for i, citation in enumerate(message["metadata"]["citations"], 1):
                        st.write(f"[{i}] {citation}")
                
                if "links" in message["metadata"]:
                    st.write("**Web Search Results:**")
                    for i, link in enumerate(message["metadata"]["links"], 1):
                        with st.expander(f"[{i}] {link['title']}"):
                            st.write(f"**URL:** [{link['url']}]({link['url']})")
                            st.write(f"**Summary:** {link['snippet']}")
                
                if "raw" in message["metadata"]:
                    st.json(message["metadata"]["raw"])

if prompt := st.chat_input("Ask me anything about our wine business..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    if st.session_state.graph is None:
        st.error("Agent not initialized. Please ingest the PDF first.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    state = {"query": prompt}
                    config = {"configurable": {"thread_id": "streamlit_chat"}}
                    result = st.session_state.graph.invoke(state, config=config)
                    
                    answer = result.get("result", {}).get("answer", "Sorry, I couldn't process that.")
                    mode = result.get("mode", "unknown")
                    
                    st.markdown(answer)
                    
                    metadata = {}
                    if "citations" in result.get("result", {}):
                        metadata["citations"] = result["result"]["citations"]
                    if "links" in result.get("result", {}):
                        metadata["links"] = result["result"]["links"]
                    if "raw" in result.get("result", {}):
                        metadata["raw"] = result["result"]["raw"]
                    
                    mode_emoji = {"rag": "📄", "search": "🔍", "weather": "🌤️"}.get(mode, "❓")
                    st.caption(f"{mode_emoji} Used: {mode}")
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer,
                        "metadata": metadata
                    })
                    
                except Exception as e:
                    error_msg = f"Error: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": error_msg
                    })

# Footer pinned visually near the chat input (non-interactive)
st.markdown("""
<div class="powered-footer">Powered by Gemini, Tavily, and OpenWeather APIs</div>
""", unsafe_allow_html=True)
