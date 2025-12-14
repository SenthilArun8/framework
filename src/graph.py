from functools import partial
from langgraph.graph import StateGraph, END
from src.state import AgentState
from src.brain import retrieve_node, subconscious_node, delta_node, generate_node, learn_node, persist_node
from src.motivational import motivational_update_node

def build_graph(memory_store, kg=None):
    """Constructs the LangGraph for the Living Character."""
    print("[DEBUG] Building LangGraph...")
    
    # Initialize Graph with our State
    workflow = StateGraph(AgentState)
    
    # Define Nodes
    # We use partial to inject the memory_store dependency into retrieve_node
    workflow.add_node("retrieve", partial(retrieve_node, memory_store=memory_store, kg=kg))
    workflow.add_node("motivational", motivational_update_node)
    workflow.add_node("subconscious", subconscious_node)
    workflow.add_node("delta", delta_node)
    workflow.add_node("learn", partial(learn_node, memory_store=memory_store)) # NEW
    workflow.add_node("generate", generate_node)
    workflow.add_node("persist", partial(persist_node, kg=kg)) # NEW
    
    # Define Edges (Linear Flow)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "motivational")
    workflow.add_edge("motivational", "subconscious") 
    workflow.add_edge("subconscious", "delta")
    workflow.add_edge("delta", "learn")
    workflow.add_edge("learn", "generate")
    workflow.add_edge("generate", "persist")
    workflow.add_edge("persist", END)
    
    # Compile
    app = workflow.compile()
    return app
