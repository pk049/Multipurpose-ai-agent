from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage, AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode

from typing import Annotated, TypedDict, List, Dict
import operator
import os
from dotenv import load_dotenv
from datetime import datetime
import json

import streamlit as st
from pymongo import MongoClient

from Operations.file_operations import LANGCHAIN_TOOLS as FILE_TOOLS
from system_prompt import SYSTEM_PROMPT

load_dotenv()

# Page config
st.set_page_config(
    page_title="File System Agent",
    page_icon="📁",
    layout="wide"
)

st.title("📁 File System Agent with LangGraph")
st.markdown("*AI-powered file operations with human approval*")

# ======================
#   AGENT STATE
# ======================
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]


# ======================
#   MONGODB CONNECTION
# ======================
def init_mongodb():
    """Initialize MongoDB connection"""
    try:
        mongo_uri = os.getenv('MONGODB_URI', "mongodb://localhost:27017")
        conn = MongoClient(mongo_uri)
        db = conn['newdb']
        collection = db['tds']
        info = conn.server_info()
        st.sidebar.success("✅ Connected to MongoDB")
        return collection
    except Exception as e:
        st.sidebar.error(f"❌ MongoDB connection failed: {e}")
        return None


# ======================
#   SESSION MANAGEMENT
# ======================
def save_session_to_mongodb(collection, thread_id: str, state):
    """Save session to MongoDB"""
    if collection is None:
        return False
    
    try:
        all_messages = state.values.get("messages", [])
        
        conversation_history = []
        user_inputs = []
        
        for msg in all_messages:
            msg_data = {
                "type": msg.type,
                "content": msg.content if isinstance(msg.content, str) else str(msg.content),
                "timestamp": datetime.now().isoformat()
            }
            
            if isinstance(msg, AIMessage):
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    msg_data["tool_calls"] = [
                        {"name": tc.get("name"), "args": tc.get("args"), "id": tc.get("id")}
                        for tc in msg.tool_calls
                    ]
            elif isinstance(msg, HumanMessage):
                user_inputs.append(msg.content if isinstance(msg.content, str) else str(msg.content))
                
            conversation_history.append(msg_data)
        
        session_document = {
            "session_id": thread_id,
            "session_start": st.session_state.get('session_start', datetime.now().isoformat()),
            "session_end": datetime.now().isoformat(),
            "total_messages": len(all_messages),
            "user_inputs": user_inputs,
            "conversation_history": conversation_history,
            "status": "active"
        }
        
        collection.replace_one(
            {"session_id": thread_id},
            session_document,
            upsert=True
        )
        return True
    except Exception as e:
        st.sidebar.error(f"⚠️ Failed to save session: {e}")
        return False


# ======================
#   GRAPH SETUP
# ======================
@st.cache_resource
def create_graph():
    """Create and compile the LangGraph"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ GEMINI_API_KEY not found in environment")
        st.stop()
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3, api_key=api_key)
    llm_with_tools = llm.bind_tools(FILE_TOOLS)
    
    # NODE: LLM Node
    def llm_node(state: AgentState):
        messages = state["messages"]
        
        try:
            if not any(isinstance(msg, SystemMessage) for msg in messages):
                messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
            
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}
        
        except Exception as e:
            return {"messages": [AIMessage(content=f"❌ LLM failed: {e}")]}
    
    # CONDITIONAL EDGE: Check if tools need to be called
    def should_continue(state: AgentState):
        messages = state["messages"]
        last_msg = messages[-1]
        
        if isinstance(last_msg, AIMessage) and hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
            return "tools"
        else:
            return END
    
    # Build graph
    workflow = StateGraph(AgentState)
    workflow.add_node("llm", llm_node)
    workflow.add_node("tools", ToolNode(FILE_TOOLS))
    
    workflow.add_edge(START, "llm")
    workflow.add_conditional_edges("llm", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "llm")
    
    # Compile with checkpointer and interrupts
    checkpointer = MemorySaver()
    graph = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["tools"]  # Interrupt before tool execution
    )
    
    return graph


# ======================
#   INITIALIZE SESSION
# ======================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "graph" not in st.session_state:
    st.session_state.graph = create_graph()

if "thread_id" not in st.session_state:
    st.session_state.thread_id = datetime.now().isoformat()

if "session_start" not in st.session_state:
    st.session_state.session_start = datetime.now().isoformat()

if "mongodb_collection" not in st.session_state:
    st.session_state.mongodb_collection = init_mongodb()

if "awaiting_approval" not in st.session_state:
    st.session_state.awaiting_approval = False

if "pending_tool_calls" not in st.session_state:
    st.session_state.pending_tool_calls = []


# ======================
#   SIDEBAR INFO
# ======================
st.sidebar.header("📊 Session Info")
st.sidebar.text(f"Thread ID: {st.session_state.thread_id[:8]}...")
st.sidebar.text(f"Messages: {len(st.session_state.messages)}")

if st.sidebar.button("🔄 New Session"):
    st.session_state.messages = []
    st.session_state.thread_id = datetime.now().isoformat()
    st.session_state.session_start = datetime.now().isoformat()
    st.session_state.awaiting_approval = False
    st.session_state.pending_tool_calls = []
    st.rerun()


# ======================
#   DISPLAY MESSAGES
# ======================
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message("assistant"):
            st.write(msg["content"])
    elif msg["role"] == "tool":
        with st.chat_message("assistant", avatar="🔧"):
            st.info(msg["content"])


# ======================
#   APPROVAL UI
# ======================
if st.session_state.awaiting_approval and st.session_state.pending_tool_calls:
    st.markdown("---")
    st.warning("🚨 **Tool Approval Required**")
    
    for i, tool_call in enumerate(st.session_state.pending_tool_calls):
        with st.expander(f"Tool {i+1}: {tool_call.get('name', 'Unknown')}", expanded=True):
            st.json(tool_call.get('args', {}))
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Approve", type="primary", use_container_width=True):
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            
            # Resume with approval
            try:
                for event in st.session_state.graph.stream(
                    Command(resume="user approved"),
                    config,
                    stream_mode="values"
                ):
                    messages = event.get("messages", [])
                    if messages:
                        last_msg = messages[-1]
                        
                        # Handle tool messages
                        if isinstance(last_msg, ToolMessage):
                            st.session_state.messages.append({
                                "role": "tool",
                                "content": last_msg.content
                            })
                        
                        # Handle AI messages
                        elif isinstance(last_msg, AIMessage) and last_msg.content:
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": last_msg.content
                            })
                
                st.session_state.awaiting_approval = False
                st.session_state.pending_tool_calls = []
                
                # Save to MongoDB
                state = st.session_state.graph.get_state(config)
                save_session_to_mongodb(
                    st.session_state.mongodb_collection,
                    st.session_state.thread_id,
                    state
                )
                
                st.rerun()
            
            except Exception as e:
                st.error(f"Error resuming graph: {e}")
    
    with col2:
        if st.button("❌ Reject", type="secondary", use_container_width=True):
            st.session_state.awaiting_approval = False
            st.session_state.pending_tool_calls = []
            st.session_state.messages.append({
                "role": "assistant",
                "content": "❌ Operation cancelled by user."
            })
            st.rerun()


# ======================
#   CHAT INPUT
# ======================
if not st.session_state.awaiting_approval:
    user_input = st.chat_input("Enter your file operation request...")
    
    if user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        
        try:
            # Stream the graph
            for event in st.session_state.graph.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config,
                stream_mode="values"
            ):
                messages = event.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    
                    # Check if interrupted (tool call pending)
                    if isinstance(last_msg, AIMessage) and hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                        st.session_state.awaiting_approval = True
                        st.session_state.pending_tool_calls = last_msg.tool_calls
                        break
                    
                    # Add assistant response
                    elif isinstance(last_msg, AIMessage) and last_msg.content:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": last_msg.content
                        })
            
            # Save to MongoDB
            state = st.session_state.graph.get_state(config)
            save_session_to_mongodb(
                st.session_state.mongodb_collection,
                st.session_state.thread_id,
                state
            )
            
            st.rerun()
        
        except Exception as e:
            st.error(f"❌ Error: {e}")
