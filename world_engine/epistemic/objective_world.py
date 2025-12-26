"""
Layer 1: Objective World State
This is ENGINE TRUTH - what actually happened, with perfect fidelity.
Characters do NOT have direct access to this.
"""
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ObjectiveFact:
    """
    A single indisputable fact about the world.
    This is what ACTUALLY happened, not what anyone believes.
    """
    fact_id: str
    tick: int                      # When it happened
    fact_type: str                 # "character_moved", "event_occurred", etc.
    subject: str                   # Who/what it's about
    data: dict                     # The actual facts
    observers: Set[str] = field(default_factory=set)  # Who was present
    
    def to_dict(self) -> dict:
        return {
            "fact_id": self.fact_id,
            "tick": self.tick,
            "fact_type": self.fact_type,
            "subject": self.subject,
            "data": self.data,
            "observers": list(self.observers)
        }


class ObjectiveWorld:
    """
    The authoritative, ground-truth record of what has happened.
    
    Properties:
    - Never forgets
    - Never drifts
    - Never lies
    - Never contradicts itself
    - Append-only (facts are immutable once recorded)
    
    Characters do NOT query this directly.
    Instead, they receive Information Artifacts derived from this.
    """
    
    def __init__(self, data_dir: str = "world_data"):
        self.data_dir = Path(data_dir) / "objective"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Immutable fact log (append-only)
        self.fact_log: List[ObjectiveFact] = []
        
        # Indices for fast queries
        self._facts_by_tick: Dict[int, List[ObjectiveFact]] = {}
        self._facts_by_subject: Dict[str, List[ObjectiveFact]] = {}
        self._facts_by_type: Dict[str, List[ObjectiveFact]] = {}
        
        # Current state (derived from fact log)
        self.current_character_states: Dict[str, dict] = {}
        self.current_location_states: Dict[str, dict] = {}
        
        self._load_from_disk()
    
    def record_fact(
        self,
        tick: int,
        fact_type: str,
        subject: str,
        data: dict,
        observers: Optional[Set[str]] = None
    ) -> ObjectiveFact:
        """
        Record an objective fact about the world.
        This is the ONLY way facts enter the system.
        
        Args:
            tick: When this happened
            fact_type: Type of fact (character_moved, event_occurred, etc.)
            subject: Primary subject (character_id, location_id, etc.)
            data: The factual data
            observers: Who was present to potentially observe this
            
        Returns:
            The recorded fact
        """
        fact_id = f"{fact_type}_{subject}_{tick}_{len(self.fact_log)}"
        
        fact = ObjectiveFact(
            fact_id=fact_id,
            tick=tick,
            fact_type=fact_type,
            subject=subject,
            data=data,
            observers=observers or set()
        )
        
        # Append to log (immutable)
        self.fact_log.append(fact)
        
        # Update indices
        if tick not in self._facts_by_tick:
            self._facts_by_tick[tick] = []
        self._facts_by_tick[tick].append(fact)
        
        if subject not in self._facts_by_subject:
            self._facts_by_subject[subject] = []
        self._facts_by_subject[subject].append(fact)
        
        if fact_type not in self._facts_by_type:
            self._facts_by_type[fact_type] = []
        self._facts_by_type[fact_type].append(fact)
        
        # Update current state projection
        self._update_current_state(fact)
        
        logger.debug(f"📝 Recorded fact: {fact_type} - {subject}")
        
        return fact
    
    def _update_current_state(self, fact: ObjectiveFact):
        """Update the current state projection from a new fact"""
        if fact.fact_type == "character_moved":
            self.current_character_states[fact.subject] = {
                "location": fact.data["destination"],
                "last_moved_tick": fact.tick
            }
        elif fact.fact_type == "character_state_changed":
            if fact.subject not in self.current_character_states:
                self.current_character_states[fact.subject] = {}
            self.current_character_states[fact.subject].update(fact.data)
    
    def query_facts_at_tick(self, tick: int) -> List[ObjectiveFact]:
        """Get all facts that occurred at a specific tick"""
        return self._facts_by_tick.get(tick, [])
    
    def query_facts_about_subject(
        self,
        subject: str,
        since_tick: Optional[int] = None,
        until_tick: Optional[int] = None
    ) -> List[ObjectiveFact]:
        """
        Get all facts about a specific subject.
        
        Args:
            subject: Character ID, location ID, etc.
            since_tick: Only facts after this tick
            until_tick: Only facts before this tick
        """
        facts = self._facts_by_subject.get(subject, [])
        
        if since_tick is not None:
            facts = [f for f in facts if f.tick >= since_tick]
        if until_tick is not None:
            facts = [f for f in facts if f.tick <= until_tick]
        
        return facts
    
    def query_facts_by_type(
        self,
        fact_type: str,
        since_tick: Optional[int] = None
    ) -> List[ObjectiveFact]:
        """Get all facts of a specific type"""
        facts = self._facts_by_type.get(fact_type, [])
        
        if since_tick is not None:
            facts = [f for f in facts if f.tick >= since_tick]
        
        return facts
    
    def get_character_location_at_tick(
        self,
        character_id: str,
        tick: int
    ) -> Optional[str]:
        """
        Get where a character objectively was at a specific tick.
        This is ENGINE TRUTH, not belief.
        """
        # Get all movement facts for this character up to this tick
        movement_facts = [
            f for f in self.query_facts_about_subject(character_id, until_tick=tick)
            if f.fact_type == "character_moved"
        ]
        
        if not movement_facts:
            return None
        
        # Most recent movement
        latest = max(movement_facts, key=lambda f: f.tick)
        return latest.data["destination"]
    
    def get_current_state(self) -> dict:
        """Get the current derived state (NOT for character use)"""
        return {
            "characters": self.current_character_states.copy(),
            "locations": self.current_location_states.copy(),
            "total_facts": len(self.fact_log)
        }
    
    def save_to_disk(self):
        """Persist the fact log"""
        fact_log_file = self.data_dir / "fact_log.jsonl"
        
        # Append-only write
        with open(fact_log_file, 'a') as f:
            # Only write facts not yet written
            # (In production, track last_written_index)
            for fact in self.fact_log:
                f.write(json.dumps(fact.to_dict()) + "\n")
        
        logger.info(f"💾 Saved {len(self.fact_log)} facts to disk")
    
    def _load_from_disk(self):
        """Load existing fact log"""
        fact_log_file = self.data_dir / "fact_log.jsonl"
        
        if not fact_log_file.exists():
            return
        
        with open(fact_log_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                
                data = json.loads(line)
                fact = ObjectiveFact(
                    fact_id=data["fact_id"],
                    tick=data["tick"],
                    fact_type=data["fact_type"],
                    subject=data["subject"],
                    data=data["data"],
                    observers=set(data.get("observers", []))
                )
                
                self.fact_log.append(fact)
                
                # Rebuild indices
                if fact.tick not in self._facts_by_tick:
                    self._facts_by_tick[fact.tick] = []
                self._facts_by_tick[fact.tick].append(fact)
                
                if fact.subject not in self._facts_by_subject:
                    self._facts_by_subject[fact.subject] = []
                self._facts_by_subject[fact.subject].append(fact)
                
                if fact.fact_type not in self._facts_by_type:
                    self._facts_by_type[fact.fact_type] = []
                self._facts_by_type[fact.fact_type].append(fact)
        
        logger.info(f"📂 Loaded {len(self.fact_log)} facts from disk")
    
    def get_stats(self) -> dict:
        """Get statistics about the objective world"""
        return {
            "total_facts": len(self.fact_log),
            "fact_types": {
                fact_type: len(facts)
                for fact_type, facts in self._facts_by_type.items()
            },
            "subjects_tracked": len(self._facts_by_subject)
        }