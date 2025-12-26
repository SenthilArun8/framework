"""
WorldCharacter - extends the existing PsychologicalProfile for world simulation
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum
import sys
from pathlib import Path

# Import from existing framework
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.schema import PsychologicalProfile, MotivationalState


class CharacterState(str, Enum):
    """Physical/activity state of character"""
    IDLE = "idle"
    TRAVELING = "traveling"
    IN_CONVERSATION = "in_conversation"
    IN_COMBAT = "in_combat"
    RESTING = "resting"
    WORKING = "working"
    EXPLORING = "exploring"


class WorldCharacter(BaseModel):
    """
    World-level character representation.
    Links to existing PsychologicalProfile for personality/memory.
    """
    
    # Identity
    id: str = Field(..., description="Unique identifier")
    profile_path: str = Field(
        ...,
        description="Path to character.json with PsychologicalProfile"
    )
    
    # Loaded profile (not serialized, loaded at runtime)
    profile: Optional[PsychologicalProfile] = Field(
        default=None,
        exclude=True,
        description="Loaded psychological profile"
    )
    motivational_state: Optional[MotivationalState] = Field(
        default=None,
        exclude=True,
        description="Current motivational state"
    )
    
    # Physical state
    location_id: str = Field(..., description="Current location ID")
    state: CharacterState = Field(
        default=CharacterState.IDLE,
        description="What the character is currently doing"
    )
    
    # Goals & Planning (autonomous)
    active_goals: List[str] = Field(
        default_factory=list,
        description="What the character is trying to achieve"
    )
    current_plan: Optional[str] = Field(
        default=None,
        description="Current action plan"
    )
    destination: Optional[str] = Field(
        default=None,
        description="Where character is heading (if traveling)"
    )
    
    # Interaction state
    interacting_with: List[str] = Field(
        default_factory=list,
        description="Character IDs currently interacting with"
    )
    last_action_tick: int = Field(
        default=0,
        description="When character last did something significant"
    )
    
    # Metadata
    is_active: bool = Field(
        default=True,
        description="Whether character is actively simulated"
    )
    
    def load_profile(self, memory_store, knowledge_graph):
        """Load the character's psychological profile"""
        import json
        with open(self.profile_path, 'r') as f:
            data = json.load(f)
            self.profile = PsychologicalProfile(**data)
        
        # Initialize motivational state if not present
        if not self.motivational_state:
            from src.motivational import DEFAULT_MOTIVATIONAL
            self.motivational_state = DEFAULT_MOTIVATIONAL.copy()
    
    def save_profile(self):
        """Save any changes to the psychological profile"""
        if self.profile:
            import json
            with open(self.profile_path, 'w') as f:
                json.dump(self.profile.dict(), f, indent=2)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "aang",
                "profile_path": "data/characters/aang.json",
                "location_id": "southern_air_temple",
                "state": "exploring",
                "active_goals": ["Master all elements", "Stop the Fire Nation"],
                "is_active": True
            }
        }