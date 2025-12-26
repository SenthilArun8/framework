"""
Enhanced Narrative Director - Complete Version

Orchestrates compelling drama while respecting epistemic constraints.
Integrates drama analysis, tension management, and story arc tracking.
"""
import json
import logging
import random
from typing import List, Dict, Any, Optional

from .prompts import WORLD_EVENT_GENERATION_PROMPT
from ..entities.event import Event, EventType
from src.llm_client import get_llm

from world_engine.epistemic.constraints import (
    DirectorConstraint,
    DirectorConstraintViolation,
    EpistemicLayer,
    validate_director_observation,
    validate_director_action
)
from world_engine.epistemic.information_artifacts import (
    InformationArtifact,
    ArtifactType,
    ReliabilityLevel
)

# ✅ NEW: Import Ai components
from .drama_analyzer import DramaAnalyzer
from .tension_manager import TensionManager
from .story_arc_tracker import StoryArcTracker

logger = logging.getLogger(__name__)


class NarrativeDirector:
    """
    Enhanced Narrative Director with sophisticated drama creation.
    
    CRITICAL CONSTRAINT:
    - May OBSERVE Layer 1 (Objective World) and Layer 3 (Belief Graph)
    - May ACT ONLY on Layer 2 (Information Artifacts)
    - May NEVER directly modify Layer 4 (Character Minds)
    
    CAPABILITIES:
    - Drama analysis and opportunity detection
    - Tension curve management
    - Story arc tracking
    - Information catalyst creation
    """
    
    def __init__(self):
        self.llm = get_llm()
        
        # ✅ Components
        self.drama_analyzer = DramaAnalyzer()
        self.tension_manager = TensionManager()
        self.story_arc_tracker = StoryArcTracker()
        
        # Modulation parameters
        self.rumor_spread_multiplier = 1.0
        self.skepticism_modifier = 1.0
        self.information_delay_modifier = 1.0
        
        # Statistics
        self.catalysts_created = 0
        self.opportunities_identified = 0
        
        # Legacy attributes (synced with tension manager)
        self.recent_events = []
        self.stagnant_threshold = 20
    
    @property
    def tension_level(self) -> float:
        """Get current tension from manager"""
        return self.tension_manager.current_tension
    
    @tension_level.setter
    def tension_level(self, value):
        """Set tension in manager"""
        self.tension_manager.current_tension = value
        
    # ==================== ENHANCED METHODS ====================
    
    async def process_tick(
        self,
        world_state,
        current_tick: int
    ) -> Dict[str, Any]:
        """
        Main director processing for this tick.
        Called by world engine each tick.
        
        Returns:
            Summary of director actions
        """
        summary = {
            "opportunities_found": 0,
            "catalysts_created": 0,
            "tension": self.tension_level
        }
        
        try:
            # 1. Update Tension based on world state
            active_events = [
                {"id": e.id, "type": e.type.name.lower()} 
                for e in world_state.events.values() 
                if e.status.name == "ACTIVE"
            ]
            self.tension_manager.update_tension(current_tick, active_events, world_state)
            
            # 2. Find dramatic opportunities
            opportunities = await self.identify_dramatic_opportunities(
                world_state,
                current_tick
            )
            summary["opportunities_found"] = len(opportunities)
            self.opportunities_identified += len(opportunities)
            
            # 3. Decide whether to intervene
            should_intervene = self._should_intervene(opportunities)
            
            if should_intervene and opportunities:
                # 4. Select best opportunity
                best_opportunity = opportunities[0]  # Already sorted by score
                
                # 5. Create catalyst
                catalyst = await self.create_information_catalyst(
                    best_opportunity,
                    world_state,
                    current_tick
                )
                
                if catalyst:
                    summary["catalysts_created"] = 1
                    self.catalysts_created += 1
                    
                    # Track arc impact
                    if "arc_id" in best_opportunity:
                        self.story_arc_tracker.update_arc(
                            best_opportunity["arc_id"],
                            current_tick,
                            f"Catalyst created: {best_opportunity['type']}"
                        )
            
            # 4. Active Rumor Spreading (Hand of Fate)
            if self.rumor_spread_multiplier > 1.0:
                self._spread_active_rumors(world_state)

            # Log if action taken
            if summary["catalysts_created"] > 0:
                logger.info(
                    f"🎬 Director: {summary['catalysts_created']} catalyst, "
                    f"tension: {summary['tension']:.1f}"
                )
            
        except DirectorConstraintViolation as e:
            logger.error(f"❌ Constraint violation: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in director processing: {e}", exc_info=True)
        
        return summary
    
    def _should_intervene(self, opportunities: List[Dict[str, Any]]) -> bool:
        """Decide whether director should intervene this tick"""
        if not opportunities:
            return False
        
        # High-score opportunities warrant intervention
        best_score = opportunities[0].get("drama_potential", 0)
        if best_score >= 0.6:
            return True
        
        # Check tension manager
        if self.tension_manager.should_escalate():
            return True
        
        # Random chance for variety (5%)
        if random.random() < 0.05:
            return True
        
        return False
    
    def _spread_active_rumors(self, world_state):
        """
        Actively spread rumors based on multiplier.
        Simulates word-of-mouth amplified by director.
        """
        import random
        
        spread_chance = 0.1 * self.rumor_spread_multiplier
        
        for artifact in world_state.artifact_store.artifacts.values():
            if artifact.artifact_type == ArtifactType.RUMOR:
                # Find potential new hearers (people at same location as knowers)
                knowers = list(artifact.known_by)
                potential_hearers = set()
                
                for knower_id in knowers:
                    # Get knower's location (Objective Layer - allowed to observe)
                    loc_id = world_state.get_character_objective_location(knower_id)
                    if loc_id:
                        location = world_state.locations.get(loc_id)
                        if location:
                            for occupant in location.occupants:
                                if occupant not in artifact.known_by:
                                    potential_hearers.add(occupant)
                
                # Spread to them
                for hearer in potential_hearers:
                    if random.random() < spread_chance:
                        artifact.known_by.add(hearer)
                        logger.info(f"🗣️ Rumor spread to {hearer}: {artifact.claim}")

    # ==================== OBSERVATION & ANALYSIS ====================
    
    async def identify_dramatic_opportunities(
        self,
        world_state,
        current_tick: int
    ) -> List[Dict[str, Any]]:
        """
        Observe epistemic state and identify opportunities via DramaAnalyzer.
        """
        # Use the specialized analyzer
        opportunities = self.drama_analyzer.analyze_world(world_state, current_tick)
        
        # Convert objects to dicts for internal processing
        opp_dicts = []
        for opp in opportunities:
            opp_dicts.append({
                "type": "belief_reality_gap" if opp.drama_type.name == "IRONY" else "generic_drama",
                "drama_potential": opp.score,
                "character": opp.characters_involved[0] if opp.characters_involved else "unknown",
                "about": opp.characters_involved[1] if len(opp.characters_involved) > 1 else "",
                "believed": opp.belief_data.get("believed", ""),
                "actual": opp.belief_data.get("actual", ""),
                "intensity": opp.intensity,
                "urgency": opp.urgency,
                # Add location for meeting ops
                "location": opp.location_id
            })
            
        return opp_dicts

    # ==================== ACTIONS (Layer 2) ====================
    
    async def create_information_catalyst(
        self,
        opportunity: Dict[str, Any],
        world_state,
        current_tick: int
    ) -> Optional[InformationArtifact]:
        """Create an information artifact to catalyze drama"""
        try:
            if opportunity["type"] == "belief_reality_gap":
                return await self._create_deceptive_artifact(
                    opportunity, world_state, current_tick
                )
            elif opportunity["type"] == "belief_contradiction":
                return await self._create_meeting_opportunity(
                    opportunity, world_state, current_tick
                )
            elif opportunity["type"] == "false_belief_cascade":
                await self._amplify_rumor_spread(
                    opportunity, world_state, current_tick
                )
                return None
            
            return None
            
        except DirectorConstraintViolation as e:
            logger.error(f"❌ Catalyst creation violated constraints: {e}")
            raise

    @validate_director_action(EpistemicLayer.INFORMATION_ARTIFACTS, "create_message")
    def _create_message_artifact(
        self,
        world_state,
        subject: str,
        claim: str,
        data: dict,
        source: str,
        recipient: str,
        reliability: ReliabilityLevel,
        current_tick: int
    ) -> InformationArtifact:
        """Create message artifact (Layer 2) - ALLOWED"""
        artifact = world_state.artifact_store.create_artifact(
            tick=current_tick,
            artifact_type=ArtifactType.MESSAGE,
            subject=subject,
            claim=claim,
            data=data,
            source=source,
            reliability=reliability,
            known_by={recipient}
        )
        logger.info(f"📜 Director created message for {recipient}: {claim}")
        return artifact

    async def _create_deceptive_artifact(
        self,
        opportunity: Dict[str, Any],
        world_state,
        current_tick: int
    ) -> InformationArtifact:
        """Create a false information artifact"""
        artifact = self._create_message_artifact(
            world_state=world_state,
            subject=opportunity["about"],
            claim=f"{opportunity['about']} is at {opportunity['believed']}",
            data={
                "location": opportunity["believed"],
                "forged": True,
                "true_location": opportunity["actual"]
            },
            source="unknown",
            recipient=opportunity["character"],
            reliability=ReliabilityLevel.CONFIDENT,
            current_tick=current_tick
        )
        return artifact

    async def _create_meeting_opportunity(
        self,
        opportunity: Dict[str, Any],
        world_state,
        current_tick: int
    ) -> Optional[InformationArtifact]:
        """Create artifact encouraging characters to meet"""
        # Create a message "inviting" them to a location
        target_char = opportunity["character"]
        meeting_loc = opportunity.get("location", "central_hub")
        
        artifact = self._create_message_artifact(
            world_state=world_state,
            subject="Meeting",
            claim=f"You are requested at {meeting_loc}",
            data={
                "location": meeting_loc,
                "urgency": "high",
                "purpose": "important_discussion"
            },
            source="Unknown Friend",
            recipient=target_char,
            reliability=ReliabilityLevel.PROBABLE,
            current_tick=current_tick
        )
        
        logger.info(f"🤝 Meeting invitation sent to {target_char} for {meeting_loc}")
        return artifact
    
    async def _amplify_rumor_spread(
        self,
        opportunity: Dict[str, Any],
        world_state,
        current_tick: int
    ) -> None:
        """Increase rumor transmission rate"""
        self.rumor_spread_multiplier = 2.5
        self.skepticism_modifier = 0.6
        
        logger.info(
            f"📢 Rumor amplification activated: spread {self.rumor_spread_multiplier}x"
        )

    # ==================== STATS ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get detailed director statistics"""
        return {
            "catalysts_created": self.catalysts_created,
            "opportunities_identified": self.opportunities_identified,
            "tension": self.tension_manager.get_stats(),
            "story_arcs": self.story_arc_tracker.get_stats()
        }

    # ==================== LEGACY (Compat) ====================
    
    async def should_generate_event(self, world_state, current_tick: int) -> bool:
        return False  # Handled by process_tick now
    
    async def generate_world_event(self, world_state, current_tick: int) -> Optional[Event]:
        return None