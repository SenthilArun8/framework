from functools import partial
from langgraph.graph import StateGraph, END
from src.state import AgentState
from src.motivational import motivational_update_node
from src.nodes import (
    retrieve_node,
    subconscious_node,
    delta_node,
    planning_node,
    generate_node,
    learn_node,
    persist_node
)

def build_graph(memory_store, kg=None):
    """Constructs the LangGraph for the Living Character with Non-Linear Dynamics."""
    print("[DEBUG] Building LangGraph (Modular + Planning + Conditional Loop)...")

    # Initialize Graph
    workflow = StateGraph(AgentState)

    # --- Define Nodes ---
    workflow.add_node("retrieve", partial(retrieve_node, memory_store=memory_store, kg=kg))
    workflow.add_node("motivational", motivational_update_node)
    workflow.add_node("subconscious", subconscious_node)
    workflow.add_node("delta", delta_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("learn", partial(learn_node, memory_store=memory_store))
    workflow.add_node("generate", generate_node)
    workflow.add_node("persist", partial(persist_node, kg=kg))

    # --- Define Linear Edges ---
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "motivational")
    workflow.add_edge("motivational", "subconscious")
    workflow.add_edge("subconscious", "delta")
    workflow.add_edge("delta", "planning")
    workflow.add_edge("planning", "learn")
    workflow.add_edge("learn", "generate")

    # --- Conditional Edge: Generate → Subconscious (loop) or Persist ---
    def should_loop(state: AgentState):
        """
        If Cognitive Load is high, optionally loop back to subconscious for
        an internal reflection before finishing.
        Safety: Limit to 1 extra iteration per turn.
        """
        state['_generate_loop_count'] = state.get('_generate_loop_count', 0) + 1
        max_loops = 1  # only allow one loop
        load = state.get("motivational", {}).get("cognitive_state", {}).get("cognitive_load", 0.0)

        if load > 0.7 and state['_generate_loop_count'] <= max_loops:
            # High load → reprocess subconscious for fragmented / internal reflection
            return "subconscious"
        # Otherwise, continue to persist
        return "persist"

    workflow.add_conditional_edges(
        "generate",
        should_loop,
        {
            "subconscious": "subconscious",
            "persist": "persist"
        }
    )

    # --- Final Node ---
    workflow.add_edge("persist", END)

    # Compile the workflow
    app = workflow.compile()
    return app
