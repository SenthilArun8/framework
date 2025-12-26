import json
from langchain_core.prompts import ChatPromptTemplate
from src.state import AgentState
from src.schema import PsychologicalProfile, MemoryFragment, PersonalityDelta
from src.llm_client import llm
from src.utils import clamp, log_exception

def delta_node(state: AgentState):
    """
    Updates the psychological profile based on cognitive frame.
    Tracks Delta History.
    """
    user_input = state['messages'][-1].content
    thought = state['subconscious_thought']

    profile = PsychologicalProfile(**state['profile'])
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

        # Update Relationship
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

        # Update Delta History
        delta_history = state.get("delta_history", []) + [delta.model_dump()]
        if len(delta_history) > 10:
            delta_history = delta_history[-10:]

        return {
            "profile": profile.model_dump(),
            "subconscious_thought": delta.thought_process, 
            "delta_history": delta_history
        }

    except Exception as e:
        log_exception("Delta Node", e)
        return {}
