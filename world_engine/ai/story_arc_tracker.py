"""
Story Arc Tracker - Tracks multi-tick narrative arcs

Maintains coherent story threads across many ticks:
- Character journey tracking
- Relationship evolution
- Quest/goal progression
- Thematic consistency
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ArcStatus(str, Enum):
    """Status of a story arc"""
    SETUP = "setup"
    DEVELOPING = "developing"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    COMPLETE = "complete"
    ABANDONED = "abandoned"


@dataclass
class StoryArc:
    """A narrative thread spanning multiple ticks"""
    arc_id: str
    arc_type: str
    title: str
    theme: str
    characters_involved: List[str]
    start_tick: int
    current_status: ArcStatus = ArcStatus.SETUP
    completion_percent: float = 0.0
    beats: List[Dict[str, Any]] = field(default_factory=list)
    last_update_tick: int = 0
    milestones_achieved: List[str] = field(default_factory=list)
    
    def add_beat(self, tick: int, description: str, beat_type: str):
        """Add a narrative beat to this arc"""
        self.beats.append({
            "tick": tick,
            "description": description,
            "type": beat_type
        })
        self.last_update_tick = tick
        logger.info(f"📖 Arc '{self.title}': {description}")
    
    def advance_status(self, new_status: ArcStatus):
        """Move arc to next phase"""
        old_status = self.current_status
        self.current_status = new_status
        
        status_completion = {
            ArcStatus.SETUP: 0.2,
            ArcStatus.DEVELOPING: 0.5,
            ArcStatus.CLIMAX: 0.8,
            ArcStatus.RESOLUTION: 0.95,
            ArcStatus.COMPLETE: 1.0
        }
        self.completion_percent = status_completion.get(new_status, 0.0)
        logger.info(f"📖 Arc '{self.title}': {old_status.value} → {new_status.value}")


class StoryArcTracker:
    """Tracks ongoing narrative arcs across the simulation"""
    
    def __init__(self):
        self.active_arcs: Dict[str, StoryArc] = {}
        self.completed_arcs: List[StoryArc] = []
        self.next_arc_id = 0
    
    def create_arc(
        self,
        arc_type: str,
        title: str,
        theme: str,
        characters: List[str],
        current_tick: int
    ) -> StoryArc:
        """Create a new story arc"""
        arc_id = f"arc_{self.next_arc_id}"
        self.next_arc_id += 1
        
        arc = StoryArc(
            arc_id=arc_id,
            arc_type=arc_type,
            title=title,
            theme=theme,
            characters_involved=characters,
            start_tick=current_tick,
            last_update_tick=current_tick
        )
        
        self.active_arcs[arc_id] = arc
        logger.info(f"📖 New story arc: '{title}' ({arc_type})")
        return arc
    
    def update_arc(
        self,
        arc_id: str,
        current_tick: int,
        beat_description: str,
        beat_type: str = "development"
    ):
        """Add a beat to an existing arc"""
        arc = self.active_arcs.get(arc_id)
        if not arc:
            logger.warning(f"Arc not found: {arc_id}")
            return
        
        arc.add_beat(current_tick, beat_description, beat_type)
        self._check_progression(arc, current_tick)
    
    def _check_progression(self, arc: StoryArc, current_tick: int):
        """Check if arc should advance to next phase"""
        num_beats = len(arc.beats)
        
        if arc.current_status == ArcStatus.SETUP and num_beats >= 2:
            arc.advance_status(ArcStatus.DEVELOPING)
        elif arc.current_status == ArcStatus.DEVELOPING and num_beats >= 5:
            arc.advance_status(ArcStatus.CLIMAX)
        elif arc.current_status == ArcStatus.CLIMAX and num_beats >= 7:
            arc.advance_status(ArcStatus.RESOLUTION)
        elif arc.current_status == ArcStatus.RESOLUTION and num_beats >= 8:
            self.complete_arc(arc.arc_id, current_tick)
    
    def complete_arc(self, arc_id: str, current_tick: int):
        """Mark an arc as complete"""
        arc = self.active_arcs.pop(arc_id, None)
        if not arc:
            return
        
        arc.advance_status(ArcStatus.COMPLETE)
        arc.last_update_tick = current_tick
        self.completed_arcs.append(arc)
        logger.info(f"✅ Arc completed: '{arc.title}'")
    
    def abandon_arc(self, arc_id: str, current_tick: int, reason: str):
        """Abandon an arc that's no longer viable"""
        arc = self.active_arcs.pop(arc_id, None)
        if not arc:
            return
        
        arc.advance_status(ArcStatus.ABANDONED)
        arc.last_update_tick = current_tick
        arc.add_beat(current_tick, f"Abandoned: {reason}", "abandonment")
        self.completed_arcs.append(arc)
        logger.info(f"❌ Arc abandoned: '{arc.title}'")
    
    def get_arcs_for_character(self, character_id: str) -> List[StoryArc]:
        """Get all active arcs involving a character"""
        return [
            arc for arc in self.active_arcs.values()
            if character_id in arc.characters_involved
        ]
    
    def get_stale_arcs(
        self,
        current_tick: int,
        stale_threshold: int = 50
    ) -> List[StoryArc]:
        """Get arcs that haven't been updated recently"""
        return [
            arc for arc in self.active_arcs.values()
            if (current_tick - arc.last_update_tick) > stale_threshold
        ]
    
    def prune_stale_arcs(self, current_tick: int, threshold: int = 100):
        """Abandon arcs that have been inactive too long"""
        stale = self.get_stale_arcs(current_tick, threshold)
        for arc in stale:
            self.abandon_arc(arc.arc_id, current_tick, "inactive too long")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics"""
        return {
            "active_arcs": len(self.active_arcs),
            "completed_arcs": len(self.completed_arcs),
            "total_arcs": len(self.active_arcs) + len(self.completed_arcs)
        }