"""
AI Prompt Templates for Autonomous Character Decisions
"""

AUTONOMOUS_DECISION_PROMPT = """You are helping a character in an autonomous world simulation decide what to do next.

# CHARACTER CONTEXT
Name: {character_name}
Current Location: {location_name} ({location_description})
Location ID: {location_id}
Current State: {character_state}
Active Goals: {goals}

# MOTIVATIONAL STATE
Needs:
- Belonging: {belonging}/100
- Autonomy: {autonomy}/100
- Security: {security}/100
- Competence: {competence}/100
- Novelty: {novelty}/100

Emotional State:
- Stress: {stress}/100
- Current Mood: {mood}

# NEARBY CHARACTERS
{nearby_characters}

# CONNECTED LOCATIONS (with IDs)
{connected_locations}

# RECENT MEMORIES
{recent_memories}

# RECENT ACTIONS
{recent_actions}

# CURRENT TIME
Tick: {current_tick}
Last action: {ticks_since_last_action} ticks ago

---

Based on this context, what should {character_name} do next?

Choose ONE action type from:
1. STAY - Stay at current location and rest/observe
2. TRAVEL - Move to a connected location
3. INTERACT - Initiate interaction with a nearby character
4. EXPLORE - Explore the current location
5. WORK - Do productive work related to goals
6. REFLECT - Internal reflection/planning

Respond in this EXACT JSON format:
{{
  "action_type": "TRAVEL|STAY|INTERACT|EXPLORE|WORK|REFLECT",
  "reasoning": "Brief explanation of why this action makes sense",
  "target": "LOCATION_ID or character_id if applicable, otherwise null",
  "duration": 5,
  "priority": 3,
  "expected_outcome": "What the character hopes will happen"
}}

CRITICAL INSTRUCTIONS:
- For TRAVEL action, "target" MUST be a location_id (e.g., "village_alpha", NOT "Village Alpha")
- For INTERACT action, "target" MUST be a character_id
- Consider the character's motivational needs
- Higher stress = prefer STAY or REFLECT
- Low belonging = prefer INTERACT
- Low novelty = prefer EXPLORE or TRAVEL
- Don't repeat the same action too frequently
- Be realistic about travel times
- AVOID repeating recent actions: {recent_actions}
"""

INTERACTION_DIALOGUE_PROMPT = """Two characters are meeting. Generate a brief interaction.

# CHARACTER A
Name: {char_a_name}
Goals: {char_a_goals}
Mood: {char_a_mood}
Relationship to B: Trust {trust_ab}, Respect {respect_ab}

# CHARACTER B
Name: {char_b_name}
Goals: {char_b_goals}
Mood: {char_b_mood}
Relationship to A: Trust {trust_ba}, Respect {respect_ba}

# CONTEXT
Location: {location_name}
Situation: {situation}

Generate a brief (2-3 exchange) dialogue that:
1. Reflects their current emotional states
2. Moves their relationship forward (or backward)
3. Is relevant to their goals

Format:
{{
  "dialogue": [
    {{"speaker": "{char_a_name}", "text": "..."}},
    {{"speaker": "{char_b_name}", "text": "..."}},
    {{"speaker": "{char_a_name}", "text": "..."}}
  ],
  "outcome": "Brief description of how this affected their relationship",
  "trust_change_a": 5,
  "trust_change_b": 3
}}
"""

WORLD_EVENT_GENERATION_PROMPT = """You are the narrative director of a living world. Generate an interesting event.

# WORLD STATE
Current Tick: {current_tick}
Active Characters: {num_characters}
Locations: {locations}
Factions: {factions}

# RECENT EVENTS
{recent_events}

# NARRATIVE TENSION
Current tension level: {tension_level}/100
Stagnant areas: {stagnant_areas}

Generate ONE event that:
1. Creates interesting situations for characters
2. Advances faction goals or conflicts
3. Introduces challenges or opportunities
4. Increases narrative tension if it's too low

Event types:
- DISCOVERY: Something new is found
- CONFLICT: Tension between characters/factions
- OPPORTUNITY: A chance for characters to achieve goals
- DISASTER: Environmental or social crisis
- CELEBRATION: Positive community event

Respond in JSON:
{{
  "event_type": "DISCOVERY|CONFLICT|OPPORTUNITY|DISASTER|CELEBRATION",
  "title": "Short event title",
  "description": "Detailed description",
  "location_id": "where it happens",
  "affected_characters": ["char_id1", "char_id2"],
  "scheduled_in_ticks": 10,
  "duration_ticks": 5,
  "priority": 2,
  "impact": {{
    "tension_change": 20,
    "description": "What changes as a result"
  }}
}}
"""