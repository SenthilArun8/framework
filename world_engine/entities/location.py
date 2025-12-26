"""
Location entity - represents places in the world
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple


class Location(BaseModel):
    """A place in the world where characters can be"""
    
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Display name")
    type: str = Field(..., description="city, wilderness, dungeon, etc.")
    
    # Spatial data
    coordinates: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="(latitude, longitude) for map rendering"
    )
    
    # State
    occupants: List[str] = Field(
        default_factory=list,
        description="Character IDs currently at this location"
    )
    active_events: List[str] = Field(
        default_factory=list,
        description="Event IDs happening here"
    )
    
    # Descriptive
    description: str = Field(
        default="",
        description="Rich text description of the location"
    )
    atmosphere: str = Field(
        default="neutral",
        description="peaceful, tense, chaotic, etc."
    )
    
    # Resources/Properties
    resources: Dict[str, int] = Field(
        default_factory=dict,
        description="Available resources (food, water, shelter)"
    )
    faction_control: Optional[str] = Field(
        default=None,
        description="Which faction controls this location"
    )
    
    # Connections
    connected_to: List[str] = Field(
        default_factory=list,
        description="Location IDs that are accessible from here"
    )
    travel_times: Dict[str, int] = Field(
        default_factory=dict,
        description="Travel time in ticks to connected locations"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "ba_sing_se",
                "name": "Ba Sing Se",
                "type": "city",
                "coordinates": (34.0, 108.0),
                "description": "The great walled city of the Earth Kingdom",
                "atmosphere": "tense",
                "faction_control": "earth_kingdom",
                "connected_to": ["omashu", "si_wong_desert"],
                "travel_times": {"omashu": 50, "si_wong_desert": 30}
            }
        }