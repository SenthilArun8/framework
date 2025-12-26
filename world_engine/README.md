# World Engine

**Autonomous World Simulation Layer**

An asynchronous, event-driven world simulation engine that extends the Living Character AI Framework with persistent, autonomous world behavior. Characters continue to live, interact, and evolve even when not directly engaged by users.

---

## Overview

The World Engine transforms the turn-based character system into a continuous, living world simulation. While the main framework handles direct user interactions, the World Engine manages:

- **Autonomous character behavior** - Characters act independently based on their psychological state
- **World events** - Dynamic events scheduled and processed over time
- **Spatial simulation** - Characters move between locations
- **Faction dynamics** - Organizations with relationships and conflicts
- **Persistent state** - World continues between sessions
- **Epistemic architecture** - Three-layer information system separating objective truth from belief

### Key Innovation: Epistemic Architecture

The World Engine implements a **three-layer epistemic system** that separates what actually happens from what characters believe:

1. **Objective World** (Layer 1) - Engine truth, perfect fidelity, characters don't access directly
2. **Information Artifacts** (Layer 2) - Reports, observations, rumors that can be outdated, partial, or false
3. **Belief Graph** (Layer 3) - Who believes what, with what confidence, and why

This enables:
- **Misinformation and rumor spread**
- **Trust dynamics affecting belief formation**
- **Characters operating on imperfect information**
- **Contradictions and cognitive dissonance**
- **Information asymmetry between characters**

### Architecture Philosophy

```
Main Framework (Turn-Based)          World Engine (Continuous)
─────────────────────────             ────────────────────────
User Input → Response                 Tick → Update → Event → Tick
                                              ↓
                                         Characters act autonomously
                                              ↓
                                    Epistemic Layers (3-tier truth model)
```

The World Engine runs in parallel with the main character system, allowing characters to:
- Make decisions when idle
- Travel between locations
- Interact with other characters
- Pursue goals over multiple ticks
- React to world events

---

## Core Components

### 1. World Ticker ([core/ticker.py](core/ticker.py))

**The heartbeat of the simulation.**

```python
WorldTicker:
    - tick_interval: float          # Seconds between ticks
    - current_tick: int             # Current simulation time
    - callbacks: List[Callable]     # Registered update functions
```

**Responsibilities**:
- Advances simulation time at regular intervals
- Invokes registered callbacks each tick
- Tracks simulation statistics

**Usage**:
```python
ticker = WorldTicker(tick_interval=5.0)  # 5 seconds per tick
ticker.register_callback(update_characters)
ticker.register_callback(process_events)
await ticker.start()  # Runs indefinitely
```

### 2. Event Queue ([core/event_queue.py](core/event_queue.py))

**Manages scheduled and active events.**

```python
EventQueue:
    - scheduled: Dict[int, List[Event]]  # Events scheduled for future ticks
    - active: List[Event]                # Currently executing events
```

**Capabilities**:
- Schedule events for future ticks
- Process events when they're due
- Track active events (multi-tick duration)
- Complete events and apply their effects

**Event Types**:
- `CHARACTER_TRAVEL` - Character moving between locations
- `CHARACTER_ACTION` - Generic character action
- `CHARACTER_INTERACTION` - Multiple characters interacting
- `FACTION_ACTION` - Faction-level event
- `WORLD_EVENT` - Large-scale narrative event

### 3. World State ([core/world_state.py](core/world_state.py))

**Purpose**: ⚠️ **REFACTORED** - Now a coordination layer, no longer source of truth.

```python
WorldState:
    # Epistemic layers (NEW)
    - objective_world: ObjectiveWorld
    - artifact_store: InformationArtifactStore
    - belief_graph: BeliefGraph
    - perception: PerceptionSystem
    
    # Entity stores (still needed for non-epistemic data)
    - characters: Dict[str, WorldCharacter]
    - locations: Dict[str, Location]
    - factions: Dict[str, Faction]
    - events: Dict[str, Event]
    - current_tick: int
```

**Responsibilities**:
- Coordinate between epistemic layers
- Route updates to objective world
- Manage perception and belief formation
- Provide convenience query methods
- Persist state to disk
- Load state from disk

**Key Change**: WorldState no longer stores facts directly. Instead:
1. Facts go to `ObjectiveWorld` (immutable truth)
2. Perception creates `InformationArtifacts` from facts
3. Characters form `Beliefs` about artifacts
4. WorldState coordinates these layers

**Key Methods**:
```python
world_state.add_character(character)
world_state.move_character(char_id, location_id)
world_state.get_active_characters()
world_state.get_nearby_characters(char_id)
world_state.save_to_disk()
world_state.load_from_disk()
```

### 4. Spatial System ([core/spatial.py](core/spatial.py))

**Manages location-based logic.**

- Distance calculations
- Travel time computation
- Proximity queries
- Path finding (basic)

---

## Epistemic System (NEW)

The epistemic system implements a three-layer architecture that separates objective reality from subjective belief.

### Layer 1: Objective World ([epistemic/objective_world.py](epistemic/objective_world.py))

**Engine truth - what actually happened.**

```python
ObjectiveWorld:
    - fact_log: List[ObjectiveFact]        # Immutable, append-only
    - _facts_by_tick: Dict[int, List]     # Indexed for queries
    - _facts_by_subject: Dict[str, List]
    - current_character_states: Dict
    - current_location_states: Dict
```

**Properties**:
- Never forgets
- Never drifts or changes
- Never lies
- Never contradicts itself
- Append-only (facts are immutable)
- Characters do NOT query this directly

**ObjectiveFact**:
```python
ObjectiveFact:
    fact_id: str
    tick: int                     # When it happened
    fact_type: str                # "character_moved", "event_occurred"
    subject: str                  # Who/what it's about
    data: dict                    # The actual facts
    observers: Set[str]           # Who was present
```

### Layer 2: Information Artifacts ([epistemic/information_artifacts.py](epistemic/information_artifacts.py))

**Information that characters actually encounter.**

```python
InformationArtifact:
    artifact_id: str
    created_at_tick: int          # When info was created (not when event happened)
    artifact_type: ArtifactType
    subject: str
    claim: str                    # Human-readable claim
    data: dict
    source: str                   # Who generated this
    reliability: ReliabilityLevel
    superseded_by: Optional[str]  # Newer info
    contradicts: Set[str]         # Conflicting artifacts
    known_by: Set[str]            # Who knows this
```

**Artifact Types**:
- `DIRECT_OBSERVATION` - Character saw it themselves (CERTAIN)
- `REPORT` - Someone told them (CONFIDENT/PROBABLE)
- `RUMOR` - Heard through grapevine (UNCERTAIN/DUBIOUS)
- `MESSAGE` - Explicit communication
- `DEDUCTION` - Inferred from other info
- `MEMORY` - Recalled from past

**Key Properties**:
- Can be outdated
- Can be partial
- Can be contradictory
- Can be false
- Has provenance (source tracking)
- Can supersede older information

### Layer 3: Belief Graph ([epistemic/belief_graph.py](epistemic/belief_graph.py))

**Who believes what, with what confidence, and why.**

```python
Belief:
    character_id: str
    artifact_id: str
    belief_state: BeliefState     # CONVINCED to REJECTED
    confidence: float             # 0.0-1.0
    justification: str
    based_on: List[str]           # Supporting artifacts
    formed_at_tick: int
    times_reinforced: int
    times_challenged: int
```

**Belief States**:
- `CONVINCED` - Absolutely believes it
- `CONFIDENT` - Strongly believes it
- `LEANING_TRUE` - Probably believes it
- `UNCERTAIN` - No strong opinion
- `LEANING_FALSE` - Probably disbelieves it
- `SKEPTICAL` - Strongly disbelieves it
- `REJECTED` - Absolutely disbelieves it

**Belief Formation Factors**:
- Trust in source (from PsychologicalProfile relationships)
- Character's base skepticism
- Artifact reliability level
- Contradicting artifacts
- Supporting evidence
- Character's cognitive state

### Perception System ([epistemic/perception.py](epistemic/perception.py))

**Bridge between objective facts and information artifacts.**

```python
PerceptionSystem:
    - process_direct_observation()  # Creates CERTAIN artifact
    - process_report()              # Creates CONFIDENT/PROBABLE artifact
    - process_rumor()               # Creates UNCERTAIN/DUBIOUS artifact
    - spread_information()          # Gossip mechanics
```

**Process Flow**:
```
Objective Fact → Perception System → Information Artifact → Belief Graph
     ↓                   ↓                      ↓                 ↓
Engine Truth      Who observed?        What they know      What they believe
```

---

## Entities

### WorldCharacter ([entities/character.py](entities/character.py))

**World-level character representation that extends PsychologicalProfile.**

```python
WorldCharacter:
    # Identity
    id: str
    profile_path: str                      # Path to character.json
    
    # Spatial
    current_location: str
    destination: Optional[str]
    
    # State
    state: CharacterState                  # IDLE, TRAVELING, etc.
    last_action_tick: int
    
    # Runtime (loaded from profile)
    profile: Optional[PsychologicalProfile]
    motivational_state: Optional[MotivationalState]
```

**⚠️ Epistemic Integration**: Characters now operate on **beliefs**, not objective facts:
- `get_beliefs(character_id)` - What this character believes
- `get_known_artifacts(character_id)` - Information they've encountered
- Trust levels affect belief formation
- Characters can have false or outdated beliefs

**Character States**:
- `IDLE` - Available for actions
- `TRAVELING` - Moving between locations
- `IN_CONVERSATION` - Interacting with others
- `IN_COMBAT` - Fighting (future)
- `RESTING` - Recovering
- `WORKING` - Performing task
- `EXPLORING` - Discovering new areas

### Location ([entities/location.py](entities/location.py))

**Physical places in the world.**

```python
Location:
    id: str
    name: str
    description: str
    location_type: LocationType            # CITY, WILDERNESS, etc.
    coordinates: Tuple[float, float]       # X, Y position
    connected_to: List[str]                # Reachable locations
    properties: Dict[str, Any]             # Custom attributes
```

**Location Types**:
- `CITY` - Urban settlement
- `VILLAGE` - Small settlement
- `WILDERNESS` - Natural area
- `DUNGEON` - Enclosed dangerous area
- `LANDMARK` - Notable location

### Event ([entities/event.py](entities/event.py))

**Scheduled or active happenings.**

```python
Event:
    id: str
    title: str
    description: str
    type: EventType
    
    # Timing
    scheduled_tick: int                    # When it starts
    duration_ticks: int                    # How long it lasts
    completion_tick: Optional[int]         # When it finished
    
    # Participants
    participants: List[str]                # Character IDs
    location: str                          # Where it happens
    
    # Effects
    impact: Dict[str, Any]                 # What changes
    status: EventStatus                    # SCHEDULED, ACTIVE, COMPLETED
```

### Faction ([entities/faction.py](entities/faction.py))

**Organizations and groups.**

```python
Faction:
    id: str
    name: str
    type: FactionType                      # GUILD, GOVERNMENT, etc.
    description: str
    
    members: List[str]                     # Character IDs
    leader: Optional[str]
    
    relations: Dict[str, FactionRelation]  # Relations with other factions
    territory: List[str]                   # Controlled locations
    resources: Dict[str, float]            # Assets
```

---

## AI Systems

### Action Generator ([ai/action_generator.py](ai/action_generator.py))

**Decides what characters should do autonomously.**

```python
async def decide_action(
    character: WorldCharacter,
    world_state: WorldState,
    current_tick: int
) -> Optional[Dict[str, Any]]
```

**Process**:
1. Analyze character's psychological state
2. Consider current location and nearby entities
3. Evaluate available actions
4. Generate action decision with reasoning
5. Return structured action (or None if character should rest)

**Action Types**:
- `TRAVEL` - Move to new location
- `EXPLORE` - Investigate current area
- `INTERACT` - Approach another character
- `REST` - Recover/idle
- `WORK` - Perform activity

### Narrative Director ([ai/director.py](ai/director.py))

**Creates world-level dramatic events.**

```python
async def should_generate_event(
    world_state: WorldState,
    tick: int
) -> bool

async def generate_world_event(
    world_state: WorldState,
    tick: int
) -> Optional[Event]
```

**Responsibilities**:
- Monitor world state for narrative opportunities
- Generate dramatic events (conflicts, discoveries, etc.)
- Balance pacing and intensity
- Create multi-character storylines

### Autonomous Pipeline ([ai/autonomous_pipeline.py](ai/autonomous_pipeline.py))

**Lightweight adapter for autonomous decisions.**

Currently a simplified wrapper around ActionGenerator. Future integration will connect the full LangGraph pipeline from the main framework:
- Memory retrieval
- Motivational analysis
- Subconscious reasoning
- Delta updates
- Action planning

---

## Running the Simulation

### Basic Usage

```python
from world_engine.main import WorldSimulation

# Create simulation
simulation = WorldSimulation(
    tick_interval=5.0,        # 5 seconds per tick
    data_dir="world_data",    # Where to save state
    load_existing=True        # Resume previous world
)

# Start simulation (runs indefinitely)
await simulation.start()
```

### Command Line

```bash
# Start world simulation
cd world_engine
python main.py

# The simulation runs continuously, logging events to:
# - Console (INFO level)
# - world_engine/logs/simulation.log
```

### Configuration

**Tick Interval**: How often the world updates (default: 5 seconds)
- Faster = More responsive, higher CPU usage
- Slower = Less frequent updates, lower CPU usage

**Autosave**: World state saved every N ticks (default: 100)

**Data Directory**: Where world state is persisted (default: `world_data/`)

---

## Integration with Main Framework

### Character Profiles

World characters link to existing `character.json` files:

```python
world_character = WorldCharacter(
    id="elias",
    profile_path="character.json",  # Uses existing profile
    current_location="sanctuary"
)

# Profile is loaded at runtime
world_character.load_profile()
```

This ensures:
- **Single source of truth** - Profile changes reflect in both systems
- **Consistent personality** - Same psychological model
- **Shared memory** - Character remembers interactions

### Motivational State

The World Engine respects the character's motivational state:
- Characters with high stress may avoid social interactions
- Low belonging need may drive characters to seek others
- Cognitive load affects decision complexity

### Memory Formation

When characters interact in the world, significant events are:
1. Logged as events in WorldState
2. Added to the character's ChromaDB memory store
3. Reflected in the knowledge graph (Neo4j)

---

## File Structure

```
world_engine/
├── README.md                    # This file
├── main.py                      # Main simulation orchestrator
├── __init__.py
│
├── core/                        # Core simulation systems
│   ├── __init__.py
│   ├── ticker.py                # Time progression
│   ├── event_queue.py           # Event scheduling/processing
│   ├── world_state.py           # Coordination layer (refactored)
│   └── spatial.py               # Location & distance logic
│
├── epistemic/                   # ✨ NEW: 3-layer epistemic system
│   ├── __init__.py
│   ├── objective_world.py       # Layer 1: Engine truth
│   ├── information_artifacts.py # Layer 2: What characters encounter
│   ├── belief_graph.py          # Layer 3: What characters believe
│   └── perception.py            # Bridge between layers
│
├── entities/                    # World entities
│   ├── __init__.py
│   ├── character.py             # WorldCharacter
│   ├── location.py              # Location
│   ├── event.py                 # Event
│   └── faction.py               # Faction
│
├── ai/                          # AI decision systems
│   ├── __init__.py
│   ├── action_generator.py      # Character action decisions
│   ├── director.py              # Narrative event generation
│   ├── autonomous_pipeline.py   # Decision pipeline adapter
│   └── prompts.py               # LLM prompts
│
├── api/                         # REST API (future)
│   └── __init__.py
│
├── utils/                       # Utilities
│   └── __init__.py
│
└── logs/                        # Simulation logs
    └── simulation.log
```

---

## Data Persistence

### World State Files

Saved to `{data_dir}/` (default: `world_data/`):

```
world_data/
├── world_state.json             # Main state snapshot
├── objective/                   # ✨ NEW: Objective world (Layer 1)
│   ├── fact_log.json            # Immutable fact history
│   └── indices.json             # Fast lookup indices
├── artifacts/                   # ✨ NEW: Information artifacts (Layer 2)
│   └── artifacts.json
├── beliefs/                     # ✨ NEW: Belief graph (Layer 3)
│   └── beliefs_by_character.json
├── characters/                  # Individual character data
│   ├── elias.json
│   └── maria.json
├── locations/                   # Location data
│   └── sanctuary.json
├── factions/                    # Faction data
│   └── resistance.json
└── events/                      # Event history
    └── events_log.json
```

### Autosave

- **Frequency**: Every 100 ticks (configurable)
- **Method**: Asynchronous write to JSON
- **Safety**: Writes to temporary file first, then renames

### Manual Save/Load

```python
# Save current state
simulation.world_state.save_to_disk()

# Load existing state
simulation.world_state.load_from_disk()
```

---

## Development Status

### ✅ Implemented (Phase 1 & 2)

- Core ticker system
- Event queue and scheduling
- World state management
- Basic character entities
- Location system
- Simple AI action generation
- Logging and persistence
- **✨ Three-layer epistemic architecture**
- **✨ Objective world (immutable fact log)**
- **✨ Information artifact system**
- **✨ Belief graph with confidence tracking**
- **✨ Perception system (observation → artifact)**

### 🚧 In Progress (Phase 2.5)

- Full LangGraph integration with epistemic queries
- Character-to-character interactions with misinformation
- Faction dynamics
- Narrative director enhancements
- Gossip and rumor spread mechanics

### 📋 Planned (Phase 3+)

- REST API for external access
- Web-based world viewer with epistemic visualization
- Multi-character conversations with belief divergence
- Information warfare and deception
- Economic simulation
- Combat system with fog of war
- Quest generation based on information asymmetry
- Player character integration
- Detective/investigation gameplay
- Trust erosion and repair mechanics

---

## Example: Demo World

The simulation creates a demo world with:

**Characters**:
- Elias (using existing profile from main framework)
- Maria (new character)

**Locations**:
- Sanctuary (safe city)
- Borderlands (wilderness)
- Ruins (dangerous exploration site)

**Initial Events**:
- Characters start in Sanctuary
- Elias may travel to explore based on autonomy need
- Maria works in Sanctuary

**What Happens**:
1. Ticker starts, advancing every 5 seconds
2. Characters evaluate their psychological state
3. AI decides actions (travel, explore, rest)
4. Events are scheduled and executed
5. World state updates
6. State autosaves every 100 ticks

---

## Logging

### Log Levels

- `INFO` - Normal simulation events (tick updates, character actions)
- `WARNING` - Unusual but non-critical events
- `ERROR` - Failed operations

### Log Locations

- **Console**: Real-time streaming
- **File**: `world_engine/logs/simulation.log`

### Example Log Output

```
2025-12-24 10:00:00 - __main__ - INFO - 🌍 World simulation started at tick 0
2025-12-24 10:00:00 - __main__ - INFO - ⏱️  Tick interval: 5.0s
2025-12-24 10:00:05 - __main__ - INFO - 📊 World Status: 2 active characters, 0 active events
2025-12-24 10:00:10 - __main__ - INFO - 🎯 Character 'elias' decided to TRAVEL to ruins
2025-12-24 10:00:10 - __main__ - INFO - ⚡ Executing: Elias travels to Ruins
```

---

## Performance Considerations

### Tick Interval Selection

```
1 second   → Very responsive, high CPU usage
5 seconds  → Balanced (recommended)
10 seconds → Slower but efficient
30 seconds → Background simulation
```

### Scaling

Current system handles:
- 10-50 characters comfortably
- 5-10 active events simultaneously
- 20-30 locations

For larger worlds, consider:
- Increasing tick interval
- Spatial partitioning (only update nearby characters)
- Event pooling

---

## API Integration (Future)

Planned REST API endpoints:

```
GET  /world/status              # Current world state
GET  /characters                # List all characters
GET  /characters/{id}           # Character details
GET  /locations                 # List all locations
GET  /events                    # Recent events
POST /events                    # Schedule event
GET  /simulation/stats          # Performance metrics
```

---

## Troubleshooting

### Simulation Not Starting

**Check**:
- Python 3.10+ installed
- Required dependencies installed (`pip install -r requirements.txt`)
- No port conflicts if running with API

### Characters Not Acting

**Possible Causes**:
- Character state is not `IDLE` (check if stuck in `TRAVELING`)
- Cooldown period (check `last_action_tick`)
- LLM API issues (check logs for errors)

### High CPU Usage

**Solutions**:
- Increase tick interval
- Reduce number of active characters
- Disable verbose logging

### State Not Persisting

**Check**:
- Write permissions in `data_dir`
- Disk space available
- Autosave enabled (default: yes)

---

## Contributing

When adding new features:

1. **Entities**: Add to `entities/` with Pydantic models
2. **AI Logic**: Extend `ai/action_generator.py` or `ai/director.py`
3. **Core Systems**: Modify `core/` components carefully (affects all entities)
4. **Integration**: Ensure compatibility with main framework's character profiles

---

## Related Documentation

- [Main Framework README](../README.md) - Parent system overview
- [Architecture Documentation](../updated_architecture.md) - Full system architecture
- [Character Schema](../src/schema.py) - PsychologicalProfile and MotivationalState

---

## License

Part of the Living Character AI Framework.

**Version**: 2.0  
**Status**: Alpha (Phase 2 Complete - Epistemic Architecture)  
**Last Updated**: December 25, 2025
