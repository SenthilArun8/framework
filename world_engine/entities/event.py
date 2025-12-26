"""
Event entity - represents things happening in the world
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum


class EventType(str, Enum):
    """Types of events that can occur"""
    CHARACTER_ACTION = "character_action"
    CHARACTER_TRAVEL = "character_travel"
    CHARACTER_INTERACTION = "character_interaction"
    LOCATION_EVENT = "location_event"
    FACTION_CONFLICT = "faction_conflict"
    ENVIRONMENTAL = "environmental"
    BATTLE = "battle"
    MEETING = "meeting"
    DISCOVERY = "discovery"


class EventStatus(str, Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Event(BaseModel):
    """An event occurring in the world"""
    
    id: str = Field(..., description="Unique identifier")
    type: EventType = Field(..., description="Type of event")
    status: EventStatus = Field(
        default=EventStatus.SCHEDULED,
        description="Current status"
    )
    
    # Temporal
    scheduled_tick: int = Field(..., description="When event should start")
    start_tick: Optional[int] = Field(
        default=None,
        description="When event actually started"
    )
    end_tick: Optional[int] = Field(
        default=None,
        description="When event ended"
    )
    duration_ticks: int = Field(
        default=1,
        description="How many ticks the event lasts"
    )
    
    # Spatial
    location_id: str = Field(..., description="Where the event occurs")
    
    # Participants
    participants: List[str] = Field(
        default_factory=list,
        description="Character IDs involved"
    )
    
    # Content
    title: str = Field(..., description="Short event title")
    description: str = Field(..., description="Detailed description")
    
    # Impact
    impact: Dict[str, Any] = Field(
        default_factory=dict,
        description="What changed as a result"
    )
    consequences: List[str] = Field(
        default_factory=list,
        description="Event IDs that were triggered by this event"
    )
    
    # Metadata
    priority: int = Field(
        default=5,
        description="Lower number = higher priority (0-10)"
    )
    visibility: str = Field(
        default="public",
        description="public, private, secret"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "evt_001",
                "type": "character_interaction",
                "status": "active",
                "scheduled_tick": 100,
                "location_id": "ba_sing_se",
                "participants": ["aang", "katara"],
                "title": "Aang meets Katara in the marketplace",
                "description": "A chance encounter that will change everything",
                "priority": 1
            }
        }