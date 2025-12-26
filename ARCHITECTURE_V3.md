# Living Character AI Framework - Architecture Documentation
**Version**: 3.0  
**Last Updated**: December 24, 2025  
**Status**: Production-Ready Multi-Phase System

---

## Executive Summary

This is a **stateful, turn-based conversational AI framework** that creates psychologically complex characters with:
- **Persistent episodic memory** (ChromaDB vector database)
- **Relational knowledge graph** (Neo4j)
- **Dynamic motivational system** (needs, emotions, attachment styles)
- **7-stage cognitive processing pipeline** (LangGraph)
- **Real-time observability dashboard** (SSE-based web interface)

The system does **not** implement autonomous goal pursuit or self-directed action. It reacts to user inputs and updates internal state synchronously per turn.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Core Components](#2-core-components)
3. [Data Flow & Processing Pipeline](#3-data-flow--processing-pipeline)
4. [Schema & Data Models](#4-schema--data-models)
5. [Memory Systems](#5-memory-systems)
6. [Motivational Engine](#6-motivational-engine)
7. [Dashboard & Observability](#7-dashboard--observability)
8. [File Structure](#8-file-structure)
9. [Integration & Configuration](#9-integration--configuration)
10. [Development History](#10-development-history)
11. [Technical Capabilities](#11-technical-capabilities)

---

## 1. System Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INPUT                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      GAME ENGINE (main.py)                       │
│  - Chat history management                                       │
│  - State orchestration                                           │
│  - Dashboard coordination                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                LANGGRAPH PROCESSING PIPELINE                     │
│                                                                   │
│  ┌─────────┐   ┌──────────────┐   ┌──────────────┐            │
│  │RETRIEVE │──>│ MOTIVATIONAL │──>│ SUBCONSCIOUS │            │
│  └─────────┘   └──────────────┘   └──────────────┘            │
│       │                                     │                    │
│       │         ┌─────────┐                │                    │
│       └────────>│  DELTA  │<───────────────┘                    │
│                 └────┬────┘                                      │
│                      │                                           │
│                 ┌────▼────┐   ┌────────┐   ┌──────────┐        │
│                 │PLANNING │──>│ LEARN  │──>│ GENERATE │        │
│                 └─────────┘   └────────┘   └─────┬────┘        │
│                                                    │             │
│                 ┌─────────┐                       │             │
│                 │ PERSIST │<──────────────────────┘             │
│                 └─────────┘                                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
    ┌────▼────┐  ┌────▼────┐  ┌────▼─────┐
    │ChromaDB │  │ Neo4j   │  │  JSON    │
    │(Vectors)│  │ (Graph) │  │(Profile) │
    └─────────┘  └─────────┘  └──────────┘
```

### Key Properties

- **Deterministic linear DAG** - No branching, no loops, no recursion
- **One pass per user message** - Synchronous turn-based processing
- **No mid-generation feedback** - All cognitive updates happen before response generation
- **Persistent state across sessions** - Profile, memories, and graph relationships maintained

---

## 2. Core Components

### 2.1 Game Engine ([main.py](main.py))

**Purpose**: Orchestrates all components and provides the CLI interface.

**Key Responsibilities**:
- Load/save character profile from `character.json`
- Initialize memory store and knowledge graph
- Build LangGraph pipeline
- Manage chat history (`data/chat_history.json`)
- Update dashboard state (`dashboard/live_state.json`)
- Display HUD console visualization

**Initialization Sequence**:
1. Load character profile (or create default)
2. Initialize motivational state from `DEFAULT_MOTIVATIONAL`
3. Seed vector database with backstory memories
4. Connect to Neo4j (graceful fallback if unavailable)
5. Ensure base relationships exist in graph
6. Build 7-stage LangGraph pipeline
7. Load chat history from JSON
8. Dump initial dashboard state

**Turn Processing Flow**:
```python
def process_turn(self, user_input):
    1. Append user message to chat_history
    2. Save chat_history.json immediately
    3. Create snapshot of old_profile (for delta comparison)
    4. Prepare AgentState input dictionary
    5. Invoke LangGraph pipeline
    6. Update profile from output
    7. Update motivational state from output
    8. Extract bot response
    9. Update knowledge graph with interaction data
    10. Save profile to character.json
    11. Export state to live_state.json
    12. Return bot message and analysis data
```

### 2.2 LangGraph Pipeline ([src/graph.py](src/graph.py))

**Purpose**: Defines the cognitive processing graph.

**Graph Structure**:
```python
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "motivational")
workflow.add_edge("motivational", "subconscious")
workflow.add_edge("subconscious", "delta")
workflow.add_edge("delta", "planning")
workflow.add_edge("planning", "learn")
workflow.add_edge("learn", "generate")
workflow.add_edge("generate", "persist")
workflow.add_edge("persist", END)
```

### 2.3 Agent State ([src/state.py](src/state.py))

**Purpose**: Mutable runtime container passed through the graph.

**Fields**:
```python
class AgentState(TypedDict):
    messages: List[BaseMessage]           # Full chat history
    profile: dict                         # Serialized PsychologicalProfile
    old_profile: dict                     # Snapshot for delta comparison
    motivational: dict                    # Serialized MotivationalState
    memories: list                        # Retrieved episodic memories
    subconscious_thought: str            # Internal monologue
    cognitive_frame: dict                # Structured output from subconscious
    cognitive_stack: List[dict]          # History of CognitiveFrames
    delta_history: List[dict]            # History of PersonalityDeltas
    planned_actions: List[str]           # Output from planning node
```

---

## 3. Data Flow & Processing Pipeline

### Stage 1: Retrieve Node ([src/nodes/retrieve.py](src/nodes/retrieve.py))

**Purpose**: Finds relevant memories and knowledge graph context.

**Process**:
1. **Emotional Query Expansion**:
   - Analyzes user input for emotional themes
   - Identifies specific entities (people, places, factions)
   - Creates memory search query biased by current emotional state

2. **Vector Search** (ChromaDB):
   - Retrieves top-5 relevant episodic memories
   - Weighted by `importance_score × emotional_intensity`
   - Proactive retrieval for active internal goals

3. **Semantic Graph RAG** (Neo4j):
   - Queries opinion paths for mentioned entities
   - Example: `Elias -[HATES]-> Empire -[DESTROYED]-> Home`
   - Creates synthetic memories from graph paths

**Output**: `memories` list (vector + graph results)

### Stage 2: Motivational Node ([src/motivational.py](src/motivational.py))

**Purpose**: Updates needs, emotions, and cognitive state. Selects behavioral strategy.

**Process**:
1. **Decay/Time-based Updates**:
   - Needs naturally drift over time
   - Security: -0.01 per turn
   - Novelty: -0.02 per turn
   - Fatigue: +0.05 per turn

2. **Intent Analysis** (LLM):
   ```
   Intent Types:
   - SUPPORT: +Belonging, -Stress
   - CRITICISM: -Competence, +Shame
   - THREAT: +Fear, -Security
   - CONTROL: -Autonomy, +Stress
   - NEGLECT: +Longing, -Belonging
   - CURIOSITY: +Novelty
   ```

3. **Pressure Calculation**:
   ```python
   Stress = stress × (1.0 - min(needs.security, needs.autonomy))
   Attachment = attachment.activation × longing
   Conflict = max(conflict.pressure for all conflicts)
   ```

4. **Strategy Blending**:
   - Calculates weighted mix of behavioral strategies
   - Example: `{"defensive_curt": 0.6, "fragmented_thoughts": 0.4}`
   - Trait-modulated by `emotional_volatility` and `focus_fragility`

5. **Cognitive Load**:
   - Increases based on input complexity (word count, question marks)
   - High load → fragmented thoughts, dissociation
   - Non-linear scaling: `complexity^1.5`

**Output**: Updated `motivational` state with `active_strategy`

### Stage 3: Subconscious Node ([src/nodes/subconscious.py](src/nodes/subconscious.py))

**Purpose**: Generates raw, unfiltered internal monologue.

**Features**:
- Reflects on input without social constraints
- Hypothesis testing ("Is the user trustworthy?")
- Memory-linked reasoning
- Outputs `CognitiveFrame`:
  ```python
  CognitiveFrame:
    - beliefs_held: List[str]
    - beliefs_rejected: List[str]
    - emotional_state: Dict[str, float]
    - linked_memories: List[str]
    - confidence_level: float
    - behavioral_constraints: List[str]
  ```

**Output**: `subconscious_thought` (string) + `cognitive_frame` (structured)

### Stage 4: Delta Node ([src/nodes/delta.py](src/nodes/delta.py))

**Purpose**: Updates psychological profile based on cognitive frame.

**Updates**:
1. **Mood Shift**: Transitions mood state
2. **Value Changes**:
   - Max change: ±0.05 per turn (clamped)
   - Modulated by `confidence_level` from cognitive frame
3. **Relationship Updates**:
   - **Trust gain**: Dampened by current trust level
     ```python
     damping_factor = (100 - current_trust) / 100.0
     real_change = raw_change × damping_factor
     ```
   - **Trust loss**: Amplified by 1.5×
   - Additional dampening if betrayal memories triggered

**Autonomy Logic**:
- **High cognitive load** (>0.7): Accept scaffolding, be compliant
- **Low cognitive load** (<0.7): Resist control, assert autonomy

**Output**: Updated `profile`, `delta_history` entry

### Stage 5: Planning Node ([src/nodes/planning.py](src/nodes/planning.py))

**Purpose**: Synthesizes memories, deltas, and motivational drives into multi-turn objectives.

**Process**:
1. **Goal Pursuit**: Match memories to active internal goals
2. **Conflict Resolution**: Identify high-pressure conflicts
3. **Action Planning**: Generate list of planned actions

**Output**: `planned_actions` list

### Stage 6: Learn Node ([src/nodes/learn.py](src/nodes/learn.py))

**Purpose**: Decides if interaction is significant enough to form permanent memory.

**Criteria**:
- High emotional intensity
- Value-challenging content
- Relationship state changes
- Novel information

**Output**: New memory added to vector store (side effect)

### Stage 7: Generate Node ([src/nodes/generate.py](src/nodes/generate.py))

**Purpose**: Produces final spoken response.

**Strategy Mapping**:
```python
STRATEGY_MAP = {
    "fragmented_thoughts": "Interrupted sentences (...), confused",
    "defensive_curt": "Short, sharp, defensive",
    "over_explaining_clingy": "Long justifications, apologies",
    "shutdown_withdrawal": "Concise, cold, one-word answers",
    "spaced_out_drifting": "Odd spacing, unrelated thoughts",
    "mixed_signals_hesitant": "Inconsistent, retracts statements",
    "argumentative_assertive": "Defensive, challenges user",
    "vulnerable_seeking": "Clingy, emotional self-disclosure",
    "hyper_vigilant": "Suspicious, clarifying questions",
    "needy_demanding": "Demands attention/answers",
    "neutral": "Normal speech consistent with mood"
}
```

**Output**: Final response message

### Stage 8: Persist Node ([src/nodes/persist.py](src/nodes/persist.py))

**Purpose**: Side effects—saves state to external systems.

**Actions**:
1. **Knowledge Graph Updates**: Add interaction events, update trust/respect edges
2. **Profile Persistence**: Save to `character.json`
3. **Delta History**: Append to `delta_history`

---

## 4. Schema & Data Models

### 4.1 Psychological Profile

```python
PsychologicalProfile:
    name: str                                # Character name
    current_mood: str                        # Current emotional state
    emotional_volatility: float              # 0.0-2.0
    values: Dict[str, CoreValue]             # Core values (mutable)
    goals: List[str]                         # Long-term goals
    relationships: Dict[str, RelationshipState]
    traits: PersonalityTraits
    last_reflection: Optional[str]
    version: str
```

**CoreValue**:
```python
name: str               # e.g., "Honesty", "Autonomy"
score: float            # 0.0-1.0
justification: str      # Why they hold this value
```

**RelationshipState**:
```python
user_id: str
trust_level: float       # 0-100
respect_level: float     # 0-100
shared_history_summary: str
latest_impression: Optional[str]
```

### 4.2 Motivational State

```python
MotivationalState:
    needs: CoreNeeds                    # 5 core psychological needs
    emotional_state: EmotionalState     # Stress, arousal, shame, fear, longing
    cognitive_state: CognitiveState     # Cognitive load, dissociation
    attachment: AttachmentSystem        # Attachment style & activation
    coping: CopingStyles                # Defense mechanisms
    conflicts: List[InternalConflict]   # Active psychological conflicts
    fatigue: float                      # Mental exhaustion
    active_strategy: Dict[str, float]   # Current behavioral strategy blend
    mood_momentum: float                # Resistance to mood change
    time_since_last_shift: int          # Turns since major mood shift
```

**CoreNeeds** (Self-Determination Theory):
```python
belonging: float    # Need for connection
autonomy: float     # Need for self-direction
security: float     # Need for stability/safety
competence: float   # Need to feel effective
novelty: float      # Need for stimulation
```

### 4.3 Memory Fragment

```python
MemoryFragment:
    id: str
    time_period: str            # e.g., "Childhood", "The War"
    description: str            # Event content
    emotional_tags: List[str]   # e.g., ["fear", "abandonment"]
    cognitive_tags: List[str]   # e.g., ["trust", "betrayal"]
    importance_score: float     # 0-1 (1.0 = core trauma)
    source_entity: str          # Who provided this information
    certainty_score: float      # Confidence in truth (0-1)
```

---

## 5. Memory Systems

### 5.1 Episodic Memory (ChromaDB)

**Location**: `data/chroma_db/`

**Purpose**: Stores "backstory" and raw interaction logs.

**Retrieval Method**: Semantic similarity via embeddings.

**Use Cases**:
- Vague emotional resonance
- Specific past events ("The drone crash")
- Mood-congruent retrieval (biased by current emotions)

### 5.2 Semantic Memory (Neo4j)

**Purpose**: Stores structured relationships and facts.

**Schema**:
```cypher
(Character {name: str})-[:TRUSTS {level: float}]->(User {name: str})
(Character)-[:EXPERIENCED]->(Event {summary: str, sentiment: str})
(User)-[:PARTICIPATED_IN]->(Event)
(Character)-[OPINION_EDGE]->(Entity)
```

**Use Cases**:
- Concrete opinions
- Social connections
- Causality chains
- Visualized in dashboard

---

## 6. Motivational Engine

### Design Philosophy

Based on psychological theories:
- **Self-Determination Theory**: Core needs
- **Attachment Theory**: Insecure attachment styles
- **Affect Theory**: Emotional dynamics
- **Cognitive Load Theory**: Working memory constraints

### Need Dynamics

**Decay Rates** (per turn):
- Security: -0.01
- Novelty: -0.02
- Fatigue: +0.05

**Intent-Based Updates**:
```
SUPPORT    → +Belonging, -Stress
CRITICISM  → -Competence, +Shame
THREAT     → +Fear, -Security
CONTROL    → -Autonomy, +Stress
```

### Strategy Blending

Calculates weighted mix of behavioral strategies based on:
- Stress pressure
- Cognitive load
- Attachment activation
- Internal conflict pressure

---

## 7. Dashboard & Observability

### Architecture

**Server**: Threading HTTP Server on port 8000

**Update Mechanism**: Server-Sent Events (SSE)

**Data Source**: `dashboard/live_state.json` (polled every 500ms)

### Panels

1. **Psyche Panel**: Live bars for mood, values, needs
2. **Relationship Meters**: Circular gauges for trust/respect
3. **Memory Feed**: Shows triggered memories
4. **Inner Thought**: Raw subconscious monologue
5. **Knowledge Graph**: Interactive force-directed visualization
6. **Strategy Radar**: Radar chart of active strategies

---

## 8. File Structure

```
framework/
├── main.py                     # Game engine & CLI
├── run_dashboard.py            # Dashboard HTTP server
├── character.json              # Character profile (mutable)
├── requirements.txt            # Python dependencies
│
├── data/
│   ├── chat_history.json       # Persistent chat log
│   └── chroma_db/              # ChromaDB vector store
│
├── dashboard/
│   ├── index.html              # Dashboard UI
│   ├── script.js               # Frontend logic
│   ├── style.css               # Styling
│   └── live_state.json         # State snapshot
│
├── src/
│   ├── graph.py                # LangGraph construction
│   ├── state.py                # AgentState definition
│   ├── schema.py               # All Pydantic models
│   ├── memory.py               # ChromaDB interface
│   ├── knowledge_graph.py      # Neo4j interface
│   ├── motivational.py         # Motivational system
│   ├── llm_client.py           # LLM configuration
│   ├── utils.py                # Helper functions
│   │
│   └── nodes/
│       ├── retrieve.py         # Memory/graph retrieval
│       ├── subconscious.py     # Internal monologue
│       ├── delta.py            # Profile updates
│       ├── planning.py         # Multi-turn objectives
│       ├── learn.py            # Memory formation
│       ├── generate.py         # Response generation
│       └── persist.py          # State persistence
│
└── scripts/
    ├── seed_graph.py           # Neo4j initialization
    └── ... (various utilities)
```

---

## 9. Integration & Configuration

### Environment Variables

Required in `.env`:
```bash
# LLM Configuration
GOOGLE_API_KEY=your_gemini_api_key

# Neo4j Configuration (optional)
NEO4J_ENABLED=true
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Dashboard Configuration
DASHBOARD_PORT=8000
```

### Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Neo4j (optional)
./scripts/install_neo4j.sh

# Start Neo4j (optional)
./scripts/start_neo4j.sh

# Seed knowledge graph (optional)
python scripts/seed_graph.py
```

### Running the System

```bash
# Start dashboard server
python run_dashboard.py &

# Start main CLI
python main.py

# Open dashboard in browser at http://localhost:8000
```

---

## 10. Development History

### Phase Evolution

**Phase 1-6**: Initial Implementation
- Basic LangGraph pipeline
- Memory retrieval
- Profile updates
- Knowledge graph integration

**Phase 7**: Motivational System
- Core needs tracking
- Emotional dynamics
- Attachment styles
- Coping mechanisms

**Phase 8**: Persistence & Graph RAG
- Chat history persistence
- Semantic entity extraction
- Opinion path retrieval
- Event logging

**Phase 9**: Delta History
- Profile change tracking
- Delta accumulation
- Historical analysis

**Phase 10**: Mood-Congruent Retrieval
- Emotional bias in memory search
- Proactive goal-based retrieval
- Importance weighting

**Phase 11**: Strategy Blending
- Multi-strategy behavioral outputs
- Trait modulation
- Mood momentum

**Phase 12**: Cognitive Framing
- Structured internal reasoning
- Belief tracking
- Behavioral constraints
- Confidence levels

**Phase 13**: Refactoring & Optimization
- Modular node architecture
- Code organization (`src/` directory)
- Performance improvements
- Non-linear scaling for cognitive load

### Current Version: 3.0

**Status**: Production-ready with full feature set

---

## 11. Technical Capabilities

### What This System CAN Do

✅ Maintain continuous psychological state across conversations  
✅ React differently to similar inputs over time  
✅ Accumulate memories and relationships  
✅ Express blended emotional/behavioral styles  
✅ Model attachment insecurity and stress dynamics  
✅ Track trust numerically  
✅ Recall emotionally salient past events  
✅ Produce internally consistent character behavior  
✅ Visualize internal state in real-time  

### What This System CANNOT Do

❌ Form or pursue goals autonomously  
❌ Plan multi-step actions independently  
❌ Learn values autonomously  
❌ Resolve internal conflicts  
❌ Self-correct maladaptive behavior  
❌ Initiate interaction  
❌ Operate without user input  
❌ Model theory of mind  
❌ Detect contradictions systematically  

### System Classification

From a systems perspective, this is:
- **Not an autonomous agent**
- **Not a planner**
- **Not a classical cognitive architecture**

It **is**:
- A stateful affective simulation
- With episodic memory
- And persistent interpersonal modeling
- Driven by external interaction

In cognitive science terms:
This is closer to a reactive **affective system with memory** than a deliberative mind.

---

## Conclusion

This framework represents a sophisticated approach to creating AI characters with genuine psychological depth. By combining multiple memory systems, a dynamic motivational engine, and a multi-stage cognitive pipeline, it produces behaviors that feel authentic and evolving.

The system prioritizes **emotional continuity** over rational coherence, and **intelligence emerges from persistence, not reasoning**.

For questions or support, refer to the main [README.md](README.md).

---

**Document Version**: 3.0  
**Framework Version**: Production  
**Last Updated**: December 24, 2025
