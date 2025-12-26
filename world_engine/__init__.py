"""
Autonomous World Simulation Engine
Built on top of the Living Character AI Framework
"""

__version__ = "0.1.0"

from .core.ticker import WorldTicker
from .core.event_queue import EventQueue
from .core.world_state import WorldState
from .entities.character import WorldCharacter
from .entities.location import Location
from .entities.event import Event, EventType
from .entities.faction import Faction

# Alias for backward compatibility if needed, or just exposition
WorldEvent = Event

__all__ = [
    "WorldTicker",
    "EventQueue",
    "WorldEvent",
    "Event",
    "EventType",
    "WorldState",
    "WorldCharacter",
    "Location",
    "Faction",
]