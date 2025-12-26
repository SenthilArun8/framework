"""
Layer 3: Belief Graph
Tracks who believes what, with what confidence, and why.
This is where contradictions, skepticism, and trust dynamics live.
"""
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from .information_artifacts import InformationArtifact, ReliabilityLevel

logger = logging.getLogger(__name__)


class BeliefState(str, Enum):
    """How strongly a character believes something"""
    CONVINCED = "convinced"           # Absolutely believes it
    CONFIDENT = "confident"           # Strongly believes it
    LEANING_TRUE = "leaning_true"     # Probably believes it
    UNCERTAIN = "uncertain"           # No strong opinion
    LEANING_FALSE = "leaning_false"   # Probably disbelieves it
    SKEPTICAL = "skeptical"           # Strongly disbelieves it
    REJECTED = "rejected"             # Absolutely disbelieves it


@dataclass
class Belief:
    """
    A character's belief about a specific artifact.
    
    This is NOT the same as the artifact itself.
    Multiple characters can have different beliefs about the same artifact.
    """
    character_id: str
    artifact_id: str
    belief_state: BeliefState
    confidence: float  # 0.0-1.0
    
    # Why they believe this
    justification: str
    based_on: List[str] = field(default_factory=list)  # Other artifact IDs that support this
    
    # Lifecycle
    formed_at_tick: int = 0
    last_updated_tick: int = 0
    times_reinforced: int = 0
    times_challenged: int = 0
    
    def to_dict(self) -> dict:
        return {
            "character_id": self.character_id,
            "artifact_id": self.artifact_id,
            "belief_state": self.belief_state.value,
            "confidence": self.confidence,
            "justification": self.justification,
            "based_on": self.based_on,
            "formed_at_tick": self.formed_at_tick,
            "last_updated_tick": self.last_updated_tick,
            "times_reinforced": self.times_reinforced,
            "times_challenged": self.times_challenged
        }


class BeliefGraph:
    """
    Tracks all character beliefs about information artifacts.
    
    This is where:
    - Characters form opinions about information
    - Trust affects belief formation
    - Contradictions create cognitive dissonance
    - Beliefs can change over time
    """
    
    def __init__(self):
        # character_id -> artifact_id -> Belief
        self.beliefs: Dict[str, Dict[str, Belief]] = {}
        
        # Track contradictory beliefs
        self.contradictions: Dict[str, Set[Tuple[str, str]]] = {}  # character_id -> set of (artifact_id, artifact_id)
        
    def form_belief(
        self,
        character_id: str,
        artifact: InformationArtifact,
        current_tick: int,
        trust_in_source: float = 0.5,
        base_skepticism: float = 0.3
    ) -> Belief:
        """
        Character forms a belief about an artifact.
        
        Args:
            character_id: Who is forming the belief
            artifact: The information artifact
            current_tick: When this happens
            trust_in_source: How much character trusts the source (0-1)
            base_skepticism: Character's general skepticism level (0-1)
            
        Returns:
            The formed belief
        """
        # Calculate initial belief state based on:
        # 1. Artifact reliability
        # 2. Trust in source
        # 3. Character's base skepticism
        
        reliability_score = self._reliability_to_score(artifact.reliability)
        combined_score = (reliability_score * 0.5 + trust_in_source * 0.5) * (1 - base_skepticism)
        
        belief_state, confidence = self._score_to_belief_state(combined_score)
        
        # Check for contradictions with existing beliefs
        existing_contradictions = self._find_contradictions(character_id, artifact)
        
        if existing_contradictions:
            # Reduce confidence if contradicts existing beliefs
            confidence *= 0.7
            belief_state = self._adjust_for_contradiction(belief_state)
            justification = f"Conflicts with {len(existing_contradictions)} existing beliefs"
        else:
            justification = f"Based on {artifact.artifact_type.value} from {artifact.source}"
        
        belief = Belief(
            character_id=character_id,
            artifact_id=artifact.artifact_id,
            belief_state=belief_state,
            confidence=confidence,
            justification=justification,
            formed_at_tick=current_tick,
            last_updated_tick=current_tick
        )
        
        # Store belief
        if character_id not in self.beliefs:
            self.beliefs[character_id] = {}
        self.beliefs[character_id][artifact.artifact_id] = belief
        
        # Track contradictions
        if existing_contradictions:
            if character_id not in self.contradictions:
                self.contradictions[character_id] = set()
            for contra_id in existing_contradictions:
                self.contradictions[character_id].add((artifact.artifact_id, contra_id))
        
        logger.debug(
            f"💭 {character_id} formed belief: {belief_state.value} "
            f"(confidence: {confidence:.2f}) about {artifact.claim}"
        )
        
        return belief
    
    def update_belief(
        self,
        character_id: str,
        artifact_id: str,
        new_evidence: InformationArtifact,
        current_tick: int,
        reinforces: bool = True
    ) -> Optional[Belief]:
        """
        Update an existing belief with new evidence.
        
        Args:
            character_id: Whose belief to update
            artifact_id: Which belief to update
            new_evidence: New information artifact
            current_tick: Current tick
            reinforces: Whether evidence supports (True) or challenges (False) the belief
            
        Returns:
            Updated belief or None if belief doesn't exist
        """
        if character_id not in self.beliefs:
            return None
        
        belief = self.beliefs[character_id].get(artifact_id)
        if not belief:
            return None
        
        if reinforces:
            # Evidence supports the belief - increase confidence
            belief.confidence = min(1.0, belief.confidence + 0.1)
            belief.times_reinforced += 1
            belief.based_on.append(new_evidence.artifact_id)
            
            # May shift belief state stronger
            if belief.confidence > 0.9 and belief.belief_state == BeliefState.CONFIDENT:
                belief.belief_state = BeliefState.CONVINCED
            elif belief.confidence > 0.7 and belief.belief_state == BeliefState.LEANING_TRUE:
                belief.belief_state = BeliefState.CONFIDENT
            
            logger.debug(f"✅ {character_id}'s belief reinforced: {artifact_id}")
        else:
            # Evidence challenges the belief - decrease confidence
            belief.confidence = max(0.0, belief.confidence - 0.15)
            belief.times_challenged += 1
            
            # May shift belief state weaker
            if belief.confidence < 0.3 and belief.belief_state == BeliefState.CONFIDENT:
                belief.belief_state = BeliefState.LEANING_TRUE
            elif belief.confidence < 0.5 and belief.belief_state == BeliefState.CONVINCED:
                belief.belief_state = BeliefState.CONFIDENT
            
            # If challenged too many times, may flip
            if belief.times_challenged >= 3:
                belief.belief_state = BeliefState.UNCERTAIN
            
            logger.debug(f"⚠️  {character_id}'s belief challenged: {artifact_id}")
        
        belief.last_updated_tick = current_tick
        
        return belief
    
    def get_belief(
        self,
        character_id: str,
        artifact_id: str
    ) -> Optional[Belief]:
        """Get a character's belief about a specific artifact"""
        if character_id not in self.beliefs:
            return None
        return self.beliefs[character_id].get(artifact_id)
    
    def get_all_beliefs(
        self,
        character_id: str,
        min_confidence: Optional[float] = None
    ) -> List[Belief]:
        """
        Get all beliefs a character holds.
        
        Args:
            character_id: Whose beliefs
            min_confidence: Only return beliefs above this confidence
        """
        if character_id not in self.beliefs:
            return []
        
        beliefs = list(self.beliefs[character_id].values())
        
        if min_confidence is not None:
            beliefs = [b for b in beliefs if b.confidence >= min_confidence]
        
        return beliefs
    
    def get_contradictions(self, character_id: str) -> Set[Tuple[str, str]]:
        """Get all contradictory belief pairs for a character"""
        return self.contradictions.get(character_id, set())
    
    def resolve_contradiction(
        self,
        character_id: str,
        artifact_id_a: str,
        artifact_id_b: str,
        favor: str  # Which artifact to favor
    ):
        """
        Resolve a contradiction by weakening one belief.
        
        Args:
            character_id: Whose contradiction to resolve
            artifact_id_a: First contradicting artifact
            artifact_id_b: Second contradicting artifact
            favor: artifact_id of the one to strengthen
        """
        belief_a = self.get_belief(character_id, artifact_id_a)
        belief_b = self.get_belief(character_id, artifact_id_b)
        
        if not belief_a or not belief_b:
            return
        
        if favor == artifact_id_a:
            # Strengthen A, weaken B
            belief_a.confidence = min(1.0, belief_a.confidence + 0.15)
            belief_b.confidence = max(0.0, belief_b.confidence - 0.2)
            belief_b.belief_state = BeliefState.SKEPTICAL
        else:
            # Strengthen B, weaken A
            belief_b.confidence = min(1.0, belief_b.confidence + 0.15)
            belief_a.confidence = max(0.0, belief_a.confidence - 0.2)
            belief_a.belief_state = BeliefState.SKEPTICAL
        
        # Remove from contradictions
        if character_id in self.contradictions:
            self.contradictions[character_id].discard((artifact_id_a, artifact_id_b))
            self.contradictions[character_id].discard((artifact_id_b, artifact_id_a))
        
        logger.debug(f"🔀 {character_id} resolved contradiction, favoring {favor}")
    
    def _reliability_to_score(self, reliability: ReliabilityLevel) -> float:
        """Convert reliability level to numeric score"""
        mapping = {
            ReliabilityLevel.CERTAIN: 1.0,
            ReliabilityLevel.CONFIDENT: 0.85,
            ReliabilityLevel.PROBABLE: 0.7,
            ReliabilityLevel.UNCERTAIN: 0.5,
            ReliabilityLevel.DUBIOUS: 0.3,
            ReliabilityLevel.CONTRADICTED: 0.1
        }
        return mapping.get(reliability, 0.5)
    
    def _score_to_belief_state(self, score: float) -> Tuple[BeliefState, float]:
        """Convert numeric score to belief state and confidence"""
        if score > 0.9:
            return BeliefState.CONVINCED, score
        elif score > 0.7:
            return BeliefState.CONFIDENT, score
        elif score > 0.55:
            return BeliefState.LEANING_TRUE, score
        elif score > 0.45:
            return BeliefState.UNCERTAIN, score
        elif score > 0.3:
            return BeliefState.LEANING_FALSE, score
        elif score > 0.1:
            return BeliefState.SKEPTICAL, score
        else:
            return BeliefState.REJECTED, score
    
    def _adjust_for_contradiction(self, belief_state: BeliefState) -> BeliefState:
        """Weaken belief state due to contradiction"""
        adjustments = {
            BeliefState.CONVINCED: BeliefState.CONFIDENT,
            BeliefState.CONFIDENT: BeliefState.LEANING_TRUE,
            BeliefState.LEANING_TRUE: BeliefState.UNCERTAIN,
            BeliefState.UNCERTAIN: BeliefState.UNCERTAIN,
            BeliefState.LEANING_FALSE: BeliefState.SKEPTICAL,
            BeliefState.SKEPTICAL: BeliefState.REJECTED,
            BeliefState.REJECTED: BeliefState.REJECTED
        }
        return adjustments.get(belief_state, belief_state)
    
    def _find_contradictions(
        self,
        character_id: str,
        new_artifact: InformationArtifact
    ) -> List[str]:
        """Find existing beliefs that contradict a new artifact"""
        if character_id not in self.beliefs:
            return []
        
        contradictions = []
        
        # Check if new artifact contradicts any existing beliefs
        for artifact_id, belief in self.beliefs[character_id].items():
            # Artifacts about same subject with contradicting data = contradiction
            # (Simplified - in production, need semantic comparison)
            if new_artifact.subject == belief.artifact_id.split('_')[1]:  # Rough heuristic
                if artifact_id in new_artifact.contradicts:
                    contradictions.append(artifact_id)
        
        return contradictions
    
    def get_stats(self, character_id: str) -> dict:
        """Get statistics about a character's belief state"""
        if character_id not in self.beliefs:
            return {
                "total_beliefs": 0,
                "contradictions": 0,
                "high_confidence": 0,
                "uncertain": 0,
                "rejected": 0
            }
        
        beliefs = self.beliefs[character_id].values()
        
        return {
            "total_beliefs": len(beliefs),
            "contradictions": len(self.contradictions.get(character_id, set())),
            "high_confidence": len([b for b in beliefs if b.confidence > 0.8]),
            "uncertain": len([b for b in beliefs if b.belief_state == BeliefState.UNCERTAIN]),
            "rejected": len([b for b in beliefs if b.belief_state == BeliefState.REJECTED])
        }