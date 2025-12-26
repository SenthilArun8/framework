from langchain_core.prompts import ChatPromptTemplate
from src.state import AgentState
from src.schema import EmotionalQuery, MemoryFragment
from src.llm_client import llm
from src.utils import log_exception

def retrieve_node(state: AgentState, memory_store, kg=None):
    """
    Finds memories based on emotional resonance + Graph Entities + Proactive Goals.
    """
    user_input = state['messages'][-1].content
    
    # Phase 10: Mood-Congruent Retrieval
    motivational = state.get("motivational", {})
    emotions = motivational.get("emotional_state", {})
    conflicts = motivational.get("internal_conflict", {})
    
    # Proactive Retrieval Trigger
    internal_goals = motivational.get("internal_goals", [])
    
    bias_str = f"Current Emotions: {emotions}\nInternal Conflicts: {conflicts}\nActive Goals: {internal_goals}"
    
    # 1. Query Expansion (The "Bridge")
    analysis_prompt = """
    You are an emotional association engine. You are analyzing an incoming message to a character.
    
    User Input: "{user_input}"
    
    Character Bias:
    {bias_str}
    
    Task:
    1. Identify the underlying emotional themes (e.g., Abandonment, Warmth, Criticism).
    2. Identify specific ENTITIES (People, Factions, Places) mentioned or implied.
    3. Create a 'Search Query' that describes a hypothetical memory this input might trigger.
       IMPORTANT: Bias the search query towards the character's current emotions. If they are fearful, look for threats.
    
    Output JSON compatible with EmotionalQuery schema.
    """
    
    prompt = ChatPromptTemplate.from_template(analysis_prompt)
    structured_llm = llm.with_structured_output(EmotionalQuery)
    chain = prompt | structured_llm
    
    memories_list = []
    
    try:
        data = chain.invoke({"user_input": user_input, "bias_str": bias_str})
        
        # 2. Vector Search (Weighted)
        vector_memories = memory_store.retrieve_relevant(
            query=data.memory_search_query, 
            k=5,
            min_importance=0.0
        )
        
        # Proactive Retrieval for Goals with Optimized Deduplication
        existing_ids = {m.id for m in vector_memories}
        for goal in internal_goals:
            goal_mems = memory_store.retrieve_relevant(goal, k=3)
            # Efficient O(1) deduplication
            for gm in goal_mems:
                 if gm.id not in existing_ids:
                      vector_memories.append(gm)
                      existing_ids.add(gm.id)

        # Weighting: Sort by importance * emotional intensity (sum of emotion values)
        total_emotion_intensity = sum(emotions.values()) if emotions else 1.0
        vector_memories.sort(key=lambda m: m.importance_score * total_emotion_intensity, reverse=True)
        
        memories_list.extend([m.model_dump() for m in vector_memories])
        
        # 3. Knowledge Graph RAG
        if kg and data.entities_of_interest:
            profile_data = state.get("profile")
            char_name = profile_data.get("name", "Elias") if isinstance(profile_data, dict) else profile_data.name

            for entity in data.entities_of_interest:
                paths = kg.get_opinion_on_topic(char_name, entity)
                if paths:
                    combined_path = " -> ".join(paths)
                    graph_mem = MemoryFragment(
                        id=f"graph_{entity}", 
                        time_period="Present Knowledge",
                        description=f"Relationship to {entity}: {combined_path}",
                        emotional_tags=["Knowledge", "Opinion"],
                        importance_score=0.8
                    ).model_dump()
                    memories_list.append(graph_mem)
        
        return {"memories": memories_list}
        
    except Exception as e:
        log_exception("Retrieve Node", e)
        # Fallback
        memories = memory_store.retrieve_relevant(user_input, k=3)
        return {"memories": [m.model_dump() for m in memories]}
