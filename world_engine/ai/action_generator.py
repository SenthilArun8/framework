"""
Action Generator - Decides what characters do autonomously
"""
import json
import logging
from typing import Optional, Dict, Any
import sys
from pathlib import Path

# Import LLM client from existing framework
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.llm_client import get_llm

from .prompts import AUTONOMOUS_DECISION_PROMPT, INTERACTION_DIALOGUE_PROMPT
from ..entities.character import WorldCharacter
from ..entities.location import Location
from ..entities.event import Event, EventType

logger = logging.getLogger(__name__)


class ActionGenerator:
    """
    Generates autonomous actions for characters using LLM.
    """
    
    def __init__(self):
        self.llm = get_llm()
        self.action_history = {}  # Track recent actions to avoid repetition
        
    async def decide_action(
        self,
        character: WorldCharacter,
        world_state,
        current_tick: int
    ) -> Optional[Dict[str, Any]]:
        """
        Decide what action a character should take.
        
        Args:
            character: The character making a decision
            world_state: Current world state
            current_tick: Current simulation tick
            
        Returns:
            Action decision dict or None if character shouldn't act yet
        """
        # Check if character acted recently
        ticks_since_last = current_tick - character.last_action_tick
        
        # Don't act every single tick - add some variation
        if ticks_since_last < 5:  # Wait at least 5 ticks between actions
            return None
        
        # Gather context
        context = self._gather_context(character, world_state, current_tick)
        
        # Build prompt
        prompt = self._build_decision_prompt(context)
        
        try:
            # Call LLM
            logger.info(f"🤔 {character.id} is deciding what to do...")
            response = await self.llm.ainvoke(prompt)
            
            # Parse response
            action = self._parse_action_response(response.content)
            
            if action:
                logger.info(
                    f"  ✓ Decided: {action['action_type']} - {action['reasoning']}"
                )
                
                # Track action
                self._track_action(character.id, action['action_type'])
                
                return action
            
        except Exception as e:
            logger.error(f"Error generating action for {character.id}: {e}")
            return None
    
    def _gather_context(
        self,
        character: WorldCharacter,
        world_state,
        current_tick: int
    ) -> Dict[str, Any]:
        """Gather all relevant context for decision-making"""
        
        # Get location
        location = world_state.get_location(character.location_id)
        
        # Get nearby characters
        nearby = world_state.get_nearby_characters(character.id)
        
        # Get connected locations
        connected = world_state.get_connected_locations(character.location_id)
        
        # Load character's psychological profile if not loaded
        if not character.profile:
            # For now, use placeholder - we'll integrate full profile loading later
            motivational = {
                'belonging': 50,
                'autonomy': 50,
                'security': 50,
                'competence': 50,
                'novelty': 50,
                'stress': 30,
                'mood': 'neutral'
            }
        else:
            # Extract from loaded profile
            motivational = {
                'belonging': getattr(character.motivational_state.needs, 'belonging', 50),
                'autonomy': getattr(character.motivational_state.needs, 'autonomy', 50),
                'security': getattr(character.motivational_state.needs, 'security', 50),
                'competence': getattr(character.motivational_state.needs, 'competence', 50),
                'novelty': getattr(character.motivational_state.needs, 'novelty', 50),
                'stress': getattr(character.motivational_state.emotional_state, 'stress', 30),
                'mood': character.profile.current_mood
            }
        
        return {
            'character': character,
            'location': location,
            'nearby_characters': nearby,
            'connected_locations': connected,
            'motivational': motivational,
            'current_tick': current_tick,
            'ticks_since_last_action': current_tick - character.last_action_tick
        }
    
    def _build_decision_prompt(self, context: Dict[str, Any]) -> str:
        """Build the decision prompt from context"""
        
        character = context['character']
        location = context['location']
        motivational = context['motivational']
        
        # Format nearby characters
        nearby_text = "None"
        if context['nearby_characters']:
            nearby_text = "\n".join([
                f"- {c.id} (state: {c.state})"
                for c in context['nearby_characters']
            ])
        
        # ✅ FIXED: Format connected locations WITH IDs
        connected_text = "None"
        if context['connected_locations']:
            connected_text = "\n".join([
                f"- {loc.name} (ID: {loc.id}, {loc.travel_times.get(character.location_id, '?')} ticks away)"
                for loc in context['connected_locations']
            ])
        
        # Get recent action history to discourage repetition
        recent_actions = "None"
        if character.id in self.action_history:
            recent_actions = ", ".join(self.action_history[character.id][-3:])
        
        prompt = AUTONOMOUS_DECISION_PROMPT.format(
            character_name=character.id,
            location_name=location.name,
            location_description=location.description,
            location_id=location.id,  # ✅ NEW: Add location ID
            character_state=character.state.value,
            goals=", ".join(character.active_goals) or "None",
            belonging=int(motivational['belonging']),
            autonomy=int(motivational['autonomy']),
            security=int(motivational['security']),
            competence=int(motivational['competence']),
            novelty=int(motivational['novelty']),
            stress=int(motivational['stress']),
            mood=motivational['mood'],
            nearby_characters=nearby_text,
            connected_locations=connected_text,
            recent_memories="[Not yet implemented]",
            recent_actions=recent_actions,  # ✅ NEW
            current_tick=context['current_tick'],
            ticks_since_last_action=context['ticks_since_last_action']
        )
        
        return prompt
    
    def _parse_action_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response into action dict"""
        try:
            # Extract JSON from response
            # Sometimes LLM wraps in markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            action = json.loads(response.strip())
            
            # Validate required fields
            required = ['action_type', 'reasoning']
            if not all(field in action for field in required):
                logger.error(f"Missing required fields in action: {action}")
                return None
            
            # Set defaults
            action.setdefault('target', None)
            action.setdefault('duration', 5)
            action.setdefault('priority', 3)
            action.setdefault('expected_outcome', '')
            
            return action
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse action JSON: {e}\nResponse: {response}")
            return None
    
    def _track_action(self, character_id: str, action_type: str):
        """Track action to avoid repetition"""
        if character_id not in self.action_history:
            self.action_history[character_id] = []
        
        self.action_history[character_id].append(action_type)
        
        # Keep only last 5 actions
        if len(self.action_history[character_id]) > 5:
            self.action_history[character_id].pop(0)
    
    def create_event_from_action(
    self,
    character: WorldCharacter,
    action: Dict[str, Any],
    current_tick: int
) -> Event:
        """
        Convert an action decision into a schedulable event.
        
        Args:
            character: Character performing action
            action: Action decision from LLM
            current_tick: Current tick
            
        Returns:
            Event object ready to be scheduled
        """
        action_type = action['action_type']
        
        # Map action types to event types
        event_type_map = {
            'TRAVEL': EventType.CHARACTER_TRAVEL,
            'INTERACT': EventType.CHARACTER_INTERACTION,
            'STAY': EventType.CHARACTER_ACTION,
            'EXPLORE': EventType.CHARACTER_ACTION,
            'WORK': EventType.CHARACTER_ACTION,
            'REFLECT': EventType.CHARACTER_ACTION
        }
        
        event_type = event_type_map.get(action_type, EventType.CHARACTER_ACTION)
        
        # ✅ NEW: Validate target for TRAVEL actions
        target = action.get('target')
        if action_type == 'TRAVEL' and target:
            # Ensure target is lowercase and formatted properly
            target = target.lower().replace(' ', '_')
        
        # Build event
        event = Event(
            id=f"evt_{action_type.lower()}_{character.id}_{current_tick}",
            type=event_type,
            scheduled_tick=current_tick + 1,  # Next tick
            duration_ticks=action.get('duration', 5),
            location_id=character.location_id,
            participants=[character.id],
            title=f"{character.id}: {action_type}",
            description=action.get('reasoning', ''),
            impact={
                'action_type': action_type,
                'target': target,
                'expected_outcome': action.get('expected_outcome', ''),
                'destination': target if action_type == 'TRAVEL' else None
            },
            priority=action.get('priority', 3)
        )
        
        return event
    
    async def generate_interaction_dialogue(
        self,
        char_a: WorldCharacter,
        char_b: WorldCharacter,
        location: Location,
        situation: str = "They meet by chance"
    ) -> Optional[Dict[str, Any]]:
        """
        Generate dialogue for character interaction.
        
        Args:
            char_a: First character
            char_b: Second character
            location: Where they're meeting
            situation: Context for the interaction
            
        Returns:
            Dialogue and relationship changes
        """
        try:
            prompt = INTERACTION_DIALOGUE_PROMPT.format(
                char_a_name=char_a.id,
                char_a_goals=", ".join(char_a.active_goals),
                char_a_mood="neutral",  # Placeholder
                trust_ab=50,  # Placeholder
                respect_ab=50,  # Placeholder
                char_b_name=char_b.id,
                char_b_goals=", ".join(char_b.active_goals),
                char_b_mood="neutral",  # Placeholder
                trust_ba=50,  # Placeholder
                respect_ba=50,  # Placeholder
                location_name=location.name,
                situation=situation
            )
            
            response = await self.llm.ainvoke(prompt)
            
            # Parse response
            if "```json" in response.content:
                json_str = response.content.split("```json")[1].split("```")[0]
            else:
                json_str = response.content
            
            dialogue_data = json.loads(json_str.strip())
            
            logger.info(f"💬 Generated dialogue between {char_a.id} and {char_b.id}")
            
            return dialogue_data
            
        except Exception as e:
            logger.error(f"Error generating dialogue: {e}")
            return None
    def _gather_context(
    self,
    character: WorldCharacter,
    world_state,
    current_tick: int
) -> Dict[str, Any]:
        """Gather all relevant context for decision-making"""
        
        # Get location (use objective for now, but could use believed location)
        location = world_state.get_location(character.location_id)
        
        # ✅ NEW: Get nearby characters based on character's BELIEFS
        nearby = []
        for other_char in world_state.get_active_characters():
            if other_char.id == character.id:
                continue
            
            # Where does this character BELIEVE the other is?
            believed_location = world_state.get_character_believed_location(
                character.id,
                other_char.id,
                current_tick
            )
            
            # If they believe other is here, include them
            if believed_location == character.location_id:
                nearby.append(other_char)
        
        # ✅ NEW: Get character's beliefs about this location
        location_beliefs = world_state.belief_graph.get_all_beliefs(
            character.id,
            min_confidence=0.5  # Only confident beliefs
        )
        
        # Get connected locations
        connected = world_state.get_connected_locations(character.location_id)
        
        # Get motivational state
        if not character.profile:
            motivational = {
                'belonging': 50,
                'autonomy': 50,
                'security': 50,
                'competence': 50,
                'novelty': 50,
                'stress': 30,
                'mood': 'neutral'
            }
        else:
            motivational = {
                'belonging': getattr(character.motivational_state.needs, 'belonging', 50),
                'autonomy': getattr(character.motivational_state.needs, 'autonomy', 50),
                'security': getattr(character.motivational_state.needs, 'security', 50),
                'competence': getattr(character.motivational_state.needs, 'competence', 50),
                'novelty': getattr(character.motivational_state.needs, 'novelty', 50),
                'stress': getattr(character.motivational_state.emotional_state, 'stress', 30),
                'mood': character.profile.current_mood
            }
        
        return {
            'character': character,
            'location': location,
            'nearby_characters': nearby,  # Based on beliefs!
            'connected_locations': connected,
            'motivational': motivational,
            'current_tick': current_tick,
            'ticks_since_last_action': current_tick - character.last_action_tick,
            'belief_stats': world_state.belief_graph.get_stats(character.id)  # NEW
        }