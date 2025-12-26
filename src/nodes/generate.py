from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.state import AgentState
from src.schema import PsychologicalProfile, MemoryFragment
from src.llm_client import llm
from src.utils import apply_cognitive_load_overrides

def generate_node(state: AgentState):
    """Generates the final response using memory-linked context, enforced cognition, and PLANS."""
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
    
    # Internal Objectives (Proactive)
    planned_actions = state.get("planned_actions", [])
    goal_str = "\n".join([f"- {g}" for g in planned_actions]) or "None"

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
    active_strategy = apply_cognitive_load_overrides(active_strategy, cog_load)

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

    # Guardrails
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
    
    if guardrails:
        style_instruction += "\n\nCRITICAL INTERVENTION:\n" + "\n".join(guardrails)

    # Format memories
    mem_str = "\n".join(
        [f"- [{m.time_period}] {m.description} (Emo: {m.emotional_tags}, Cog: {getattr(m, 'cognitive_tags', [])})"
         for m in memories]
    )

    prompt = ChatPromptTemplate.from_template("""
    You are the character described below.

    Profile:
    - Mood: {mood}
    - Role: Grad Student / Researcher

    Current Behavioral State: {strategy_name}

    ACTING INSTRUCTIONS (Internal Guidelines):
    {style_instruction}

    Internal Objectives (Proactive Goals):
    {goal_str}

    COGNITIVE FRAME (Enforced Subconscious Mandates):
    Beliefs Held: {beliefs_held}
    Emotion: {emotion_data}
    Linked Memories Influencing Beliefs:
    {linked_memories}

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
    - Attempt to further your Internal Objectives.
    """)

    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({
        "mood": profile.current_mood,
        "strategy_name": strategy_display_name,
        "style_instruction": style_instruction,
        "goal_str": goal_str,
        "beliefs_held": beliefs_held,
        "emotion_data": emotion_data,
        "linked_memories": linked_mem_str,
        "behavioral_constraints": constraints_str,
        "thought": thought,
        "mem_str": mem_str,
        "input": user_input
    })

    return {"messages": [response]}
