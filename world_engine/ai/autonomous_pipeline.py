"""
Autonomous Pipeline - Simplified version of LangGraph for autonomous decisions
This is a lightweight adapter until we fully integrate the existing pipeline
"""
import logging
from typing import Dict, Any, Optional

from .action_generator import ActionGenerator

logger = logging.getLogger(__name__)


class AutonomousPipeline:
    """
    Simplified autonomous decision pipeline.
    
    For Phase 1, this is a lightweight wrapper.
    Later we'll integrate the full LangGraph pipeline from src/graph.py
    """
    
    def __init__(self):
        self.action_generator = ActionGenerator()
        
    async def process_character(
        self,
        character,
        world_state,
        current_tick: int
    ) -> Optional[Dict[str, Any]]:
        """
        Process a character's turn - decide what they should do.
        
        Args:
            character: WorldCharacter instance
            world_state: WorldState instance
            current_tick: Current simulation tick
            
        Returns:
            Action decision or None if character shouldn't act
        """
        try:
            # For now, just use action generator
            # Later, this will be a full LangGraph pipeline with:
            # - Memory retrieval
            # - Motivational analysis
            # - Subconscious reasoning
            # - Action planning
            
            action = await self.action_generator.decide_action(
                character,
                world_state,
                current_tick
            )
            
            return action
            
        except Exception as e:
            logger.error(f"Error processing character {character.id}: {e}")
            return None