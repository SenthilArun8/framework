import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage
from src.state import AgentState # Updated import
from src.schema import PsychologicalProfile, MemoryFragment, PersonalityDelta, EmotionalQuery, save_character_profile # Updated import

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

# --- Node 2: Subconscious Analysis (Enforced Cognition) ---
def subconscious_node(state: AgentState):
    """
    Reflects on the input before speaking.
    Output: 'cognitive_frame' (dict) and 'subconscious_thought' (str, JSON)
    """
    from src.schema import CognitiveFrame
    
    # Hydrate objects
    profile = PsychologicalProfile(**state['profile'])
    memories = [MemoryFragment(**m) if isinstance(m, dict) else m for m in state['memories']]
    user_input = state['messages'][-1].content

    # Cognitive Load Filtering
    cog_load = state.get("motivational", {}).get("cognitive_state", {}).get("cognitive_load", 0.0)
    if cog_load > 0.7:
        # High Load: Fragmented Attention
        memories = memories[:1]  # Throttle working memory
        context_instruction = "Your mind is racing. Fragmented thoughts only."
    else:
        context_instruction = "Use your inner voice. Reflect deeply."

    # Simple textual representation of memories
    mem_str = "\n".join([
        f"- [{m.time_period}] {m.description} (Tags: {m.emotional_tags}, Cognitive: {getattr(m, 'cognitive_tags', [])})"
        for m in memories
    ])

    # Convert profile to a concise string for the prompt
    values_str = ", ".join([f"{v.name} ({v.score})" for v in profile.values.values()])

    # Prompt for structured LLM
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

    Task: 
    Analyze the situation and output a Structured Cognitive Frame.
    Include 'linked_memories' that influenced your beliefs.

    Fields to Generate:
    1. beliefs_held
    2. beliefs_rejected
    3. emotional_state
    4. behavioral_constraints
    5. confidence_level
    6. linked_memories

    Output ONLY the JSON object defined by the CognitiveFrame schema.
    """)

    structured_llm = llm.with_structured_output(CognitiveFrame)
    chain = prompt | structured_llm

    try:
        frame = chain.invoke({
            "mood": profile.current_mood,
            "values": values_str,
            "goals": profile.goals,
            "mem_str": mem_str,
            "input": user_input,
            "context_instruction": context_instruction
        })

        # Always serialize for downstream robustness
        thought_str = json.dumps(frame.model_dump(), indent=2)

        return {
            "cognitive_frame": frame.model_dump(),
            "subconscious_thought": thought_str
        }

    except Exception as e:
        print(f"Subconscious Logic Failed: {e}")
        return {"subconscious_thought": "I am processing...", "cognitive_frame": {}}

# --- Node 3: Delta State Updater ---
# --- Node 3: Delta State Updater ---
def delta_node(state: AgentState):
    """
    Updates the psychological profile (values, mood, trust) based on cognitive frame.
    """
    # Helper for clamping values
    def clamp(n, smallest, largest): 
        return max(smallest, min(n, largest))

    user_input = state['messages'][-1].content
    thought = state['subconscious_thought']

    profile = PsychologicalProfile(**state['profile'])
    # Safer memory hydration
    memories = [MemoryFragment(**m) if isinstance(m, dict) else m for m in state.get('memories', [])]
    memory_context = "\n".join([f"- [{m.time_period}] {m.description}" for m in memories])

    coping_str = str(state.get("motivational", {}).get("coping_styles", {}))
    cog_load = state.get("motivational", {}).get("cognitive_state", {}).get("cognitive_load", 0.0)

    autonomy_instruction = (
        """
        [STATE: OVERWHELMED (High Cognitive Load)]
        Accept scaffolding.
        """ if cog_load > 0.7 else
        """
        [STATE: STABLE (Low Cognitive Load)]
        Resist control, assert autonomy.
        """
    )

    # LLM prompt for personality delta
    system_prompt = f"""
    You are the subconscious mind of the character.
    Current Mood: {{current_mood}}
    Values: {{values}}
    Relationship: {{relationship}}
    Coping Styles: {coping_str}

    User Input: "{{user_input}}"
    Memory Context: "{{memory_context}}"

    Autonomy Instruction: {autonomy_instruction}

    Output ONLY the JSON object defined by the PersonalityDelta schema.
    """
    prompt = ChatPromptTemplate.from_template(system_prompt)
    structured_llm = llm.with_structured_output(PersonalityDelta)
    chain = prompt | structured_llm

    values_json = json.dumps({v.name: v.score for v in profile.values.values()})
    rel_json = json.dumps({k: {"trust": v.trust_level, "respect": v.respect_level} for k,v in profile.relationships.items()})

    try:
        delta = chain.invoke({
            "current_mood": profile.current_mood,
            "values": values_json,
            "relationship": rel_json,
            "user_input": user_input,
            "memory_context": memory_context
        })
        
        # Debug Logging
        print(f"Delta Output: {delta}", flush=True)

        # Update Mood
        if delta.mood_shift:
            new_mood = delta.mood_shift.split("->")[-1].strip()
            profile.current_mood = new_mood

        # Update Values
        frame = state.get("cognitive_frame") or {}
        confidence = frame.get("confidence_level", 0.5)
        for change in delta.values_impacted:
            target_key = next((k for k, v in profile.values.items()
                               if v.name.lower() == change.value_name.lower() or k == change.value_name), None)
            if target_key:
                delta_val = (change.new_score - profile.values[target_key].score) * confidence
                clamped_delta = clamp(delta_val, -0.05, 0.05)
                profile.values[target_key].score = clamp(profile.values[target_key].score + clamped_delta, 0.0, 1.0)
                profile.values[target_key].justification = change.reason

        # Update Relationship with trust damping + memory awareness
        user_id = "User_123"
        if delta.relationship_impact and user_id in profile.relationships:
            user_rel = profile.relationships[user_id]
            raw_change = getattr(delta.relationship_impact, "trust_change", 0.0)
            current_trust = user_rel.trust_level

            if raw_change > 0:
                damping_factor = (100 - current_trust) / 100.0
                linked_mems = frame.get("linked_memories") or []
                if any("betrayal" in m.lower() or "lie" in m.lower() for m in linked_mems):
                    damping_factor *= 0.5
                real_change = raw_change * damping_factor
            else:
                real_change = raw_change * 1.5

            user_rel.trust_level = clamp(current_trust + real_change, 0.0, 100.0)
            user_rel.respect_level = clamp(user_rel.respect_level + getattr(delta.relationship_impact, "respect_change", 0.0), 0.0, 100.0)
            user_rel.latest_impression = delta.relationship_impact.new_impression

        return {
            "profile": profile.model_dump(),
            "subconscious_thought": delta.thought_process
        }

    except Exception as e:
        print(f"Delta Logic Failed: {e}", flush=True)
        return {}

# --- Node 4: Generation ---
def generate_node(state: AgentState):
    """Generates the final response using memory-linked context and enforced cognition."""
    user_input = state['messages'][-1].content
    thought = state['subconscious_thought']

    profile = PsychologicalProfile(**state['profile'])
    memories = [
        MemoryFragment(**m) if isinstance(m, dict) else m
        for m in state.get("memories", [])
    ]

    # Extract cognitive frame
    frame = state.get("cognitive_frame") or {}
    beliefs_held_list = frame.get("beliefs_held", [])
    beliefs_held = ", ".join(beliefs_held_list) if isinstance(beliefs_held_list, list) else str(beliefs_held_list)
    linked_memories = frame.get("linked_memories") or []
    emotion_data = str(frame.get("emotional_state", {}))
    constraints_list = frame.get("behavioral_constraints") or []

    # Map linked memories to full memory info
    linked_mem_details = [
        f"- {m.description} (Emo: {m.emotional_tags}, Cog: {getattr(m, 'cognitive_tags', [])})"
        for m in memories if m.description in linked_memories
    ]
    linked_mem_str = "\n".join(linked_mem_details) or "None"

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

    # Behavioral strategy
    motivational = state.get("motivational", {})
    active_strategy = motivational.get("active_strategy", "neutral")
    cog_load = motivational.get("cognitive_state", {}).get("cognitive_load", 0.0)
    
    # Strategy Override based on Cognitive Load
    if cog_load > 0.7:
        active_strategy = {"fragmented_thoughts": 1.0}

    instruction_lines = []
    if isinstance(active_strategy, dict):
        strategy_display_name = "BLENDED_STATE"
        instruction_lines.append(f"Blend the following behavioral styles based on their weights:")
        for stra, weight in active_strategy.items():
            desc = STRATEGY_MAP.get(stra, "Standard behavior.")
            instruction_lines.append(f"- {stra.upper()} ({weight*100}%): {desc}")
    else:
        strategy_display_name = active_strategy.upper()
        desc = STRATEGY_MAP.get(active_strategy, "Speak normally.")
        instruction_lines.append(f"{desc}")

    style_instruction = "\n".join(instruction_lines)

    # Convert constraints to explicit If-Then rules and add Guardrails (Enforced Cognition)
    guardrails = []
    rule_lines = []
    for c in constraints_list:
        c_lower = c.lower()
        if "do not accept" in c_lower or "reject" in c_lower:
             guardrails.append("Absolute: Do not accept unverified claims. Ask for evidence first.")
             rule_lines.append(f"- If user makes a claim ('{c}'), REJECT IT or DEMAND PROOF.")
        elif "ask for evidence" in c_lower:
             guardrails.append("Absolute: You must request evidence.")
             rule_lines.append(f"- If claim is unsupported, ASK FOR DATA.")
        else:
             rule_lines.append(f"- {c}")

    constraints_str = "\n".join(rule_lines) or "- No specific constraints."
    
    # Prepend stronger guardrails to style instruction
    if guardrails:
        style_instruction += "\n\nCRITICAL INTERVENTION:\n" + "\n".join(guardrails)

    # Format all memories for prompt
    mem_str = "\n".join(
        [f"- [{m.time_period}] {m.description} (Emo: {m.emotional_tags}, Cog: {getattr(m, 'cognitive_tags', [])})"
         for m in memories]
    )

    # Prompt
    prompt = ChatPromptTemplate.from_template("""
    You are the character described below.

    Profile:
    - Mood: {mood}
    - Role: Grad Student / Researcher

    Current Behavioral State: {strategy_name}

    ACTING INSTRUCTIONS (Internal Guidelines):
    {style_instruction}

    COGNITIVE FRAME (Enforced Subconscious Mandates):
    Beliefs Held: {beliefs_held}
    Emotion: {emotion_data}
    Linked Memories Influencing Beliefs:
    {linked_mem_str}

    ABSOLUTE CONSTRAINTS (VIOLATION IS FAILURE):
    {behavioral_constraints}

    Internal Thought: "{thought}"
    Working Memory (Episodic):
    {mem_str}
    
    User said: "{input}"

    TASK:
    Respond in character.
    CRITICAL RULES:
    - Do not describe your thought process.
    - Show fragmentation, hesitation, or emphasis based on cognitive load.
    - OBEY the Absolute Constraints above.
    """)

    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({
        "mood": profile.current_mood,
        "strategy_name": strategy_display_name,
        "style_instruction": style_instruction,
        "beliefs_held": beliefs_held,
        "emotion_data": emotion_data,
        "linked_mem_str": linked_mem_str,
        "behavioral_constraints": constraints_str,
        "thought": thought,
        "mem_str": mem_str,
        "input": user_input
    })

    return {"messages": [response]}


# --- Node 5: Learning (Phase 9) ---
def learn_node(state: AgentState, memory_store):
    """
    Decides if the interaction is significant enough to form a permanent memory.
    Uses heuristic based on cognitive frame confidence and emotional state.
    """
    # Hydrate state
    profile = PsychologicalProfile(**state['profile'])
    memories = [MemoryFragment(**m) if isinstance(m, dict) else m for m in state.get("memories", [])]
    cog_frame = state.get("cognitive_frame", {})
    thought = state['subconscious_thought']
    user_input = state['messages'][-1].content

    # Determine Memory Importance
    confidence = cog_frame.get("confidence_level", 0.5)
    importance = min(max(confidence, 0.1), 1.0)

    # Create Memory Fragment
    from datetime import datetime
    import uuid

    new_mem = MemoryFragment(
        id=str(uuid.uuid4())[:8],
        time_period=datetime.utcnow().isoformat(),
        description=f"Interaction: {user_input} | Thought: {thought}",
        emotional_tags=list(cog_frame.get("emotional_state", {}).keys()),
        cognitive_tags=cog_frame.get("beliefs_held", []),
        importance=importance,
        linked_memories=cog_frame.get("linked_memories", [])
    )

    # Commit Logic
    if new_mem.importance > 0.2:
        memory_store.add_memories([new_mem])
        print(f"📝 [Learning]: Committed new memory (Importance: {importance:.2f})")
        memories.append(new_mem)

    return {
        "memories": [m.model_dump() for m in memories]
    }


def persist_node(state: AgentState, kg=None):
    """
    Handles side-effects: Knowledge Graph updates, profile saves, live state dump.
    """
    try:
        profile = PsychologicalProfile(**state['profile'])
        
        # 1. Update Knowledge Graph (Trust / Interaction)
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
        save_character_profile(profile, "character.json")

        # 3. Dump live_state.json
        import json
        dump_state = {
            "profile": profile.model_dump(),
            "messages": state.get("messages", []),
            "cognitive_frame": state.get("cognitive_frame", {}),
            "memories": state.get("memories", []),
            "subconscious_thought": state.get("subconscious_thought", ""),
            "motivational": state.get("motivational", {})
        }
        with open("live_state.json", "w") as f:
            json.dump(dump_state, f, indent=2)

        return state  # optional: allows downstream nodes to see the persisted state

    except Exception as e:
        print(f"Persistence Logic Failed: {e}")
        return state
