import json
from langchain_core.prompts import ChatPromptTemplate
from src.state import AgentState
from src.schema import PsychologicalProfile, MemoryFragment, CognitiveFrame
from src.llm_client import llm
from src.utils import log_exception

def subconscious_node(state: AgentState):
    """
    Reflects on the input before speaking.
    Maintains a Cognitive Stack of recent frames.
    """
    # Hydrate objects
    profile = PsychologicalProfile(**state['profile'])
    memories = [MemoryFragment(**m) if isinstance(m, dict) else m for m in state['memories']]
    
    if state['messages']:
        user_input = state['messages'][-1].content
    else:
        user_input = "[INTERNAL REFLECTION TRIGGERED]"

    # Cognitive Load Filtering
    motivational = state.get("motivational", {})
    cog_load = motivational.get("cognitive_state", {}).get("cognitive_load", 0.0)
    
    if cog_load > 0.7:
        memories = memories[:1]
        context_instruction = "Your mind is racing. Fragmented thoughts only."
    else:
        context_instruction = "Use your inner voice. Reflect deeply."

    # Memory Chaining from Cognitive Stack
    stack = state.get("cognitive_stack", [])
    linked_memories_set = set()
    for past_frame in stack[-3:]: # Look at last 3 frames
        linked_memories_set.update(past_frame.get("linked_memories", []))
    
    mem_str = "\n".join([
        f"- [{m.time_period}] {m.description} (Tags: {m.emotional_tags}, Cognitive: {getattr(m, 'cognitive_tags', [])})"
        for m in memories
    ])

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
        
        # Merge previous linked memories
        current_linked = set(frame.linked_memories)
        current_linked.update(linked_memories_set)
        frame.linked_memories = list(current_linked)

        thought_str = json.dumps(frame.model_dump(), indent=2)

        # Update Stack
        new_stack = stack + [frame.model_dump()]
        if len(new_stack) > 10:
            new_stack = new_stack[-10:]

        return {
            "cognitive_frame": frame.model_dump(),
            "subconscious_thought": thought_str,
            "cognitive_stack": new_stack
        }

    except Exception as e:
        log_exception("Subconscious Node", e)
        return {"subconscious_thought": "I am processing...", "cognitive_frame": {}}
