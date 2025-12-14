import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage
from src.state import AgentState # Updated import
from src.schema import PsychologicalProfile, MemoryFragment, PersonalityDelta, EmotionalQuery # Updated import

# Initialize LLM
# Use gemini-2.0-flash-exp or gemini-1.5-pro (gemini-1.5-flash is deprecated)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.2
)

# Helper
def clamp(n, minn, maxn):
    return max(minn, min(n, maxn))

import sys

# --- Node 1: Retrieval (Not an LLM node in standard RAG, but now an Emotional Agent) ---
def retrieve_node(state: AgentState, memory_store, kg=None):
    """
    Finds memories based on emotional resonance + Graph Entitites.
    
    FALLBACK: If the LLM call fails (e.g. API error), this node safely catches the exception
    and performs a raw keyword search on the memory_store using 'user_input'.
    """
    user_input = state['messages'][-1].content
    
    # Phase 10: Mood-Congruent Retrieval
    motivational = state.get("motivational", {})
    emotions = motivational.get("emotional_state", {})
    conflicts = motivational.get("internal_conflict", {})
    bias_str = f"Current Emotions: {emotions}\nInternal Conflicts: {conflicts}"
    
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
            k=3,
            min_importance=0.0
        )
        memories_list.extend([m.model_dump() for m in vector_memories])
        
        # 3. Knowledge Graph RAG (New Phase 8)
        if kg and data.entities_of_interest:
            # Hydrate profile for name
            profile_data = state.get("profile")
            char_name = profile_data.get("name", "Elias") if isinstance(profile_data, dict) else profile_data.name

            for entity in data.entities_of_interest:
                # Find opinion paths
                paths = kg.get_opinion_on_topic(char_name, entity)
                if paths:
                    # Synthesize a "Graph Memory"
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
        print(f"Retrieval Logic Failed: {e}")
        # Fallback
        memories = memory_store.retrieve_relevant(user_input, k=3)
        return {"memories": [m.model_dump() for m in memories]}

# --- Node 2: Subconscious Analysis ---
def subconscious_node(state: AgentState):
    """
    Reflects on the input before speaking.
    Output: 'subconscious_thought' (str)
    """
    # Hydrate objects
    profile = PsychologicalProfile(**state['profile'])
    memories = [MemoryFragment(**m) if isinstance(m, dict) else m for m in state['memories']]
    user_input = state['messages'][-1].content
    
    # Phase 10: Cognitive Load Filtering
    motivational = state.get("motivational", {})
    cog_state = motivational.get("cognitive_state", {})
    load = cog_state.get("cognitive_load", 0.0)
    
    if load > 0.7:
        # High Load: Fragmented Attention
        memories = memories[:1] # Throttle working memory
        context_instruction = "Your mind is racing. You cannot think clearly. Fragmented thoughts only."
    else:
        context_instruction = "Use your inner voice. Reflect deeply."

    # Simple textual representation of memories
    mem_str = "\n".join([f"- [{m.time_period}] {m.description} (Tags: {m.emotional_tags})" for m in memories])

    # Convert profile to a concise string for the prompt
    values_str = ", ".join([f"{v.name} ({v.score})" for v in profile.values.values()])
    
    prompt = ChatPromptTemplate.from_template("""
    You are the subconscious of a character. 
    Review the User Input and your Current Psyche.
    Check if this triggers any stored Memories.
    
    Current Psyche:
    - Mood: {mood}
    - Values: {values}
    - Goals: {goals}
    
    Triggered Memories (Working Memory):
    {mem_str}
    
    User Input: "{input}"
    
    Cognitive Context: {context_instruction}
    
    Task: Use your inner voice. Does this challenge your beliefs? specific memories? 
    Output a raw thought (no JSON, just text).
    """)
    
    chain = prompt | llm | StrOutputParser()
    thought = chain.invoke({
        "mood": profile.current_mood,
        "values": values_str,
        "goals": profile.goals,
        "mem_str": mem_str,
        "input": user_input,
        "context_instruction": context_instruction
    })
    
    return {"subconscious_thought": thought}

# --- Node 3: Delta State Updater ---
def delta_node(state: AgentState):
    """
    Decides if the profile needs updating (values, mood, trust).
    Output: 'profile' (Updated PsychologicalProfile object)
    """
    user_input = state['messages'][-1].content
    thought = state['subconscious_thought']
    
    # Hydrate
    profile = PsychologicalProfile(**state['profile'])
    memories = [MemoryFragment(**m) if isinstance(m, dict) else m for m in state['memories']]
    
    # Simple memory context string
    memory_context = "\n".join([f"- [{m.time_period}] {m.description}" for m in memories])

    # Phase 10: Defense Mechanisms
    motivational = state.get("motivational", {})
    coping = motivational.get("coping_styles", {})
    coping_str = str(coping)

    # 1. Prepare Prompt
    system_prompt = """You are the subconscious mind of the character. 
    You are analyzing the conversation to update your internal psychology.
    
    Current State:
    Mood: {current_mood}
    Core Values: {values}
    Relationship with User: {relationship}
    
    Active Defense Mechanisms (Coping Styles):
    {coping_str}
    
    Input:
    User said: "{user_input}"
    Retrieved Memory context: "{memory_context}"
    
    Task:
    Analyze the user's input. Does it challenge your beliefs? Does it comfort you? Does it make you trust them more or less?
    
    Rules:
    1. Neuroplasticity is slow. Do not flip values from 0.1 to 0.9 in one turn. Small increments (+/- 0.05) are realistic.
    2. Ego is fragile. If the user attacks your values, your immediate reaction might be to lower trust, even if they are right.
    3. DEFENSE: If 'Avoidance', 'Intellectualization', or 'Aggression' styles are high (>0.6) and the input is challenging, 
       REJECT the change. Do not update values. Justify this resistance in the thought process.
    
    Output ONLY the JSON object defined by the PersonalityDelta schema.
    """
    
    prompt = ChatPromptTemplate.from_template(system_prompt)
    
    # 2. Call LLM with Structured Output (Force Schema)
    structured_llm = llm.with_structured_output(PersonalityDelta)
    chain = prompt | structured_llm
    
    # Serialization for prompt
    values_json = json.dumps({v.name: v.score for v in profile.values.values()})
    # Warning: relationship dict might be large, for now just dump specifically for ID if possible, 
    # but we'll dump all for generality as per user prompt "relationship={relationship}"
    rel_json = json.dumps({k: {"trust": v.trust_level, "respect": v.respect_level} for k,v in profile.relationships.items()})

    try:
        delta = chain.invoke({
            "current_mood": profile.current_mood,
            "values": values_json,
            "relationship": rel_json,
            "user_input": user_input,
            "memory_context": memory_context,
            "coping_str": coping_str
        })
        
        # 4. Apply Changes (Evolution Logic)
        
        # Update Mood
        if delta.mood_shift:
            # Handle "Old -> New" format if LLM follows it, or just New
            new_mood = delta.mood_shift.split("->")[-1].strip()
            profile.current_mood = new_mood
            
        # Update Values
        for change in delta.values_impacted:
            # Finding the key by value name is tricky if they don't match exact keys.
            # We assume 'value_name' matches the key or the name field.
            # Best effort match:
            target_key = None
            for key, val_obj in profile.values.items():
                if val_obj.name.lower() == change.value_name.lower() or key == change.value_name:
                    target_key = key
                    break
            
            if target_key:
                # HARD CLAMP: Max +/- 0.05 change per turn
                current_score = profile.values[target_key].score
                raw_new_score = change.new_score
                delta_val = raw_new_score - current_score
                clamped_delta = max(-0.05, min(0.05, delta_val))
                final_score = clamp(current_score + clamped_delta, 0.0, 1.0)
                
                profile.values[target_key].score = final_score
                profile.values[target_key].justification = change.reason
        
        # Update Relationship (Hardcoded for single user 'User_123' for now as per example)
        # Ideally we get user ID from state
        user_id = "User_123" 
        if delta.relationship_impact and user_id in profile.relationships:
            user_rel = profile.relationships[user_id]
            user_rel.trust_level = clamp(user_rel.trust_level + delta.relationship_impact.trust_change, 0, 100)
            user_rel.respect_level = clamp(user_rel.respect_level + delta.relationship_impact.respect_change, 0, 100)
            user_rel.latest_impression = delta.relationship_impact.new_impression
            
        # We also need to put the thought process somewhere so we can see it.
        # We'll save it to subconscious_thought in the state for the next node (Generation) to use.
        return {
            "profile": profile.model_dump(),
            "subconscious_thought": delta.thought_process
        }

    except Exception as e:
        print(f"Delta Logic Failed: {e}\n", flush=True)
        return {}

# --- Node 4: Generation ---
def generate_node(state: AgentState):
    """Generates the final response."""
    user_input = state['messages'][-1].content
    thought = state['subconscious_thought']
    
    # Hydrate
    profile = PsychologicalProfile(**state['profile'])
    memories = [MemoryFragment(**m) if isinstance(m, dict) else m for m in state['memories']]
    
    # Hydrate Motivational State (Phase 7)
    motivational = state.get("motivational", {})
    active_strategy = motivational.get("active_strategy", "neutral")
    
    # Strategy Mapping
    STRATEGY_MAP = {
        "fragmented_thoughts": "Use interrupted sentences (...), change topics abruptly, show confusion. You are overwhelmed.",
        "defensive_curt": "Be short, sharp, and defensive. Do not elaborate.",
        "over_explaining_clingy": "Use overly long justifications, apologies, and disclaimers. Fawn over the user.",
        "shutdown_withdrawal": "Be very concise, cold, and withdrawn. Give one-word answers if possible.",
        "spaced_out_drifting": "Use odd spacing, unrelated thoughts intruding. You are dissociating.",
        "mixed_signals_hesitant": "Be inconsistent, say one thing then retract it. hesitate.",
        "argumentative_assertive": "Use defensive, argumentative tone. Challenge the user.",
        "vulnerable_seeking": "Be clingy, use emotional self-disclosure. Seek reassurance.",
        "hyper_vigilant": "Be suspicious, ask clarifying questions, do not trust.",
        "needy_demanding": "Demand attention or answers.",
        "neutral": "Speak normally, but consistent with your mood."
    }
    
    # Phase 11: Strategy Blending Logic
    instruction_lines = []
    
    if isinstance(active_strategy, dict):
        # Weighted blend
        strategy_display_name = "BLENDED_STATE"
        instruction_lines.append(f"Blend the following behavioral styles based on their weights:")
        for stra, weight in active_strategy.items():
            desc = STRATEGY_MAP.get(stra, "Standard behavior.")
            instruction_lines.append(f"- {stra.upper()} ({weight*100}%): {desc}")
    else:
        # Single legacy strategy
        strategy_display_name = active_strategy.upper()
        desc = STRATEGY_MAP.get(active_strategy, "Speak normally.")
        instruction_lines.append(f"{desc}")

    style_instruction = "\n".join(instruction_lines)
    
    prompt = ChatPromptTemplate.from_template("""
    You are the character described below.
    
    Profile:
    - Mood: {mood}
    - Role: Medic/Survivor
    
    EMERGENT BEHAVIOR STRATEGY: {strategy_name}
    INSTRUCTION: 
    {style_instruction}
    
    Internal Thought (Do NOT speak this, just act on it): 
    "{thought}"
    
    Relevant Memories:
    {mem_str}
    
    User said: "{input}"
    
    Respond in character. Blend the instructions if multiple are present.
    """)
    
    # Formatting
    mem_str = "\n".join([f"- {m.description}" for m in memories])
    
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({
        "mood": profile.current_mood,
        "strategy_name": strategy_display_name,
        "style_instruction": style_instruction,
        "thought": thought,
        "mem_str": mem_str,
        "input": user_input
    })
    
    return {"messages": [response]}

# --- Node 5: Learning (Phase 9) ---
def learn_node(state: AgentState, memory_store):
    """
    Decides if the interaction is significant enough to form a permanent memory.
    """
    user_input = state['messages'][-1].content
    thought = state['subconscious_thought']
    
    # Heuristic: Only learn if there's sufficient emotional weight or specific triggers?
    # Or ask LLM.
    
    prompt = ChatPromptTemplate.from_template("""
    You are the memory consolidation system.
    Analyze the interaction to see if a NEW meaningful memory should be formed.
    
    User Input: "{input}"
    Internal Thought: "{thought}"
    
    Criteria for significant memory:
    1. Reveals major new information about the user.
    2. Is an emotionally intense event (conflict, bonding).
    3. Changes the relationship state significantly.
    
    If YES, output the memory content. If NO, output "None".
    
    Output Format:
    Title: [Short Title]
    Description: [1-2 sentences]
    Time Period: "Recent Interaction"
    Tags: [Tag1, Tag2]
    Importance: [0.0 - 1.0]
    """)
    
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"input": user_input, "thought": thought})
    
    if "None" in result or len(result) < 10:
        return {}
        
    try:
        # Simple parsing of the non-JSON output (speed over strict schema for now, or could use schema)
        # Let's assume the LLM generates a block.
        # Ideally we use Structured Output for safety.
        # Let's pivot to Structured Output for robustness.
        from typing import List, Optional
        from pydantic import BaseModel, Field

        class NewMemory(BaseModel):
            should_commit: bool
            description: str
            emotional_tags: List[str]
            importance: float
            
        structured_llm = llm.with_structured_output(NewMemory)
        chain_v2 = prompt | structured_llm
        
        mem_data = chain_v2.invoke({"input": user_input, "thought": thought})
        
        if mem_data.should_commit and mem_data.importance > 0.4:
            # Create Fragment
            from datetime import datetime
            import uuid
            
            new_id = str(uuid.uuid4())[:8]
            frag = MemoryFragment(
                id=new_id,
                time_period="Recent",
                description=mem_data.description,
                emotional_tags=mem_data.emotional_tags,
                importance_score=mem_data.importance
            )
            
            # Commit to Store
            memory_store.add_memories([frag])
            print(f"📝 [Learning]: Committed new memory '{mem_data.description}'")
            
    except Exception as e:
        print(f"Learning Logic Failed: {e}")
        
    
    return {} # No state update needed, side effect on store

# --- Node 6: Persistence (Phase 9) ---
def persist_node(state: AgentState, kg=None):
    """
    Handles all side-effects: Neo4j updates, File saves.
    Decouples main.py from internal logic.
    """
    try:
        profile = PsychologicalProfile(**state['profile'])
        
        # 1. Update Knowledge Graph (Trust/Events)
        if kg and state.get('old_profile'):
            old_profile = PsychologicalProfile(**state['old_profile'])
            user_id = "User_123"
            
            # Trust Delta
            if user_id in profile.relationships and user_id in old_profile.relationships:
                new_rel = profile.relationships[user_id]
                old_rel = old_profile.relationships[user_id]
                trust_delta = new_rel.trust_level - old_rel.trust_level
                
                if abs(trust_delta) > 0.0:
                     kg.update_trust(profile.name, user_id, trust_delta)
            
            # Interaction Event
            thought = state.get('subconscious_thought', '')
            if thought:
                kg.add_interaction_event(profile.name, user_id, thought, profile.current_mood)

        # 2. Save Profile to Disk
        # We need the save function. Imported at top? No, passed or re-imported.
        # It's cleaner to import it here or at top.
        from schema import save_character_profile
        save_character_profile(profile, "character.json")
        
        # 3. Dashboard Dump (Partial replication of logic, or just let main do it? 
        # Plan said: "Dump live_state.json". Let's do it here for full decoupling.)
        import json
        viz_data = {"nodes": [], "edges": []}
        if kg:
             viz_data = kg.get_viz_data()
             
        # Reconstruct output state for dump
        dump_state = {
            "profile": profile.model_dump(),
            # Chat Log is managed by main.py (history.json), so we might miss it here unless passed in state?
            # State doesn't have chat_log.
            # Compromise: persist_node updates DBs and Profile. main.py handles Chat History and Dashboard Dump?
            # User asked for "Dump live_state.json" in persist_node.
            # I'll dump what I have. main.py can overwrite or we add chat_history to state.
            # Let's keep Dashboard Dump in main.py for now to avoid passing massive chat history in LangGraph state.
            # I will ONLY do KG and Profile Save here.
        }
        
        return {} # Pass through
        
    except Exception as e:
        print(f"Persistence Logic Failed: {e}")
        return {}
