from src.state import AgentState

def planning_node(state: AgentState):
    """
    Synthesizes memories, deltas, motivational drives into multi-turn internal objectives.
    Outputs planned actions for generate_node.
    """
    memories = state.get("memories", [])
    motivational = state.get("motivational", {})
    delta_history = state.get("delta_history", []) # Not yet fully used but available for future prompt expansion

    # Combine: memory salience + unresolved goals + motivational pressure
    planned_actions = []
    
    # 1. Goal Pursuit
    for goal in motivational.get("internal_goals", []):
        # Check if memory relates to goal
        # Simplistic substring match for now
        relevant_mem = [m for m in memories if isinstance(m, dict) and goal.lower() in m.get('description', '').lower()]
        if relevant_mem:
             planned_actions.append(f"Pursue goal '{goal}' by referencing memory: {relevant_mem[0]['description'][:50]}...")
        else:
             planned_actions.append(f"Pursue goal '{goal}' proactively")
             
    # 2. Conflict Resolution (if pressure is high)
    conflicts = motivational.get("internal_conflict", {})
    if conflicts:
        top_conflict = max(conflicts.items(), key=lambda x: x[1])
        planned_actions.append(f"Resolve internal conflict: {top_conflict[0]}")

    # Fallback
    if not planned_actions:
        planned_actions.append("Respond naturally to user input.")

    return {"planned_actions": planned_actions}
