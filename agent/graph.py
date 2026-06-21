from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
import os

from agent.tools import (
    identify_user, fetch_slots, book_appointment, retrieve_appointments, 
    cancel_appointment, modify_appointment, end_conversation
)

# Define State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    phone_number: str
    is_done: bool

# Initialize LLM
llm = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY", "dummy"),
    model="meta-llama/llama-3.3-70b-instruct:free",
)

# Bind tools
tools = [
    identify_user, fetch_slots, book_appointment, 
    retrieve_appointments, cancel_appointment, modify_appointment, end_conversation
]
llm_with_tools = llm.bind_tools(tools)

# Define Nodes
def agent_node(state: AgentState):
    # Append system prompt dynamically if needed, or just let messages handle it
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def tool_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_responses = []
    is_done = state.get("is_done", False)
    phone_number = state.get("phone_number", "")
    
    # Simple tool executor
    tool_map = {t.__name__: t for t in tools}
    
    for tool_call in last_message.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        
        print(f"Executing tool: {name} with args: {args}")
        
        if name in tool_map:
            try:
                res = tool_map[name](**args)
                if name == "identify_user" and "phone_number" in args:
                    phone_number = args["phone_number"]
                if name == "end_conversation":
                    is_done = True
                
                tool_responses.append(
                    ToolMessage(content=str(res), tool_call_id=tool_call["id"], name=name)
                )
            except Exception as e:
                tool_responses.append(
                    ToolMessage(content=f"Error: {str(e)}", tool_call_id=tool_call["id"], name=name)
                )
                
    return {"messages": tool_responses, "phone_number": phone_number, "is_done": is_done}

def route_after_agent(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    if state.get("is_done", False):
        return END
    return END

# Build Graph
graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)

graph.set_entry_point("agent")
graph.add_conditional_edges("agent", route_after_agent, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")

compiled_graph = graph.compile()
