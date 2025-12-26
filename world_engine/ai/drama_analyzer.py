"""
Drama Analyzer - Evaluates dramatic potential of situations

Identifies opportunities for compelling narratives based on:
- Belief-reality gaps
- Character relationships
- Value conflicts
- Information asymmetry
"""
import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DramaType(str, Enum):
    """Types of dramatic situations"""
    DECEPTION = "deception"              # Someone is being misled
    BETRAYAL = "betrayal"                # Trust violation
    REVELATION = "revelation"            # Hidden truth exposed
    DILEMMA = "dilemma"                  # Conflicting values/goals
    SUSPENSE = "suspense"                # Uncertain outcome
    IRONY = "irony"                      # Audience knows, character doesn't
    SACRIFICE = "sacrifice"              # Loss for greater good
    DISCOVERY = "discovery"              # New information changes everything


@dataclass
class DramaticOpportunity:
    """A situation with narrative potential"""
    drama_type: DramaType
    intensity: float  # 0.0-1.0
    urgency: float    # 0.0-1.0 (how soon to act)
    
    # Key elements
    characters_involved: List[str]
    location_id: str
    
    # The gap/conflict/situation
    situation: str
    dramatic_question: str  # What's at stake?
    
    # Supporting data
    belief_data: Dict[str, Any]
    relationship_data: Dict[str, Any]
    
    # Potential catalysts
    suggested_catalysts: List[Dict[str, Any]]
    
    def __post_init__(self):
        self.score = self._calculate_score()
    
    def _calculate_score(self) -> float:
        """Overall dramatic score for prioritization"""
        return (self.intensity * 0.6 + self.urgency * 0.4)


class DramaAnalyzer:
    """
    Analyzes world state to identify dramatic opportunities.
    
    Uses epistemic layers to find compelling situations:
    - Belief-reality gaps (dramatic irony)
    - Information asymmetry (suspense)
    - Value conflicts (dilemmas)
    - Relationship tensions (betrayal potential)
    """
    
    def __init__(self):
        self.minimum_drama_threshold = 0.3
    
    def analyze_world(
        self,
        world_state,
        current_tick: int
    ) -> List[DramaticOpportunity]:
        """
        Comprehensive analysis of world for dramatic potential.
        
        Returns:
            List of dramatic opportunities, sorted by score
        """
        opportunities = []
        
        # 1. Analyze belief-reality gaps
        opportunities.extend(
            self._analyze_belief_gaps(world_state, current_tick)
        )
        
        # 2. Analyze relationship tensions
        opportunities.extend(
            self._analyze_relationships(world_state, current_tick)
        )
        
        # 3. Analyze information asymmetry
        opportunities.extend(
            self._analyze_information_asymmetry(world_state, current_tick)
        )
        
        # 4. Analyze value conflicts
        opportunities.extend(
            self._analyze_value_conflicts(world_state, current_tick)
        )
        
        # 5. Analyze proximity opportunities
        opportunities.extend(
            self._analyze_proximity(world_state, current_tick)
        )
        
        # Filter and sort
        opportunities = [
            opp for opp in opportunities
            if opp.score >= self.minimum_drama_threshold
        ]
        opportunities.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(
            f"🎭 Drama analysis found {len(opportunities)} opportunities "
            f"(threshold: {self.minimum_drama_threshold})"
        )
        
        return opportunities
    
    def _analyze_belief_gaps(
        self,
        world_state,
        current_tick: int
    ) -> List[DramaticOpportunity]:
        """Find dramatic irony: audience knows truth, character doesn't"""
        opportunities = []
        
        for char_id, char in world_state.characters.items():
            for other_id in world_state.characters:
                if char_id == other_id:
                    continue
                
                # What they believe vs reality
                believed_loc = world_state.get_character_believed_location(
                    char_id, other_id, current_tick
                )
                actual_loc = world_state.get_character_objective_location(other_id)
                
                if not believed_loc or not actual_loc:
                    continue
                
                if believed_loc != actual_loc:
                    # Calculate intensity based on how wrong they are
                    intensity = self._calculate_gap_intensity(
                        char_id, other_id, believed_loc, actual_loc, world_state
                    )
                    
                    # Check if this matters to the character
                    urgency = self._calculate_gap_urgency(
                        char_id, other_id, world_state
                    )
                    
                    if intensity > 0.3:  # Only significant gaps
                        opportunities.append(DramaticOpportunity(
                            drama_type=DramaType.IRONY,
                            intensity=intensity,
                            urgency=urgency,
                            characters_involved=[char_id, other_id],
                            location_id=actual_loc,
                            situation=f"{char_id} believes {other_id} is at {believed_loc}, but they're actually at {actual_loc}",
                            dramatic_question=f"What happens when {char_id} discovers the truth?",
                            belief_data={
                                "believer": char_id,
                                "about": other_id,
                                "believed": believed_loc,
                                "actual": actual_loc
                            },
                            relationship_data=self._get_relationship_data(
                                char_id, other_id, world_state
                            ),
                            suggested_catalysts=[
                                {
                                    "type": "revelation_event",
                                    "description": f"Character discovers {other_id}'s true location"
                                },
                                {
                                    "type": "deceptive_message",
                                    "description": f"False confirmation of {other_id} being at {believed_loc}"
                                }
                            ]
                        ))
        
        return opportunities
    
    def _analyze_relationships(
        self,
        world_state,
        current_tick: int
    ) -> List[DramaticOpportunity]:
        """Find relationship-based drama (betrayal, loyalty tests)"""
        opportunities = []
        
        # Check for characters with strong relationships at same location
        for loc_id, location in world_state.locations.items():
            if len(location.occupants) < 2:
                continue
            
            # Check all pairs at this location
            for i, char_a in enumerate(location.occupants):
                for char_b in location.occupants[i+1:]:
                    # Get relationship strength
                    relationship = self._get_relationship_data(
                        char_a, char_b, world_state
                    )
                    
                    if not relationship:
                        continue
                    
                    # High trust + contradictory beliefs = betrayal potential
                    if relationship.get("trust", 0) > 70:
                        contradictions = self._check_belief_contradictions(
                            char_a, char_b, world_state
                        )
                        
                        if contradictions:
                            opportunities.append(DramaticOpportunity(
                                drama_type=DramaType.BETRAYAL,
                                intensity=0.8,
                                urgency=0.6,
                                characters_involved=[char_a, char_b],
                                location_id=loc_id,
                                situation=f"{char_a} and {char_b} have high trust but contradictory beliefs",
                                dramatic_question="Will their friendship survive the truth?",
                                belief_data={"contradictions": contradictions},
                                relationship_data=relationship,
                                suggested_catalysts=[
                                    {
                                        "type": "forced_revelation",
                                        "description": "Event forces them to confront contradiction"
                                    }
                                ]
                            ))
        
        return opportunities
    
    def _analyze_information_asymmetry(
        self,
        world_state,
        current_tick: int
    ) -> List[DramaticOpportunity]:
        """Find cases where some know what others don't"""
        opportunities = []
        
        # Check all artifacts for knowledge gaps
        for artifact_id, artifact in world_state.artifact_store.artifacts.items():
            knowers = artifact.known_by
            
            if len(knowers) < 1:
                continue
            
            # Find characters who should care but don't know
            affected_chars = self._get_affected_characters(artifact, world_state)
            unknowers = [c for c in affected_chars if c not in knowers]
            
            if unknowers:
                intensity = len(unknowers) / max(len(affected_chars), 1)
                
                opportunities.append(DramaticOpportunity(
                    drama_type=DramaType.SUSPENSE,
                    intensity=intensity,
                    urgency=0.5,
                    characters_involved=list(knowers) + unknowers,
                    location_id=artifact.subject,  # Simplified
                    situation=f"{len(knowers)} know something {len(unknowers)} don't",
                    dramatic_question="When will they find out?",
                    belief_data={
                        "artifact_id": artifact_id,
                        "knowers": list(knowers),
                        "unknowers": unknowers
                    },
                    relationship_data={},
                    suggested_catalysts=[
                        {
                            "type": "leak_information",
                            "description": "Information spreads to unknowers"
                        },
                        {
                            "type": "discovery",
                            "description": "Unknowers discover on their own"
                        }
                    ]
                ))
        
        return opportunities
    
    def _analyze_value_conflicts(
        self,
        world_state,
        current_tick: int
    ) -> List[DramaticOpportunity]:
        """Find situations where characters face value dilemmas"""
        opportunities = []
        
        # Check for characters with contradictory goals at same location
        for loc_id, location in world_state.locations.items():
            if len(location.occupants) < 2:
                continue
            
            for i, char_a in enumerate(location.occupants):
                char_a_obj = world_state.get_character(char_a)
                if not char_a_obj:
                    continue
                
                for char_b in location.occupants[i+1:]:
                    char_b_obj = world_state.get_character(char_b)
                    if not char_b_obj:
                        continue
                    
                    # Check for conflicting goals
                    goal_conflict = self._check_goal_conflict(
                        char_a_obj, char_b_obj
                    )
                    
                    if goal_conflict:
                        opportunities.append(DramaticOpportunity(
                            drama_type=DramaType.DILEMMA,
                            intensity=0.7,
                            urgency=0.8,
                            characters_involved=[char_a, char_b],
                            location_id=loc_id,
                            situation=f"{char_a} and {char_b} have conflicting goals",
                            dramatic_question="Who will compromise?",
                            belief_data={},
                            relationship_data=self._get_relationship_data(
                                char_a, char_b, world_state
                            ),
                            suggested_catalysts=[
                                {
                                    "type": "force_choice",
                                    "description": "Situation requires one to give in"
                                }
                            ]
                        ))
        
        return opportunities
    
    def _analyze_proximity(
        self,
        world_state,
        current_tick: int
    ) -> List[DramaticOpportunity]:
        """Find characters who should meet but haven't"""
        opportunities = []
        
        # Look for characters with strong belief connections but separated
        for char_id, beliefs in world_state.belief_graph.beliefs.items():
            for artifact_id, belief in beliefs.items():
                # Find what/who this belief is about
                artifact = world_state.artifact_store.artifacts.get(artifact_id)
                if not artifact:
                    continue
                
                # If it's about another character and belief is strong
                if belief.confidence > 0.7:
                    subject = artifact.subject
                    
                    if subject in world_state.characters:
                        # Are they at different locations?
                        char_loc = world_state.get_character_objective_location(char_id)
                        subject_loc = world_state.get_character_objective_location(subject)
                        
                        if char_loc and subject_loc and char_loc != subject_loc:
                            opportunities.append(DramaticOpportunity(
                                drama_type=DramaType.SUSPENSE,
                                intensity=0.5,
                                urgency=0.4,
                                characters_involved=[char_id, subject],
                                location_id=char_loc,
                                situation=f"{char_id} seeks {subject} but they're apart",
                                dramatic_question="When will they meet?",
                                belief_data={
                                    "seeker": char_id,
                                    "sought": subject,
                                    "seeker_loc": char_loc,
                                    "sought_loc": subject_loc
                                },
                                relationship_data={},
                                suggested_catalysts=[
                                    {
                                        "type": "convergence_event",
                                        "description": "Event brings them to same location"
                                    }
                                ]
                            ))
        
        return opportunities
    
    # ==================== Helper Methods ====================
    
    def _calculate_gap_intensity(
        self,
        believer: str,
        about: str,
        believed: str,
        actual: str,
        world_state
    ) -> float:
        """Calculate how dramatic a belief-reality gap is"""
        # Base intensity
        intensity = 0.5
        
        # Higher if relationship is strong
        relationship = self._get_relationship_data(believer, about, world_state)
        if relationship:
            trust = relationship.get("trust", 50) / 100.0
            intensity += trust * 0.3
        
        # Higher if believer has high-confidence belief
        # (Would check actual belief confidence in production)
        intensity += 0.2
        
        return min(1.0, intensity)
    
    def _calculate_gap_urgency(
        self,
        believer: str,
        about: str,
        world_state
    ) -> float:
        """Calculate how urgent it is to address this gap"""
        # Urgency based on whether believer is actively seeking the other
        char = world_state.get_character(believer)
        if not char:
            return 0.3
        
        # If 'about' is in their goals, it's urgent
        if any(about in goal for goal in char.active_goals):
            return 0.9
        
        return 0.4
    
    def _get_relationship_data(
        self,
        char_a: str,
        char_b: str,
        world_state
    ) -> Dict[str, Any]:
        """Get relationship data between two characters"""
        char_a_obj = world_state.get_character(char_a)
        if not char_a_obj or not char_a_obj.profile:
            return {}
        
        relationships = getattr(char_a_obj.profile, 'relationships', {})
        relationship = relationships.get(char_b)
        
        if not relationship:
            return {}
        
        return {
            "trust": relationship.trust_level,
            "respect": relationship.respect_level,
            "history": relationship.shared_history_summary
        }
    
    def _check_belief_contradictions(
        self,
        char_a: str,
        char_b: str,
        world_state
    ) -> List[str]:
        """Check if two characters have contradictory beliefs"""
        # Simplified - would do semantic comparison in production
        contradictions_a = world_state.belief_graph.get_contradictions(char_a)
        contradictions_b = world_state.belief_graph.get_contradictions(char_b)
        
        # Return list of contradiction descriptions
        return [f"Contradiction set {i}" for i in range(len(contradictions_a))]
    
    def _get_affected_characters(
        self,
        artifact,
        world_state
    ) -> List[str]:
        """Get characters who should care about this artifact"""
        # Simplified - return all active characters
        return list(world_state.characters.keys())
    
    def _check_goal_conflict(
        self,
        char_a,
        char_b
    ) -> bool:
        """Check if two characters have conflicting goals"""
        # Simplified heuristic
        goals_a = set(char_a.active_goals)
        goals_b = set(char_b.active_goals)
        
        # Check for obvious conflicts (would need semantic analysis in production)
        conflict_keywords = [
            ("destroy", "protect"),
            ("steal", "guard"),
            ("defeat", "defend")
        ]
        
        for goal_a in goals_a:
            for goal_b in goals_b:
                for word_a, word_b in conflict_keywords:
                    if word_a in goal_a.lower() and word_b in goal_b.lower():
                        return True
        
        return False