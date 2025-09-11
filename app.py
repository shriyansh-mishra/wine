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
    #model_temp = st.slider("Model Temperature", 0.0, 1.0, 0.2, 0.1)
    
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

with col2:
    # Weather display in top right
    try:
        from agent.tools import current_weather
        # Use sidebar-controlled default city
        weather_data = current_weather(default_city)
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-align: center;">
            <h4>🌤️ {weather_data['city']}</h4>
            <p style="margin: 0; font-size: 18px; font-weight: bold;">{weather_data['temperature']}°C</p>
            <p style="margin: 0; color: #666;">{weather_data['conditions'].title()}</p>
            <p style="margin: 0; font-size: 12px; color: #888;">💧 {weather_data['humidity']}% | 💨 {weather_data['wind_speed']} m/s</p>
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

# Footer
st.divider()
st.caption("Powered by Gemini, Tavily, and OpenWeather APIs")
