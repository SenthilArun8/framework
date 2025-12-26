"""
World State Manager - NOW JUST COORDINATION
No longer the source of truth, just coordinates between epistemic layers
"""
import json
import logging
from typing import Dict, List, Optional, Set
from pathlib import Path

# Import epistemic layers
import sys
sys.path.append(str(Path(__file__).parent.parent))
from world_engine.epistemic.objective_world import ObjectiveWorld
from world_engine.epistemic.information_artifacts import InformationArtifactStore
from world_engine.epistemic.belief_graph import BeliefGraph
from world_engine.epistemic.perception import PerceptionSystem

from ..entities.character import WorldCharacter, CharacterState
from ..entities.location import Location
from ..entities.event import Event, EventStatus
from ..entities.faction import Faction

logger = logging.getLogger(__name__)


class WorldState:
    """
    REFACTORED: Now coordinates between epistemic layers.
    
    This is NO LONGER the source of truth.
    Instead, it's a coordination layer that:
    - Routes updates to the objective world
    - Manages perception and belief formation
    - Provides convenience methods for querying
    """
    
    def __init__(self, data_dir: str = "world_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # ✅ NEW: Epistemic layers
        self.objective_world = ObjectiveWorld(data_dir)
        self.artifact_store = InformationArtifactStore()
        self.belief_graph = BeliefGraph()
        self.perception = PerceptionSystem(self.objective_world, self.artifact_store)
        
        # Entity stores (still needed for non-epistemic data)
        self.characters: Dict[str, WorldCharacter] = {}
        self.locations: Dict[str, Location] = {}
        self.factions: Dict[str, Faction] = {}
        self.events: Dict[str, Event] = {}
        
        # Indices
        self._location_to_characters: Dict[str, Set[str]] = {}
        self._faction_to_members: Dict[str, Set[str]] = {}
        
        # Metadata
        self.current_tick = 0
        self.world_name = "Unnamed World"
        
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load world state from JSON files"""
        logger.info("📂 Loading world state from disk...")
        
        # Load world metadata
        state_file = self.data_dir / "world_state.json"
        if state_file.exists():
            with open(state_file, 'r') as f:
                data = json.load(f)
                self.current_tick = data.get("current_tick", 0)
                self.world_name = data.get("world_name", "Unnamed World")
        
        # Load locations
        locations_file = self.data_dir / "locations.json"
        if locations_file.exists():
            with open(locations_file, 'r') as f:
                locations_data = json.load(f)
                for loc_data in locations_data:
                    location = Location(**loc_data)
                    self.locations[location.id] = location
            logger.info(f"  ✓ Loaded {len(self.locations)} locations")
        
        # Load factions
        factions_file = self.data_dir / "factions.json"
        if factions_file.exists():
            with open(factions_file, 'r') as f:
                factions_data = json.load(f)
                for faction_data in factions_data:
                    faction = Faction(**faction_data)
                    self.factions[faction.id] = faction
            logger.info(f"  ✓ Loaded {len(self.factions)} factions")
        
        # Load characters (references to character.json files)
        characters_file = self.data_dir / "characters.json"
        if characters_file.exists():
            with open(characters_file, 'r') as f:
                characters_data = json.load(f)
                for char_data in characters_data:
                    character = WorldCharacter(**char_data)
                    self.characters[character.id] = character
            logger.info(f"  ✓ Loaded {len(self.characters)} characters")
        
        # Build indices
        self._rebuild_indices()
        
        logger.info(f"✅ World '{self.world_name}' loaded at tick {self.current_tick}")
    
    # ==================== Character Management (UPDATED) ====================
    
    def move_character(
    self,
    character_id: str,
    new_location_id: str,
    current_tick: int  # ✅ ADD THIS PARAMETER
) -> bool:
        """
        Move a character to a new location.
        NOW: Records to objective world AND generates information artifacts.
        """
        character = self.get_character(character_id)
        if not character:
            logger.error(f"Cannot move non-existent character: {character_id}")
            return False
        
        if new_location_id not in self.locations:
            logger.error(f"Cannot move to non-existent location: {new_location_id}")
            return False
        
        old_location = character.location_id
        
        # ✅ Record to OBJECTIVE WORLD
        observers = self._get_characters_at_location(old_location) | \
                self._get_characters_at_location(new_location_id)
        observers.discard(character_id)  # Don't include self
        
        fact = self.objective_world.record_fact(
            tick=current_tick,
            fact_type="character_moved",
            subject=character_id,
            data={
                "from": old_location,
                "destination": new_location_id
            },
            observers=observers
        )
        
        # ✅ Generate information artifacts based on who was present
        # Character themselves gets direct observation
        self_artifact = self.perception.process_direct_observation(fact, character_id)
        self.belief_graph.form_belief(
            character_id,
            self_artifact,
            current_tick,
            trust_in_source=1.0,  # Trust own observation
            base_skepticism=0.0
        )
        
        # Other observers get observations too
        for observer_id in observers:
            observer_artifact = self.perception.process_direct_observation(fact, observer_id)
            
            # Observer forms belief
            observer = self.get_character(observer_id)
            if observer and observer.profile:
                # Use character's actual skepticism (placeholder for now)
                base_skepticism = 0.2
            else:
                base_skepticism = 0.3
            
            self.belief_graph.form_belief(
                observer_id,
                observer_artifact,
                current_tick,
                trust_in_source=1.0,  # Direct observation
                base_skepticism=base_skepticism
            )
        
        # Update traditional state (for backward compatibility)
        character.location_id = new_location_id
        character.state = CharacterState.IDLE
        character.destination = None
        
        # Update indices
        if old_location in self._location_to_characters:
            self._location_to_characters[old_location].discard(character_id)
        if old_location in self.locations:
            old_loc = self.locations[old_location]
            if character_id in old_loc.occupants:
                old_loc.occupants.remove(character_id)
        
        if new_location_id not in self._location_to_characters:
            self._location_to_characters[new_location_id] = set()
        self._location_to_characters[new_location_id].add(character_id)
        
        new_loc = self.locations[new_location_id]
        if character_id not in new_loc.occupants:
            new_loc.occupants.append(character_id)
        
        logger.info(f"🚶 {character_id} moved: {old_location} → {new_location_id}")
        return True
    
    def _get_characters_at_location(self, location_id: str) -> Set[str]:
        """Helper to get character IDs at location"""
        return self._location_to_characters.get(location_id, set()).copy()
    
    # ==================== Querying (UPDATED) ====================
    
    def get_character_believed_location(
        self,
        character_id: str,
        about_character: str,
        current_tick: int
    ) -> Optional[str]:
        """
        Get where a character BELIEVES another character is.
        This may differ from objective reality!
        
        Args:
            character_id: Who is asking
            about_character: Who they're asking about
            current_tick: Current tick
            
        Returns:
            Location ID or None if they don't know
        """
        # Get artifacts character knows about the other character's location
        artifacts = self.artifact_store.get_artifacts_known_by(
            character_id,
            about_subject=about_character
        )
        
        if not artifacts:
            # They don't know anything
            return None
        
        # Find most recent movement artifact they believe
        location_artifacts = [
            a for a in artifacts
            if a.data.get("destination")
        ]
        
        if not location_artifacts:
            return None
        
        # Get the one they most strongly believe
        best_artifact = None
        best_confidence = 0.0
        
        for artifact in location_artifacts:
            belief = self.belief_graph.get_belief(character_id, artifact.artifact_id)
            if belief and belief.confidence > best_confidence:
                best_artifact = artifact
                best_confidence = belief.confidence
        
        if best_artifact:
            return best_artifact.data.get("destination")
        
        return None
    
    def get_character_objective_location(self, character_id: str) -> Optional[str]:
        """
        Get where a character ACTUALLY is (engine truth).
        Only use this for engine mechanics, not for character reasoning.
        """
        return self.objective_world.get_character_location_at_tick(
            character_id,
            self.current_tick
        )
    
    # ==================== Persistence ====================
    
    def save_to_disk(self) -> None:
        """Save world state to JSON files"""
        logger.info("💾 Saving world state to disk...")
        
        # Save metadata
        state_file = self.data_dir / "world_state.json"
        with open(state_file, 'w') as f:
            json.dump({
                "world_name": self.world_name,
                "current_tick": self.current_tick,
            }, f, indent=2)
        
        # Save epistemic layers
        self.objective_world.save_to_disk()
        
        # Save entities (unchanged)
        locations_file = self.data_dir / "locations.json"
        with open(locations_file, 'w') as f:
            json.dump(
                [loc.dict() for loc in self.locations.values()],
                f,
                indent=2
            )
        
        factions_file = self.data_dir / "factions.json"
        with open(factions_file, 'w') as f:
            json.dump(
                [faction.dict() for faction in self.factions.values()],
                f,
                indent=2
            )
        
        characters_file = self.data_dir / "characters.json"
        with open(characters_file, 'w') as f:
            json.dump(
                [char.dict() for char in self.characters.values()],
                f,
                indent=2
            )
        
        logger.info("✅ World state saved")
    
    def get_stats(self) -> dict:
        """Get world statistics"""
        return {
            "world_name": self.world_name,
            "current_tick": self.current_tick,
            "characters": {
                "total": len(self.characters),
                "active": len(self.get_active_characters())
            },
            "locations": len(self.locations),
            "factions": len(self.factions),
            "events": {
                "total": len(self.events),
                "active": len([e for e in self.events.values() 
                              if e.status == EventStatus.ACTIVE])
            },
            "epistemic": {
                "objective_facts": self.objective_world.get_stats()["total_facts"],
                "information_artifacts": len(self.artifact_store.artifacts),
            }
        }
    
    # ==================== Character Management ====================
    
    def add_character(self, character: WorldCharacter) -> None:
        """Add a character to the world"""
        self.characters[character.id] = character
        
        # Update location index
        if character.location_id not in self._location_to_characters:
            self._location_to_characters[character.location_id] = set()
            self._location_to_characters[character.location_id].add(character.id)
        
        # ✅ FIX: Also add to location's occupants list
        location = self.get_location(character.location_id)
        if location and character.id not in location.occupants:
            location.occupants.append(character.id)
        
        logger.info(f"➕ Added character: {character.id} at {character.location_id}")
    
    def get_character(self, character_id: str) -> Optional[WorldCharacter]:
        """Get character by ID"""
        return self.characters.get(character_id)
    
    # def move_character(self, character_id: str, new_location_id: str) -> bool:
    #     """
    #     Move a character to a new location.
    #     Updates all relevant indices.
    #     """
    #     character = self.get_character(character_id)
    #     if not character:
    #         logger.error(f"Cannot move non-existent character: {character_id}")
    #         return False
    
    #     if new_location_id not in self.locations:
    #         logger.error(f"Cannot move to non-existent location: {new_location_id}")
    #         return False
    
    #     old_location = character.location_id
    
    #     # Update character
    #     character.location_id = new_location_id
    #     character.state = CharacterState.IDLE
    #     character.destination = None
    
    #     # Update old location
    #     if old_location in self._location_to_characters:
    #         self._location_to_characters[old_location].discard(character_id)
    #     if old_location in self.locations:
    #         old_loc = self.locations[old_location]
    #         if character_id in old_loc.occupants:  # ✅ FIX: Check before removing
    #             old_loc.occupants.remove(character_id)
    
    #     # Update new location
    #     if new_location_id not in self._location_to_characters:
    #         self._location_to_characters[new_location_id] = set()
    #     self._location_to_characters[new_location_id].add(character_id)
    
    #     new_loc = self.locations[new_location_id]
    #     if character_id not in new_loc.occupants:  # ✅ FIX: Avoid duplicates
    #         new_loc.occupants.append(character_id)
    
    #     logger.info(f"🚶 {character_id} moved: {old_location} → {new_location_id}")
    #     return True
    
    def get_characters_at_location(self, location_id: str) -> List[WorldCharacter]:
        """Get all characters at a specific location"""
        char_ids = self._location_to_characters.get(location_id, set())
        return [self.characters[cid] for cid in char_ids if cid in self.characters]
    
    def get_nearby_characters(
        self, 
        character_id: str, 
        include_self: bool = False
    ) -> List[WorldCharacter]:
        """Get all characters at the same location as this character"""
        character = self.get_character(character_id)
        if not character:
            return []
        
        nearby = self.get_characters_at_location(character.location_id)
        
        if not include_self:
            nearby = [c for c in nearby if c.id != character_id]
        
        return nearby
    
    # ==================== Location Management ====================
    
    def add_location(self, location: Location) -> None:
        """Add a location to the world"""
        self.locations[location.id] = location
        self._location_to_characters[location.id] = set()
        logger.info(f"➕ Added location: {location.name} ({location.id})")
    
    def get_location(self, location_id: str) -> Optional[Location]:
        """Get location by ID"""
        return self.locations.get(location_id)
    
    def get_connected_locations(self, location_id: str) -> List[Location]:
        """Get all locations connected to this one"""
        location = self.get_location(location_id)
        if not location:
            return []
        
        return [
            self.locations[loc_id]
            for loc_id in location.connected_to
            if loc_id in self.locations
        ]
    
    # ==================== Faction Management ====================
    
    def add_faction(self, faction: Faction) -> None:
        """Add a faction to the world"""
        self.factions[faction.id] = faction
        self._faction_to_members[faction.id] = set(faction.members)
        logger.info(f"➕ Added faction: {faction.name} ({faction.id})")
    
    def get_faction(self, faction_id: str) -> Optional[Faction]:
        """Get faction by ID"""
        return self.factions.get(faction_id)
    
    def get_faction_members(self, faction_id: str) -> List[WorldCharacter]:
        """Get all character members of a faction"""
        member_ids = self._faction_to_members.get(faction_id, set())
        return [self.characters[cid] for cid in member_ids if cid in self.characters]
    
    # ==================== Event Management ====================
    
    def add_event(self, event: Event) -> None:
        """Add an event to the world"""
        self.events[event.id] = event
        
        # Add to location's active events if not completed
        if event.status != EventStatus.COMPLETED:
            location = self.get_location(event.location_id)
            if location and event.id not in location.active_events:
                location.active_events.append(event.id)
    
    def get_event(self, event_id: str) -> Optional[Event]:
        """Get event by ID"""
        return self.events.get(event_id)
    
    def get_events_at_location(self, location_id: str) -> List[Event]:
        """Get all events at a location"""
        location = self.get_location(location_id)
        if not location:
            return []
        
        return [
            self.events[event_id]
            for event_id in location.active_events
            if event_id in self.events
        ]
    
    def complete_event(self, event_id: str) -> None:
        """Mark an event as completed and remove from location"""
        event = self.get_event(event_id)
        if not event:
            return
        
        event.status = EventStatus.COMPLETED
        
        # Remove from location's active events
        location = self.get_location(event.location_id)
        if location and event_id in location.active_events:
            location.active_events.remove(event_id)
    
    # ==================== Query Methods ====================
    
    def get_active_characters(self) -> List[WorldCharacter]:
        """Get all characters that are actively simulated"""
        return [char for char in self.characters.values() if char.is_active]
    
    def get_all_locations(self) -> List[Location]:
        """Get all locations"""
        return list(self.locations.values())
    
    def get_all_factions(self) -> List[Faction]:
        """Get all factions"""
        return list(self.factions.values())
    
    # ==================== Internal Methods ====================
    
    def _rebuild_indices(self) -> None:
        """Rebuild all indices from scratch"""
        logger.info("🔄 Rebuilding indices...")
        
        # Location -> Characters
        self._location_to_characters.clear()
        for char in self.characters.values():
            if char.location_id not in self._location_to_characters:
                self._location_to_characters[char.location_id] = set()
            self._location_to_characters[char.location_id].add(char.id)
        
        # Faction -> Members
        self._faction_to_members.clear()
        for faction in self.factions.values():
            self._faction_to_members[faction.id] = set(faction.members)
        
        logger.info("  ✓ Indices rebuilt")
    
    # ==================== Statistics ====================
    
    def get_stats(self) -> dict:
        """Get world statistics"""
        return {
            "world_name": self.world_name,
            "current_tick": self.current_tick,
            "characters": {
                "total": len(self.characters),
                "active": len(self.get_active_characters())
            },
            "locations": len(self.locations),
            "factions": len(self.factions),
            "events": {
                "total": len(self.events),
                "active": len([e for e in self.events.values() 
                              if e.status == EventStatus.ACTIVE])
            }
        }