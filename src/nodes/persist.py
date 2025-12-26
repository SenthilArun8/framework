from src.state import AgentState
from src.schema import PsychologicalProfile, save_character_profile
import json
from src.utils import log_exception

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

        # 3. Dump live_state.json with EXTENDED Context
        dump_state = {
            "profile": profile.model_dump(),
            "messages": state.get("messages", []),
            "cognitive_frame": state.get("cognitive_frame", {}),
            "memories": state.get("memories", []),
            "subconscious_thought": state.get("subconscious_thought", ""),
            "motivational": state.get("motivational", {}),
            "cognitive_stack": state.get("cognitive_stack", []),
            "delta_history": state.get("delta_history", []),
            "planned_actions": state.get("planned_actions", [])
        }
        with open("live_state.json", "w") as f:
            json.dump(dump_state, f, indent=2)

        return state

    except Exception as e:
        log_exception("Persistence Node", e)
        return state
