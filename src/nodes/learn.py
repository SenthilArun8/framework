import json
from src.state import AgentState
from src.schema import PsychologicalProfile, MemoryFragment

def learn_node(state: AgentState, memory_store):
    """
    Decides if the interaction is significant enough to form a permanent memory.
    Also commits INTERNAL REFLECTIONS if high confidence.
    """
    # Hydrate current state
    profile = PsychologicalProfile(**state['profile'])
    memories = [MemoryFragment(**m) if isinstance(m, dict) else m for m in state.get("memories", [])]
    cog_frame = state.get("cognitive_frame", {})
    thought = state['subconscious_thought']
    if state['messages']:
        user_input = state['messages'][-1].content
    else:
        user_input = "[INTERNAL]"

    # 1. Standard Interaction Memory
    # Heuristic: Importance is derived from confidence/intensity.
    confidence = cog_frame.get("confidence_level", 0.5)
    importance = min(max(confidence, 0.1), 1.0)
    
    from datetime import datetime
    import uuid
    
    emotional_tags = list(cog_frame.get("emotional_state", {}).keys())
    cognitive_tags = cog_frame.get("beliefs_held", [])
    
    new_mems_to_add = []

    # Interaction Mem
    inter_mem = MemoryFragment(
        id=str(uuid.uuid4())[:8],
        time_period=datetime.utcnow().isoformat(),
        description=f"Interaction: {user_input[:50]}... | Thought: {thought[:50]}...", 
        emotional_tags=emotional_tags,
        cognitive_tags=cognitive_tags,
        importance_score=importance,
        linked_memories=cog_frame.get("linked_memories", [])
    )
    # Full desc
    inter_mem.description = f"Interaction: {user_input} | Thought: {thought}"
    
    if inter_mem.importance_score > 0.2:
        new_mems_to_add.append(inter_mem)

    # 2. Internal Reflection Memory
    stack = state.get("cognitive_stack", [])
    if stack:
        last_frame = stack[-1] 
        if last_frame.get("confidence_level", 0.0) > 0.6:
             internal_mem = MemoryFragment(
                id=str(uuid.uuid4())[:8],
                time_period=datetime.utcnow().isoformat(),
                description=f"Internal Reflection: {json.dumps(last_frame.get('beliefs_held', []))}",
                emotional_tags=list(last_frame.get("emotional_state", {}).keys()),
                cognitive_tags=["REFLECTION", "SELF_DISCOVERY"],
                importance_score=last_frame.get("confidence_level", 0.5)
             )
             new_mems_to_add.append(internal_mem)

    if new_mems_to_add:
        # Check if memory_store has add_memories method or if we need check
        memory_store.add_memories(new_mems_to_add)
        print(f"📝 [Learning]: Committed {len(new_mems_to_add)} new memories.")
        
        # Append to current state memories for immediate consistency
        memories.extend(new_mems_to_add)
        return {
            "memories": [m.model_dump() for m in memories]
        }
    
    return {}
