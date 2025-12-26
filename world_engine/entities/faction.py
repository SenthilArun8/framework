"""
Faction entity - represents groups, nations, organizations
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum


class FactionType(str, Enum):
    """Types of factions"""
    NATION = "nation"
    ORGANIZATION = "organization"
    TRIBE = "tribe"
    GUILD = "guild"
    CULT = "cult"
    FAMILY = "family"


class FactionRelation(str, Enum):
    """How factions relate to each other"""
    ALLIED = "allied"
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    SUSPICIOUS = "suspicious"
    HOSTILE = "hostile"
    AT_WAR = "at_war"


class Faction(BaseModel):
    """A group with shared goals and identity"""
    
    # Identity
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Display name")
    type: FactionType = Field(..., description="Type of faction")
    
    # Description
    description: str = Field(
        default="",
        description="Rich text description"
    )
    ideology: str = Field(
        default="",
        description="Core beliefs and values"
    )
    
    # Power & Resources
    power_level: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Overall influence/strength (0-100)"
    )
    resources: Dict[str, int] = Field(
        default_factory=dict,
        description="Wealth, military, political capital, etc."
    )
    
    # Territory
    controlled_locations: List[str] = Field(
        default_factory=list,
        description="Location IDs under faction control"
    )
    
    # Members
    members: List[str] = Field(
        default_factory=list,
        description="Character IDs who are members"
    )
    leader_id: Optional[str] = Field(
        default=None,
        description="Character ID of current leader"
    )
    
    # Relations
    relations: Dict[str, FactionRelation] = Field(
        default_factory=dict,
        description="faction_id -> relation status"
    )
    
    # Goals
    goals: List[str] = Field(
        default_factory=list,
        description="What the faction is trying to achieve"
    )
    
    # State
    is_active: bool = Field(
        default=True,
        description="Whether faction still exists"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "fire_nation",
                "name": "Fire Nation",
                "type": "nation",
                "description": "Aggressive expansionist empire",
                "ideology": "Domination through superior firepower",
                "power_level": 85.0,
                "controlled_locations": ["fire_capital", "colonies"],
                "leader_id": "fire_lord_ozai",
                "relations": {
                    "earth_kingdom": "at_war",
                    "water_tribes": "hostile"
                },
                "goals": ["Conquer the world", "Eliminate the Avatar"]
            }
        }