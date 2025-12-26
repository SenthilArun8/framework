"""
Perception System - Bridge between Objective World and Information Artifacts
Determines what characters observe and how reliably.
"""
import logging
import random
from typing import Set, Optional

from .objective_world import ObjectiveWorld, ObjectiveFact
from .information_artifacts import (
    InformationArtifactStore,
    ArtifactType,
    ReliabilityLevel,
    InformationArtifact
)

logger = logging.getLogger(__name__)


class PerceptionSystem:
    """
    Converts objective facts into information artifacts.
    
    This is where:
    - Observation happens
    - Information degrades
    - Rumors spread
    - Reports get generated
    """
    
    def __init__(
        self,
        objective_world: ObjectiveWorld,
        artifact_store: InformationArtifactStore
    ):
        self.objective_world = objective_world
        self.artifact_store = artifact_store
    
    def process_direct_observation(
        self,
        fact: ObjectiveFact,
        observer: str
    ) -> InformationArtifact:
        """
        Character directly observes something happening.
        Creates a CERTAIN artifact for the observer.
        """
        artifact = self.artifact_store.create_artifact(
            tick=fact.tick,
            artifact_type=ArtifactType.DIRECT_OBSERVATION,
            subject=fact.subject,
            claim=self._generate_claim(fact),
            data=fact.data.copy(),
            source=observer,
            reliability=ReliabilityLevel.CERTAIN,
            known_by={observer}
        )
        
        logger.debug(f"👁️  {observer} observed: {artifact.claim}")
        
        return artifact
    
    def process_report(
        self,
        fact: ObjectiveFact,
        reporter: str,
        recipient: str,
        reporter_reliability: float = 0.9
    ) -> InformationArtifact:
        """
        One character tells another about something.
        Reliability depends on reporter's credibility.
        """
        # Determine reliability based on reporter
        if reporter_reliability > 0.9:
            reliability = ReliabilityLevel.CONFIDENT
        elif reporter_reliability > 0.7:
            reliability = ReliabilityLevel.PROBABLE
        else:
            reliability = ReliabilityLevel.UNCERTAIN
        
        artifact = self.artifact_store.create_artifact(
            tick=fact.tick + 1,  # Report comes after the fact
            artifact_type=ArtifactType.REPORT,
            subject=fact.subject,
            claim=f"{reporter} says: {self._generate_claim(fact)}",
            data=fact.data.copy(),
            source=reporter,
            reliability=reliability,
            known_by={recipient}
        )
        
        logger.debug(f"📢 {reporter} reported to {recipient}: {artifact.claim}")
        
        return artifact
    
    def process_rumor(
        self,
        fact: ObjectiveFact,
        current_tick: int,
        spreaders: Set[str],
        delay_ticks: int = 5
    ) -> InformationArtifact:
        """
        Information spreads as rumor (degraded reliability).
        """
        # Rumors are less reliable
        reliability = random.choice([
            ReliabilityLevel.UNCERTAIN,
            ReliabilityLevel.DUBIOUS
        ])
        
        # Information may be distorted
        distorted_data = self._distort_data(fact.data)
        
        artifact = self.artifact_store.create_artifact(
            tick=current_tick,
            artifact_type=ArtifactType.RUMOR,
            subject=fact.subject,
            claim=f"Rumor: {self._generate_claim(fact)}",
            data=distorted_data,
            source="rumor_mill",
            reliability=reliability,
            known_by=spreaders
        )
        
        logger.debug(f"💬 Rumor spread: {artifact.claim}")
        
        return artifact
    
    def _generate_claim(self, fact: ObjectiveFact) -> str:
        """Generate human-readable claim from fact"""
        if fact.fact_type == "character_moved":
            return f"{fact.subject} moved to {fact.data.get('destination')}"
        elif fact.fact_type == "event_occurred":
            return f"Event: {fact.data.get('title', 'Something happened')}"
        else:
            return f"{fact.fact_type} involving {fact.subject}"
    
    def _distort_data(self, data: dict, distortion_rate: float = 0.2) -> dict:
        """Simulate information distortion in rumors"""
        distorted = data.copy()
        
        # Randomly distort some fields
        for key in distorted:
            if random.random() < distortion_rate:
                if isinstance(distorted[key], str):
                    distorted[key] = distorted[key] + " (unverified)"
        
        return distorted
    
    def update_stale_information(self, current_tick: int, staleness_threshold: int = 20):
        """
        Check for information that might be outdated.
        Generate new artifacts to update stale ones.
        """
        # Check all artifacts
        for artifact_id, artifact in self.artifact_store.artifacts.items():
            age = current_tick - artifact.created_at_tick
            
            if age > staleness_threshold and artifact.superseded_by is None:
                # This information is getting old
                # Check if objective world has newer facts
                newer_facts = self.objective_world.query_facts_about_subject(
                    artifact.subject,
                    since_tick=artifact.created_at_tick
                )
                
                if newer_facts:
                    # Create updated artifact
                    latest_fact = newer_facts[-1]
                    new_artifact = self.artifact_store.create_artifact(
                        tick=current_tick,
                        artifact_type=ArtifactType.REPORT,
                        subject=latest_fact.subject,
                        claim=f"Updated: {self._generate_claim(latest_fact)}",
                        data=latest_fact.data.copy(),
                        source="system",
                        reliability=ReliabilityLevel.CONFIDENT,
                        known_by=artifact.known_by.copy()
                    )
                    
                    # Supersede old artifact
                    self.artifact_store.supersede_artifact(artifact_id, new_artifact.artifact_id)