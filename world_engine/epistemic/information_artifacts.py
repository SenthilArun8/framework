"""
Layer 2: Information Artifacts
Reports, observations, rumors, messages that characters actually encounter.
These CAN be: outdated, partial, contradictory, or false.
"""
from typing import Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ArtifactType(str, Enum):
    """Types of information artifacts"""
    DIRECT_OBSERVATION = "direct_observation"  # Character saw it themselves
    REPORT = "report"                          # Someone told them
    RUMOR = "rumor"                            # Heard through grapevine
    MESSAGE = "message"                        # Explicit communication
    DEDUCTION = "deduction"                    # Inferred from other info
    MEMORY = "memory"                          # Recalled from past


class ReliabilityLevel(str, Enum):
    """How reliable is this information?"""
    CERTAIN = "certain"           # Directly observed
    CONFIDENT = "confident"       # Trusted source
    PROBABLE = "probable"         # Likely true
    UNCERTAIN = "uncertain"       # May or may not be true
    DUBIOUS = "dubious"           # Probably false
    CONTRADICTED = "contradicted" # Proven false


@dataclass
class InformationArtifact:
    """
    A piece of information that exists in the world.
    This is what characters actually work with.
    
    Key properties:
    - Has a source (who/what generated it)
    - Has a timestamp (when it was created, NOT when event happened)
    - Has reliability (how trustworthy)
    - Can be superseded by newer information
    - Can contradict other artifacts
    """
    artifact_id: str
    created_at_tick: int           # When this info was created
    artifact_type: ArtifactType
    
    # Content
    subject: str                   # What/who it's about
    claim: str                     # Human-readable claim
    data: dict                     # Structured data
    
    # Provenance
    source: str                    # Who generated this (character_id or "system")
    reliability: ReliabilityLevel
    
    # Lifecycle
    superseded_by: Optional[str] = None  # Artifact ID that replaces this
    contradicts: Set[str] = field(default_factory=set)  # Artifact IDs this contradicts
    
    # Access control
    known_by: Set[str] = field(default_factory=set)  # Character IDs who know this
    
    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "created_at_tick": self.created_at_tick,
            "artifact_type": self.artifact_type.value,
            "subject": self.subject,
            "claim": self.claim,
            "data": self.data,
            "source": self.source,
            "reliability": self.reliability.value,
            "superseded_by": self.superseded_by,
            "contradicts": list(self.contradicts),
            "known_by": list(self.known_by)
        }


class InformationArtifactStore:
    """
    Manages all information artifacts in the world.
    """
    
    def __init__(self):
        self.artifacts: dict[str, InformationArtifact] = {}
        self._artifacts_by_subject: dict[str, List[str]] = {}
        self._artifacts_known_by: dict[str, Set[str]] = {}  # character_id -> artifact_ids
    
    def create_artifact(
        self,
        tick: int,
        artifact_type: ArtifactType,
        subject: str,
        claim: str,
        data: dict,
        source: str,
        reliability: ReliabilityLevel,
        known_by: Optional[Set[str]] = None
    ) -> InformationArtifact:
        """
        Create a new information artifact.
        
        This represents information entering the epistemic system.
        """
        artifact_id = f"artifact_{subject}_{tick}_{len(self.artifacts)}"
        
        artifact = InformationArtifact(
            artifact_id=artifact_id,
            created_at_tick=tick,
            artifact_type=artifact_type,
            subject=subject,
            claim=claim,
            data=data,
            source=source,
            reliability=reliability,
            known_by=known_by or set()
        )
        
        self.artifacts[artifact_id] = artifact
        
        # Index by subject
        if subject not in self._artifacts_by_subject:
            self._artifacts_by_subject[subject] = []
        self._artifacts_by_subject[subject].append(artifact_id)
        
        # Index by knower
        for character_id in artifact.known_by:
            if character_id not in self._artifacts_known_by:
                self._artifacts_known_by[character_id] = set()
            self._artifacts_known_by[character_id].add(artifact_id)
        
        logger.debug(f"📰 Created artifact: {claim}")
        
        return artifact
    
    def share_artifact(self, artifact_id: str, character_id: str):
        """Make a character aware of an artifact"""
        artifact = self.artifacts.get(artifact_id)
        if not artifact:
            return
        
        artifact.known_by.add(character_id)
        
        if character_id not in self._artifacts_known_by:
            self._artifacts_known_by[character_id] = set()
        self._artifacts_known_by[character_id].add(artifact_id)
    
    def supersede_artifact(self, old_id: str, new_id: str):
        """Mark an artifact as superseded by newer information"""
        old_artifact = self.artifacts.get(old_id)
        if old_artifact:
            old_artifact.superseded_by = new_id
            logger.debug(f"🔄 Artifact {old_id} superseded by {new_id}")
    
    def mark_contradiction(self, artifact_id: str, contradicts_id: str):
        """Mark two artifacts as contradicting each other"""
        artifact = self.artifacts.get(artifact_id)
        if artifact:
            artifact.contradicts.add(contradicts_id)
        
        # Reciprocal
        other = self.artifacts.get(contradicts_id)
        if other:
            other.contradicts.add(artifact_id)
    
    def get_artifacts_known_by(
        self,
        character_id: str,
        about_subject: Optional[str] = None,
        include_superseded: bool = False
    ) -> List[InformationArtifact]:
        """
        Get all artifacts a character knows about.
        
        This is what a character's reasoning would work with.
        """
        artifact_ids = self._artifacts_known_by.get(character_id, set())
        artifacts = [self.artifacts[aid] for aid in artifact_ids if aid in self.artifacts]
        
        # Filter by subject if specified
        if about_subject:
            artifacts = [a for a in artifacts if a.subject == about_subject]
        
        # Filter out superseded unless requested
        if not include_superseded:
            artifacts = [a for a in artifacts if a.superseded_by is None]
        
        return artifacts
    
    def get_latest_artifact_about(
        self,
        subject: str,
        known_by: Optional[str] = None
    ) -> Optional[InformationArtifact]:
        """Get the most recent artifact about a subject"""
        artifact_ids = self._artifacts_by_subject.get(subject, [])
        artifacts = [self.artifacts[aid] for aid in artifact_ids]
        
        # Filter by knower if specified
        if known_by:
            artifacts = [a for a in artifacts if known_by in a.known_by]
        
        # Filter out superseded
        artifacts = [a for a in artifacts if a.superseded_by is None]
        
        if not artifacts:
            return None
        
        # Most recent
        return max(artifacts, key=lambda a: a.created_at_tick)