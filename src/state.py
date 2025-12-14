from typing import Annotated, List, Dict
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from src.schema import PsychologicalProfile, MemoryFragment

class AgentState(TypedDict):
    # The chat history
    messages: Annotated[List[BaseMessage], add_messages]
    
    # The living profile (Mutable)
    profile: dict
    
    # Retrieved memories for the current turn (Immutable)
    memories: list
    
    # Internal thought/plan from the Subconscious node
    subconscious_thought: str # Internal monologue
    motivational: dict        # Serialized MotivationalState (Needs, Emotions)
    old_profile: dict         # Snapshot of profile at start of turn (for delta tracking)
