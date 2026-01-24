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
# import streamlit as st
from pymongo import MongoClient
from Operations.file_operations import LANGCHAIN_TOOLS as FILE_TOOLS
from system_prompt import SYSTEM_PROMPT

load_dotenv()

# Agent state
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]

# Making the gemini model
try:
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("GEMINI API KEY NOT FOUND IN ENV..............")
    llm = ChatGoogleGenerativeAI(
        model='gemini-2.5-flash',
        api_key=api_key,
        temperature=0.3
    )
    llm_with_tools = llm.bind_tools(FILE_TOOLS)
    print(f"Created model successfully with API KEY and Temperature {0.3}")
except Exception as e:
    print(f"Error occurred while creating Gemini Model: {e}")

# ======================================= MAKING THE GRAPH =============================================

# Graph node functions
def llm_node(state: AgentState):
    """LLM node that processes messages and invokes the model"""
    messages = state["messages"]
    
    # Add system prompt if this is the first message
    if len(messages) == 1 and isinstance(messages[0], HumanMessage):
        messages_with_system = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        print("System prompt added")
    else:
        messages_with_system = messages
    
    try:
        result = llm_with_tools.invoke(messages_with_system)
        return {"messages": [result]}
    except Exception as e:
        print(f"LLM invoking failed in graph: {e}")
        return {"messages": [AIMessage(content=f"Error: {str(e)}")]}

def should_continue(state: AgentState):
    """Determine if we should continue to tools or end"""
    messages = state["messages"]
    last_msg = messages[-1]
    
    if isinstance(last_msg, AIMessage) and hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tool_node"
    else:
        return END

# Making actual graph
try:
    workflow = StateGraph(AgentState)
    workflow.add_node("llm_node", llm_node)
    workflow.add_node("tool_node", ToolNode(FILE_TOOLS))
    
    workflow.add_edge(START, "llm_node")
    workflow.add_conditional_edges(
        "llm_node",
        should_continue,
        {"tool_node": "tool_node", END: END}
    )
    workflow.add_edge("tool_node", "llm_node")
    
    checkpointer = MemorySaver()
    graph = workflow.compile(interrupt_before=["tool_node"], checkpointer=checkpointer)
    print("Graph is now compiled...")
except Exception as e:
    print(f"Error occurred while creating a graph: {e}")



# ======================================= RUNNING THE GRAPH =============================================

def run_agent():
    """Run the agent with user input"""
    user_input = input("Enter user input: ")
    config = {"configurable": {"thread_id": datetime.now().isoformat()}}
    
    # Initial input
    current_input = {"messages": [HumanMessage(content=user_input)]}
    
    while True:
        for event in graph.stream(current_input, stream_mode="values", config=config):
            last_msg = event["messages"][-1]
            
            if isinstance(last_msg, AIMessage) and hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                try:
                    print("\nThe next tool that will be called is:")
                    print(f"Tool name: {last_msg.tool_calls[0]['name']}")
                    print(f"Tool arguments: {last_msg.tool_calls[0]['args']}")
                except Exception as e:
                    print(f"LLM will call: {last_msg.tool_calls}")
                    
            elif isinstance(last_msg, AIMessage) and last_msg.content:
                # Handle different content formats
                if isinstance(last_msg.content, str):
                    content = last_msg.content
                elif isinstance(last_msg.content, list) and len(last_msg.content) > 0:
                    # Content is a list of content blocks
                    if isinstance(last_msg.content[0], dict) and 'text' in last_msg.content[0]:
                        content = last_msg.content[0]['text']
                    else:
                        content = str(last_msg.content[0])
                else:
                    content = str(last_msg.content)
                
                print(f"\nAssistant: {content}")
              
            elif isinstance(last_msg, ToolMessage):
                try:
                    print(f"Tool result: {last_msg.content}")
                except Exception as e:
                    print(f"The tool message is: {last_msg}")
        
        # Check if we need approval
        snapshot = graph.get_state(config=config)
        if snapshot.next:
            # Get tool name from the last AI message
            ai_msg = snapshot.values["messages"][-1]
            if isinstance(ai_msg, AIMessage) and ai_msg.tool_calls:
                tool_name = ai_msg.tool_calls[0]['name']
            else:
                tool_name = "tool"
            
            approval = input(f"\nApprove execution of {tool_name}? (yes/no): ").lower()
            
            if approval == "yes":
                current_input = Command(resume="user approved")
            else:
                current_input = Command(resume="user denied")
        else:
            # Conversation ended, get new input
            user_input = input("\nEnter next task (or 'quit' to exit): ")
            if user_input.lower() == 'quit':
                break
            current_input = {"messages": [HumanMessage(content=user_input)]}



if __name__ == "__main__":
    run_agent()