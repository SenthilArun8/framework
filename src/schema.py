from typing import List, Dict, Optional, Any, Union, Tuple, Literal
from pydantic import BaseModel, Field, field_validator
import json
import os

# --- PART 1: THE ARCHIVE (Immutable Context) ---
# These are chunked and stored in a Vector DB (Chroma/Pinecone).
# They don't change, but "accessing" them depends on the conversation.

class MemoryFragment(BaseModel):
    id: str
    time_period: str  # e.g., "Childhood", "The War", "2023"
    description: str  # The actual event content
    emotional_tags: List[str]  # e.g., ["fear", "abandonment"]
    importance_score: float = Field(..., ge=0, le=1) # 1.0 = Core Trauma
    # Phase 11 additions
    source_entity: str = Field(default="Unknown", description="Who provided this information?")
    certainty_score: float = Field(default=1.0, description="Confidence in truth (0.0-1.0)")

# --- PART 2: THE PSYCHE (Mutable State) ---
# This is the "Living" part that the LLM updates after interactions.

class PersonalityTraits(BaseModel):
    emotional_volatility: float = Field(default=0.5, description="Multiplier for stress/emotion impacts (0.0-2.0)")
    focus_fragility: float = Field(default=0.5, description="Multiplier for cognitive load increase (0.0-2.0)")

class CoreValue(BaseModel):
    name: str # e.g., "Honesty", "Self-Preservation"
    score: float = Field(..., ge=0, le=1)  # 0.0 = Doesn't care, 1.0 = Die for it
    justification: str # Why do they hold this value? (e.g., "Father lied to me")

class RelationshipState(BaseModel):
    user_id: str
    trust_level: float = Field(..., ge=0, le=100)
    respect_level: float = Field(..., ge=0, le=100)
    shared_history_summary: str # Compressed summary of your chats
    latest_impression: Optional[str] = None # The most recent assessment of this user

class PsychologicalProfile(BaseModel):
    # The "Soul" of the character
    name: str = Field(default="Elias", description="Character Name")
    current_mood: str
    emotional_volatility: float # Legacy field (keeping for compatibility, but moving logic to 'traits')
    
    values: Dict[str, CoreValue] # Mutable: These can shift over time
    goals: List[str] # e.g., ["Find out user's name", "Hide my past"]
    
    # The dynamic link to the user
    relationships: Dict[str, RelationshipState] 
    
    # Phase 11: Trait Model
    traits: PersonalityTraits = Field(default_factory=PersonalityTraits)

    # Internal Scratchpad for the System
    last_reflection: Optional[str] = None # The last "thought" the AI had about its growth
    version: str = Field(default="1.0", description="Schema version")

# --- DELTA SCHEMA (Output from Subconscious) ---
class ValueChange(BaseModel):
    value_name: str
    new_score: float # The updated score (e.g., 0.8 -> 0.7)
    reason: str # "User proved that blind obedience leads to failure."

class RelationshipUpdate(BaseModel):
    trust_change: float # e.g., +5.0 or -10.0
    respect_change: float # e.g., +2.0
    new_impression: str # "User seems knowledgeable about medicine."

class PersonalityDelta(BaseModel):
    # If nothing changed, these lists are empty
    mood_shift: Optional[str] = None # e.g., "Defensive -> Contemplative"
    values_impacted: List[ValueChange] = []
    relationship_impact: Optional[RelationshipUpdate] = None
    
    # The "Internal Monologue" that explains the shift
    thought_process: str 

class EmotionalQuery(BaseModel):
    detected_emotions: List[str] # e.g., ["condescension", "authority"]
    entities_of_interest: List[str] # e.g., ["Empire", "General Kael"]
    memory_search_query: str     # e.g., "being belittled by a superior"
    trigger_strength: float      # 0.0 to 1.0

# --- PART 4: EMERGENT MOTIVATIONAL SYSTEM (Phase 7) ---

class CoreNeeds(BaseModel):
    belonging: float       # need for connection
    autonomy: float        # need for self-direction
    security: float        # need for stability, safety
    competence: float      # need to feel effective
    novelty: float         # need for stimulation/interest

class EmotionalState(BaseModel):
    stress: float           # 0 to 1
    arousal: float          # 0 to 1 (energy vs shutdown)
    shame: float            # 0 to 1
    fear: float             # 0 to 1
    longing: float          # 0 to 1 (important for relationships)

class CognitiveState(BaseModel):
    cognitive_load: float       # 0 to 1
    dissociation: float         # 0 to 1
    focus_fragility: float      # Legacy Trait ref

class AttachmentSystem(BaseModel):
    style: Literal["secure", "anxious", "avoidant", "disorganized"]
    activation: float           # 0 to 1 (degree of insecurity triggered)
    protest_tendency: float     # anxious behaviors
    withdrawal_tendency: float  # avoidant behaviors

class CopingStyles(BaseModel):
    avoidance: float
    intellectualization: float
    over_explaining: float
    humor_deflection: float
    aggression: float
    appeasement: float

class InternalConflict(BaseModel):
    name: str
    pressure: float       # how "active" this conflict is
    polarity: Tuple[str, str]  # e.g. ("freedom", "duty")
    importance: float = Field(default=1.0, description="Weight of this conflict (0.0-2.0)")

class MotivationalState(BaseModel):
    needs: CoreNeeds
    emotional_state: EmotionalState
    cognitive_state: CognitiveState
    attachment: AttachmentSystem
    coping: CopingStyles
    conflicts: List[InternalConflict]
    fatigue: float                 # too tired -> fragmented thoughts
    
    # Phase 11: Strategy Blending & Momentum
    active_strategy: Dict[str, float] = Field(default_factory=lambda: {"neutral": 1.0}) # Consistent Dict
    mood_momentum: float = Field(default=0.0, description="Resistance to mood change")
    time_since_last_shift: int = Field(default=0, description="Turns since last major mood shift")

    @field_validator('active_strategy', mode='before')
    @classmethod
    def parse_active_strategy(cls, v):
        if isinstance(v, str):
            return {v: 1.0}
        return v

# --- PERSISTENCE HELPERS ---

def load_character_profile(filepath: str) -> PsychologicalProfile:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"{filepath} not found.")
    with open(filepath, 'r') as f:
        data = json.load(f)
    return PsychologicalProfile(**data)

def save_character_profile(profile: PsychologicalProfile, filepath: str):
    with open(filepath, 'w') as f:
        f.write(profile.model_dump_json(indent=2))
