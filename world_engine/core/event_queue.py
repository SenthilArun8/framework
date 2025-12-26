"""
Event Queue - Priority-based scheduling system
Events are processed when their scheduled tick arrives
"""
from queue import PriorityQueue
from dataclasses import dataclass, field
from typing import Any, Optional, List
import logging

from ..entities.event import Event, EventType, EventStatus

logger = logging.getLogger(__name__)


@dataclass(order=True)
class QueuedEvent:
    """
    Wrapper for events in the priority queue.
    Lower tick + lower priority = processed first.
    """
    tick: int
    priority: int
    event: Event = field(compare=False)



class EventQueue:
    """
    Manages scheduling and execution of world events.
    """
    
    def __init__(self):
        self.queue: PriorityQueue[QueuedEvent] = PriorityQueue()
        self.active_events: dict[str, Event] = {}  # Events currently running
        self.completed_events: List[Event] = []
        
        # Statistics
        self.total_scheduled = 0
        self.total_processed = 0
        
    def schedule(self, event: Event) -> None:
        """
        Schedule an event to occur at a specific tick.
        
        Args:
            event: Event to schedule
        """
        queued = QueuedEvent(
            tick=event.scheduled_tick,
            priority=event.priority,
            event=event
        )
        self.queue.put(queued)
        self.total_scheduled += 1
        
        logger.info(
            f"📅 Scheduled {event.type.value} '{event.title}' "
            f"for tick {event.scheduled_tick} (priority {event.priority})"
        )
        
    def schedule_multiple(self, events: List[Event]) -> None:
        """Schedule multiple events at once"""
        for event in events:
            self.schedule(event)
            
    async def process_due_events(
        self, 
        current_tick: int,
        executor: Optional[callable] = None
    ) -> List[Event]:
        """
        Process all events scheduled for this tick or earlier.
        
        Args:
            current_tick: Current simulation tick
            executor: Optional async function to execute events
            
        Returns:
            List of events that were processed
        """
        processed = []
        
        # Collect all due events
        while not self.queue.empty():
            queued = self.queue.queue[0]  # Peek without removing
            
            if queued.tick <= current_tick:
                queued = self.queue.get()  # Now remove it
                event = queued.event
                
                # Mark as active
                event.status = EventStatus.ACTIVE
                event.start_tick = current_tick
                self.active_events[event.id] = event
                
                logger.info(f"▶️  Processing: {event.title}")
                
                # Execute if executor provided
                if executor:
                    try:
                        await executor(event)
                    except Exception as e:
                        logger.error(f"Error executing event {event.id}: {e}")
                        event.status = EventStatus.CANCELLED
                
                processed.append(event)
                self.total_processed += 1
            else:
                break  # No more due events
                
        return processed
        
    def complete_event(self, event_id: str, current_tick: int) -> Optional[Event]:
        """
        Mark an event as completed.
        
        Args:
            event_id: ID of event to complete
            current_tick: Current tick
            
        Returns:
            The completed event, or None if not found
        """
        if event_id in self.active_events:
            event = self.active_events.pop(event_id)
            event.status = EventStatus.COMPLETED
            event.end_tick = current_tick
            self.completed_events.append(event)
            
            logger.info(f"✅ Completed: {event.title}")
            return event
        
        return None
        
    def update_active_events(self, current_tick: int) -> None:
        """
        Update all active events - complete those past their duration.
        
        Args:
            current_tick: Current tick
        """
        to_complete = []
        
        for event_id, event in self.active_events.items():
            if event.start_tick is not None:
                elapsed = current_tick - event.start_tick
                if elapsed >= event.duration_ticks:
                    to_complete.append(event_id)
                    
        for event_id in to_complete:
            self.complete_event(event_id, current_tick)
            
    def get_upcoming_events(self, limit: int = 10) -> List[Event]:
        """
        Get the next N scheduled events without removing them.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of upcoming events
        """
        events = []
        temp_queue = PriorityQueue()
        
        # Extract events
        while not self.queue.empty() and len(events) < limit:
            queued = self.queue.get()
            events.append(queued.event)
            temp_queue.put(queued)
            
        # Restore queue
        while not temp_queue.empty():
            self.queue.put(temp_queue.get())
            
        return events
        
    def get_stats(self) -> dict:
        """Get queue statistics"""
        return {
            "queued": self.queue.qsize(),
            "active": len(self.active_events),
            "completed": len(self.completed_events),
            "total_scheduled": self.total_scheduled,
            "total_processed": self.total_processed
        }