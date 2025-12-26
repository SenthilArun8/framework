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

1. [System Architecture Overview](#system-architecture-overview)
2. [Core Components](#core-components)
3. [Data Flow & Processing Pipeline](#data-flow--processing-pipeline)
4. [Schema & Data Models](#schema--data-models)
5. [Node Implementations](#node-implementations)
6. [Memory Systems](#memory-systems)
7. [Motivational Engine](#motivational-engine)
8. [Dashboard & Observability](#dashboard--observability)
9. [File Structure](#file-structure)
10. [Integration & Configuration](#integration--configuration)
11. [Development History](#development-history)

---

## System Architecture Overview

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

- **Deterministic linear DAG** (no branching, no loops, no recursion)
- **One pass per user message** (synchronous turn-based)
- **No mid-generation feedback** (all cognitive updates before response)
- **Persistent state across sessions** (profile, memories, graph)

---

## Core Components

### 1. Game Engine (main.py)

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

**Console HUD Features**:
- Memory triggers (blue)
- Graph connections (cyan)
- Mood changes (magenta)
- Value shifts (green/red with arrows)
- Trust/respect changes (charts)

### 2. LangGraph Pipeline (src/graph.py)

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

**Future Enhancement Note**: The graph includes conditional logic for potential looping based on cognitive load (`cognitive_load > 0.7` triggers loop to subconscious), but this is currently disabled to prevent infinite loops.

### 3. Agent State (src/state.py)

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

**Key Constraint**: No runtime schema enforcement—state integrity relies on node discipline.

---

## Data Flow & Processing Pipeline

### Core Model

`MotivationalState` is a numerical affective simulation, not symbolic reasoning.

### Subsystems

- **Core Needs** (belonging, autonomy, security, competence, novelty)
- **Emotional State** (stress, arousal, shame, fear, longing)
- **Cognitive State** (load, dissociation, fragility)
- **Attachment System** (style + activation)
- **Coping Styles** (static weights)
- **Internal Conflicts** (pressure vectors)
- **Fatigue accumulator**
- **Active strategy** (softmax-like blend)

### Update Mechanics

#### 4.1 Time-Based Decay

- Needs decay linearly per turn
- Fatigue increases monotonically
- Mood momentum increments but is not behaviorally enforced

#### 4.2 Input-Based Reactivity

- User message length → cognitive load (√ scaling)
- LLM-based intent classification:
    - SUPPORT
    - CRITICISM
    - THREAT
    - INQUIRY
    - NEUTRAL
- Intent modifies:
    - Needs
    - Stress
    - Shame
    - Attachment activation
- Fallback heuristics exist but are primitive.

#### 4.3 Trait Modulation

- Emotional volatility scales magnitude of updates
- Focus fragility scales cognitive load growth

#### 4.4 Strategy Synthesis

- **Pressures computed**:
    - Stress × cognitive load
    - Attachment insecurity
    - Conflict pressure (weighted)
    - Need deprivation
- **Strategy weights assigned**
- **Normalized**
- **Jittered with random noise**
- **Pruned below threshold**

Result: `active_strategy: Dict[str, float]`

### What This System CAN Do

- Produce non-deterministic affective shifts
- Maintain continuity across turns
- Express blended behavioral tendencies
- React differently to similar inputs depending on history

### What It CANNOT Do

- Reason about emotions
- Learn coping styles
- Resolve conflicts
- Inhibit reactions
- Reflect on past affective states

## 5. Subconscious Node (Interpretation Layer)

### Function (Inferred)

- Generates an internal monologue
- Possibly detects emotions, entities, triggers

### Limitations

- Output is string-only
- No structured influence downstream except via text
- No causal linkage to memory retrieval parameters
- No effect on motivational state

This node currently acts as narrative glue, not cognition.

## 6. Delta Node (Personality Change Detector)

### Purpose

- Compare `old_profile` vs updated profile
- Produce a `PersonalityDelta`

### Delta Capabilities

- Mood shifts (label only)
- Value changes (manual)
- Relationship trust/respect change
- Impression update
- Thought process explanation (string)

### Constraints

- No automatic value inference
- No statistical learning
- No multi-turn accumulation
- No causality verification

Delta is descriptive, not causal.

## 7. Memory System (Vector Store / Episodic Memory)

### Storage

- ChromaDB (persistent)
- Google Embeddings (text-embedding-004)

### Memory Unit

`MemoryFragment`:
- Description
- Emotional tags
- Time period
- Importance score
- Certainty
- Source

### Retrieval

- Similarity search
- Optional filtering:
    - Importance threshold
    - Time period
    - Emotional tags (post-filtered)

### Capabilities

- Contextual recall
- Emotional clustering
- Persistent memory across runs

### Limitations

- No consolidation
- No forgetting
- No reinforcement
- No contradiction resolution
- No causal links between memories

## 8. Knowledge Graph (Neo4j)

### Data Model

- **Nodes**:
    - Character
    - User
    - Event
- **Edges**:
    - TRUSTS (with numeric level)
    - EXPERIENCED
    - PARTICIPATED_IN

### Capabilities

- Persistent relationship tracking
- Trust as mutable state
- Event logging
- Simple graph traversal

### Limitations

- No ontology
- No schema enforcement
- No temporal reasoning
- No read integration into cognition
- Mostly write-only

The KG is currently a ledger, not a reasoning substrate.

## 9. Learning Node

### Function

- Converts deltas into:
    - Memory fragments (vector DB)
    - Event nodes (KG)
    - Trust updates

### Limitations

- No success/failure evaluation
- No reinforcement learning
- No prioritization
- No decay or pruning

## 10. Generation Node

### Role

- Produces final user-visible response

### Ingests

- Active strategy
- Memories
- Profile
- Subconscious thought

### Constraints

- Single-shot generation
- No self-critique
- No safety mediation
- No revision loop

## 11. Persistence Layer

### Persisted State

- Psychological profile (file)
- Episodic memories (Chroma)
- Relationships + events (Neo4j)

### Guarantees

- Persistence is best-effort
- No transactions across systems
- No rollback
- No integrity checks

## 12. What the System CAN Do (Explicitly)

- Maintain a continuous psychological state across conversations
- React differently to similar inputs over time
- Accumulate memories and relationships
- Express blended emotional/behavioral styles
- Model attachment insecurity and stress dynamics
- Track trust numerically
- Recall emotionally salient past events
- Produce internally consistent character behavior

## 13. What the System CANNOT Do (Important)

- ❌ Form or pursue goals
- ❌ Plan actions
- ❌ Learn values autonomously
- ❌ Resolve internal conflicts
- ❌ Reflect in a causal sense
- ❌ Model theory of mind
- ❌ Evaluate correctness of beliefs
- ❌ Detect contradictions
- ❌ Self-correct maladaptive behavior
- ❌ Initiate interaction
- ❌ Operate without user input

## 14. Implicit Assumptions (Unenforced)

- User intent classification is correct
- Emotional reactions are proportional
- Memory importance is accurate
- Trust is linear and additive
- Time passes per turn
- Psychological continuity is desirable
- LLM outputs are stable

None of these are validated or enforced.

## 15. Conceptual Classification

### From a systems perspective, this is:

- Not an autonomous agent
- Not a planner
- Not a cognitive architecture in the classical sense

### It is:

- A stateful affective simulation
- With episodic memory
- And persistent interpersonal modeling
- Driven by external interaction

### In cognitive science terms:

This is closer to a reactive **affective system with memory** than a deliberative mind.

## 16. Bottom-Line Summary

If someone reads this codebase correctly, they should understand:

- The system simulates *how a character feels and reacts over time*
- Not *what it should do*
- It prioritizes **emotional continuity** over rational coherence
- Learning is accumulative, not corrective
- **Intelligence emerges from persistence, not reasoning**
