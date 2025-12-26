"""
Tension Manager - Manages narrative tension curves

Ensures the simulation has proper pacing:
- Builds tension gradually
- Creates peaks and valleys
- Avoids monotony
- Manages story rhythm
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class TensionPoint:
    """A point on the tension curve"""
    tick: int
    tension: float  # 0-100
    source: str     # What caused this tension level
    event_id: Optional[str] = None


class TensionManager:
    """
    Manages narrative tension over time.
    
    Follows principles of story structure:
    - Rising action
    - Climax
    - Falling action
    - Resolution
    """
    
    def __init__(self, target_arc_length: int = 100):
        self.current_tension = 30.0
        self.target_tension = 50.0
        self.target_arc_length = target_arc_length
        
        # Tension history for analysis
        self.tension_history: deque = deque(maxlen=200)
        
        # Arc tracking
        self.current_arc_start = 0
        self.arc_phase = "rising"  # rising, peak, falling, valley
        
        # Constraints
        self.min_tension = 10.0
        self.max_tension = 90.0
        self.max_change_per_tick = 5.0
    
    def update_tension(
        self,
        current_tick: int,
        dramatic_events: List[Dict[str, Any]],
        world_state
    ) -> float:
        """
        Update tension based on recent events and world state.
        
        Args:
            current_tick: Current simulation tick
            dramatic_events: Events that occurred this tick
            world_state: Current world state
            
        Returns:
            New tension level
        """
        # Calculate base tension from world state
        base_tension = self._calculate_base_tension(world_state)
        
        # Add event-based spikes
        event_delta = self._calculate_event_tension(dramatic_events)
        
        # Apply arc-based modulation
        arc_modifier = self._get_arc_modifier(current_tick)
        
        # Calculate new tension
        raw_tension = base_tension + event_delta + arc_modifier
        
        # Apply constraints
        new_tension = self._apply_constraints(
            self.current_tension,
            raw_tension
        )
        
        # Update state
        self.current_tension = new_tension
        self.tension_history.append(TensionPoint(
            tick=current_tick,
            tension=new_tension,
            source="update",
            event_id=dramatic_events[0]["id"] if dramatic_events else None
        ))
        
        # Update arc phase
        self._update_arc_phase(current_tick)
        
        logger.debug(
            f"📊 Tension: {new_tension:.1f}/100 "
            f"(base: {base_tension:.1f}, events: {event_delta:+.1f}, "
            f"arc: {arc_modifier:+.1f}) - Phase: {self.arc_phase}"
        )
        
        return new_tension
    
    def _calculate_base_tension(self, world_state) -> float:
        """Calculate base tension from world state"""
        tension = 20.0
        
        # Active conflicts increase tension
        active_events = len([
            e for e in world_state.events.values()
            if e.status.value == "active"
        ])
        tension += active_events * 5.0
        
        # Characters in close proximity with contradictions
        # (Would implement full analysis in production)
        tension += 10.0
        
        return min(self.max_tension, tension)
    
    def _calculate_event_tension(
        self,
        dramatic_events: List[Dict[str, Any]]
    ) -> float:
        """Calculate tension spike from dramatic events"""
        delta = 0.0
        
        for event in dramatic_events:
            event_type = event.get("type", "")
            
            # Different event types have different tension impacts
            tension_map = {
                "betrayal": 20.0,
                "revelation": 15.0,
                "conflict": 10.0,
                "discovery": 8.0,
                "meeting": 5.0
            }
            
            delta += tension_map.get(event_type, 3.0)
        
        return min(20.0, delta)  # Cap spike at 20
    
    def _get_arc_modifier(self, current_tick: int) -> float:
        """Get tension modifier based on story arc phase"""
        ticks_in_arc = current_tick - self.current_arc_start
        progress = ticks_in_arc / self.target_arc_length
        
        if self.arc_phase == "rising":
            # Gradually increase tension
            return progress * 10.0
        elif self.arc_phase == "peak":
            # Maintain high tension
            return 5.0
        elif self.arc_phase == "falling":
            # Decrease tension
            return -progress * 10.0
        else:  # valley
            # Low tension
            return -5.0
    
    def _apply_constraints(
        self,
        current: float,
        target: float
    ) -> float:
        """Apply rate limits and bounds to tension changes"""
        # Maximum change per tick
        delta = target - current
        if abs(delta) > self.max_change_per_tick:
            delta = self.max_change_per_tick if delta > 0 else -self.max_change_per_tick
        
        new_value = current + delta
        
        # Apply bounds
        return max(self.min_tension, min(self.max_tension, new_value))
    
    def _update_arc_phase(self, current_tick: int):
        """Update the current narrative arc phase"""
        ticks_in_arc = current_tick - self.current_arc_start
        progress = ticks_in_arc / self.target_arc_length
        
        # Phase transitions
        if self.arc_phase == "rising" and progress > 0.6:
            self.arc_phase = "peak"
            logger.info("🎭 Entering PEAK phase")
        elif self.arc_phase == "peak" and progress > 0.7:
            self.arc_phase = "falling"
            logger.info("🎭 Entering FALLING phase")
        elif self.arc_phase == "falling" and progress > 0.9:
            self.arc_phase = "valley"
            logger.info("🎭 Entering VALLEY phase")
        elif self.arc_phase == "valley" and progress >= 1.0:
            # Start new arc
            self.arc_phase = "rising"
            self.current_arc_start = current_tick
            logger.info("🎭 Starting new arc - RISING phase")
    
    def should_escalate(self) -> bool:
        """Should the director escalate tension?"""
        return self.current_tension < self.target_tension and self.arc_phase == "rising"
    
    def should_de_escalate(self) -> bool:
        """Should the director de-escalate tension?"""
        return self.current_tension > self.target_tension and self.arc_phase == "falling"
    
    def get_tension_trend(self, window: int = 10) -> str:
        """Get recent tension trend"""
        if len(self.tension_history) < 2:
            return "stable"
        
        recent = list(self.tension_history)[-window:]
        if len(recent) < 2:
            return "stable"
        
        start_tension = recent[0].tension
        end_tension = recent[-1].tension
        delta = end_tension - start_tension
        
        if delta > 5:
            return "rising"
        elif delta < -5:
            return "falling"
        else:
            return "stable"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tension statistics"""
        return {
            "current_tension": self.current_tension,
            "target_tension": self.target_tension,
            "arc_phase": self.arc_phase,
            "trend": self.get_tension_trend(),
            "history_size": len(self.tension_history)
        }