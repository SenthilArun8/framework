# Architecture Deep Dive

A detailed explanation of what's happening in each Python file of the Living Character AI System.

---

## 📁 Core System Files

### **`main.py` - Game Engine & CLI Interface**

**Purpose**: Orchestrates all components and provides the command-line interface.

**Key Classes & Functions**:

#### `Colors` Class
```python
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
```
- **What it does**: ANSI color codes for terminal output formatting
- **Why**: Makes the console HUD visually informative with color-coded state changes

#### `GameEngine` Class

**`__init__(self)`**:
1. Loads character profile from `character.json`
2. Initializes `MotivationalState` from defaults (ephemeral, can be persisted)
3. Initializes `MemoryStore` (ChromaDB vector database)
4. Seeds initial backstory memories
5. Connects to Neo4j knowledge graph (optional, falls back gracefully)
6. Ensures base relationships exist in the graph
7. Builds the LangGraph processing pipeline with KG injection (now 5-stage with motivational)
8. **Loads chat history from `chat_history.json`** (Phase 8: Persistence)
9. Ensures default User_123 relationship exists
10. Dumps initial dashboard state

**`process_turn(self, user_input)`**:
1. Appends user message to chat history
2. **Immediately saves chat history to `chat_history.json`** (Phase 8: Persistence)
3. Creates a snapshot of the old profile (for comparison)
4. Prepares input dictionary with messages, profile, memories, subconscious thought, **and motivational state**
5. Invokes the LangGraph pipeline (5-stage reasoning with motivational node)
   - **Graph RAG now handled inside `retrieve_node`** via semantic entity extraction (Phase 8)
6. Updates character profile from output
7. Updates motivational state from output
8. Extracts bot response
9. Updates knowledge graph with new interaction data
10. Saves updated profile to `character.json`
11. Exports state to `live_state.json` for dashboard
12. Returns bot message and analysis data

**`_update_graph(self, old_profile, output)`**:
- Calculates trust/respect deltas by comparing old vs new profile
- Updates trust relationship edges in the graph
- **Logs interaction events to Neo4j** (Phase 8 Clarity):
  - **Event summary source**: `subconscious_thought` from output (refined by `delta_node`)
  - **Event sentiment**: Current mood from profile
  - This captures the internal reasoning/reflection about the interaction

**`dump_dashboard(self, analysis)`**:
- Serializes current character state to JSON
- Includes: profile, chat history, analysis data, graph visualization data
- Writes to `dashboard/live_state.json` for real-time dashboard polling

#### `main()` Function
1. Instantiates `GameEngine`
2. Prints welcome banner
3. Enters infinite loop:
   - Takes user input
   - Calls `engine.process_turn()`
   - Displays **HUD Console Visualization**:
     - Memory triggers (blue)
     - Graph connections (cyan)
     - Mood changes (magenta header)
     - Value shifts (green/red with arrows)
     - Trust/respect changes (green/red with charts)
   - Prints bot response (bold)
   - Shows internal thought (cyan)
4. On "quit", closes Neo4j connection and exits

---

### **`brain.py` - Core AI Reasoning Nodes**

**Purpose**: Contains the four core LangGraph nodes that process each user interaction (retrieve, subconscious, delta, generate). Works in conjunction with `motivational.py` for the 5-stage pipeline.

**Global Configuration**:
```python
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.2  # Low temperature for consistency
)
```

#### **Node 1: `retrieve_node(state, memory_store, kg=None)`**

**What it does**: Emotional memory retrieval + Semantic Graph RAG (Phase 8)

**Process**:
1. Extracts latest user message from state
2. **Query Expansion** (The "Bridge"):
   - Prompts Gemini to analyze emotional themes in user input
   - LLM identifies emotions (e.g., "abandonment", "criticism", "warmth")
   - **Extracts entities of interest** (e.g., "Empire", "General Kael") (Phase 8)
   - Creates a hypothetical memory search query
   - Uses structured output (`EmotionalQuery` schema)
3. **Vector Search**:
   - Queries ChromaDB with the emotional search query
   - Retrieves top 3 most relevant memories
   - Filters by minimum importance score
4. **Semantic Graph RAG** (Phase 8):
   - For each extracted entity:
     - Queries `kg.get_opinion_on_topic("Elias", entity)`
     - Synthesizes opinion paths into "Graph Memory" fragments
     - Adds to memories list with `time_period="Present Knowledge"`
   - Example: "Relationship to Empire: -[HATES]-> Empire -[DESTROYED]-> Home"
5. Returns combined list of vector memories + graph memories in state

**Fallback**: On error, falls back to direct keyword search

---

#### **Node 2: `subconscious_node(state)`**

**What it does**: Internal reflection before speaking

**Process**:
1. Hydrates objects from state:
   - `PsychologicalProfile` from dict
   - `MemoryFragment` list from dicts
2. Formats context strings:
   - Memory descriptions with time periods and emotional tags
   - Core values with scores
3. Prompts Gemini with:
   - Current psyche (mood, values, goals)
   - Triggered memories
   - User input
4. LLM produces raw internal thought (not JSON, just text)
   - "Does this challenge my beliefs?"
   - "What memories does this trigger?"
   - Raw emotional reaction
5. Returns subconscious thought string in state

**Key**: This is the character's private reflection, not the public response

---

#### **Node 3: `delta_node(state)`**

**What it does**: Decides if/how the character's psychology should change

**Process**:
1. Hydrates profile and memories from state
2. Formats context (current mood, values, relationships, memory triggers)
3. **Structured Output Prompt**:
   - System message defines neuroplasticity rules:
     - Values change slowly (±0.05 increments)
     - Ego is fragile (attacks can lower trust)
     - Output must match `PersonalityDelta` schema
4. **LLM Analysis**:
   - Determines if mood should shift (e.g., "Defensive → Contemplative")
   - Calculates value score changes with justifications
   - Decides relationship impacts (trust/respect deltas)
   - Generates internal thought process explaining changes
5. **Applies Changes**:
   - Updates mood if shifted
   - Iterates through `values_impacted`, finds matching value keys
   - Updates scores and justifications
   - Applies trust/respect changes (clamped 0-100)
   - Updates latest impression of user
6. Returns updated profile dict and thought process

**Error Handling**: On failure, returns empty dict (no changes applied)

---

#### **Node 4: `generate_node(state)`**

**What it does**: Produces the final character response

**Process**:
1. Hydrates profile and memories
2. Formats memory context (descriptions only, no metadata)
3. Prompts Gemini with:
   - Character profile (mood, role)
   - **Internal thought** (private, not to be spoken)
   - Relevant memories
   - User input
4. LLM generates in-character response
   - Colored by mood and memories
   - Informed by subconscious thought
   - Concise and character-appropriate
5. Returns response as message in state
**Key**: The internal thought influences the tone without being directly quoted

---

### **`schema.py` - Data Models (Pydantic)**

**Purpose**: Defines all data structures using Pydantic for validation and serialization.

#### **Immutable Context**

**`MemoryFragment`**:
```python
class MemoryFragment(BaseModel):
    id: str
    time_period: str            # "Childhood", "The War", "2023"
    description: str            # The actual event
    emotional_tags: List[str]   # ["fear", "abandonment"]
    importance_score: float     # 0.0 to 1.0 (1.0 = core trauma)
```
- **What it is**: A chunk of backstory stored in vector DB
- **Why immutable**: The past doesn't change, only how it's accessed

---

#### **Mutable State**

**`CoreValue`**:
```python
class CoreValue(BaseModel):
    name: str                   # "Honesty", "Pacifism"
    score: float                # 0.0 to 1.0
    justification: str          # Why they hold this value
```
- **What it is**: A belief system component
- **Mutability**: Score changes slowly based on interactions

**`RelationshipState`**:
```python
class RelationshipState(BaseModel):
    user_id: str
    trust_level: float          # 0 to 100
    respect_level: float        # 0 to 100
    shared_history_summary: str
    latest_impression: Optional[str]
```
- **What it is**: Dynamic relationship metrics
- **Updates**: Every interaction can shift trust/respect

**`PsychologicalProfile`**:
```python
class PsychologicalProfile(BaseModel):
    current_mood: str
    emotional_volatility: float  # How easily mood changes
    values: Dict[str, CoreValue]
    goals: List[str]
    relationships: Dict[str, RelationshipState]
    last_reflection: Optional[str]
```
- **What it is**: The character's "soul" - complete psychological state
- **Persistence**: Serialized to `character.json` after each turn

---

#### **Delta Schemas (LLM Structured Output)**

**`ValueChange`**:
```python
class ValueChange(BaseModel):
    value_name: str
    new_score: float
    reason: str  # "User proved blind obedience leads to failure"
```
- **What it is**: Instruction to update a specific value
- **Used by**: `delta_node` to apply changes

**`RelationshipUpdate`**:
```python
class RelationshipUpdate(BaseModel):
    trust_change: float      # +5.0 or -10.0
    respect_change: float
    new_impression: str
```
- **What it is**: Instruction to update relationship metrics

**`PersonalityDelta`**:
```python
class PersonalityDelta(BaseModel):
    mood_shift: Optional[str]
    values_impacted: List[ValueChange]
    relationship_impact: Optional[RelationshipUpdate]
    thought_process: str  # Internal monologue explaining changes
```
- **What it is**: Complete change package from `delta_node`
- **Forces LLM**: To output structured, parseable decisions

---

#### **Retrieval Schema**

**`EmotionalQuery`**:
```python
class EmotionalQuery(BaseModel):
    detected_emotions: List[str]     # ["condescension", "authority"]
    entities_of_interest: List[str]  # ["Empire", "General Kael"] (Phase 8)
    memory_search_query: str         # "being belittled by superior"
    trigger_strength: float          # 0.0 to 1.0
```
- **What it is**: Emotional analysis of user input with entity extraction (Phase 8)
- **Used by**: `retrieve_node` to find semantically relevant memories and query knowledge graph

---

#### **Motivational System Schemas (Phase 7)**

**`CoreNeeds`**:
```python
class CoreNeeds(BaseModel):
    belonging: float       # need for connection (0-1)
    autonomy: float        # need for self-direction (0-1)
    security: float        # need for stability, safety (0-1)
    competence: float      # need to feel effective (0-1)
    novelty: float         # need for stimulation/interest (0-1)
```
- **What it is**: Fundamental psychological needs (Self-Determination Theory)
- **Dynamics**: Depletes over time, replenished by satisfying interactions

**`EmotionalState`**:
```python
class EmotionalState(BaseModel):
    stress: float           # 0 to 1
    arousal: float          # 0 to 1 (energy vs shutdown)
    shame: float            # 0 to 1
    fear: float             # 0 to 1
    longing: float          # 0 to 1 (relationship-specific)
```
- **What it is**: Current emotional activation levels
- **Used for**: Calculating emotional pressure factors

**`CognitiveState`**:
```python
class CognitiveState(BaseModel):
    cognitive_load: float       # 0 to 1 (mental effort)
    dissociation: float         # 0 to 1 (disconnection)
    focus_fragility: float      # trait: 0.2 = stable, 0.8 = easily distracted
```
- **What it is**: Mental processing capacity and stability
- **Influences**: Thought coherence and response style

**`AttachmentSystem`**:
```python
class AttachmentSystem(BaseModel):
    style: Literal["secure", "anxious", "avoidant", "disorganized"]
    activation: float           # 0 to 1 (degree of insecurity triggered)
    protest_tendency: float     # anxious behaviors (clingy, over-explaining)
    withdrawal_tendency: float  # avoidant behaviors (shutdown, distance)
```
- **What it is**: Attachment theory modeling (Bowlby/Ainsworth)
- **Why**: Explains relationship anxiety and behavioral patterns

**`CopingStyles`**:
```python
class CopingStyles(BaseModel):
    avoidance: float
    intellectualization: float
    over_explaining: float
    humor_deflection: float
    aggression: float
    appeasement: float
```
- **What it is**: Defense mechanism tendencies (0-1 scores)
- **Used for**: Determining response style under stress

**`InternalConflict`**:
```python
class InternalConflict(BaseModel):
    name: str                    # "Trust vs Survival"
    pressure: float              # 0 to 1 (how active)
    polarity: Tuple[str, str]    # ("Openness", "Safety")
```
- **What it is**: Active psychological tension between opposing drives
- **Examples**: "Trust vs Survival", "Independence vs Belonging"

**`MotivationalState`**:
```python
class MotivationalState(BaseModel):
    needs: CoreNeeds
    emotions: EmotionalState
    cognition: CognitiveState
    attachment: AttachmentSystem
    coping: CopingStyles
    conflicts: List[InternalConflict]
    fatigue: float                 # accumulated interaction cost
    active_strategy: Optional[str]  # emergent behavior (e.g., "defensive_curt")
```
- **What it is**: Complete deep psychological state
- **Updated by**: `motivational_update_node` every turn
- **Influences**: Behavioral strategy selection, response tone, engagement level

**Why this system**:
- **Depth**: Goes beyond surface personality to model underlying drives
- **Emergent Behavior**: Strategy isn't scripted, it emerges from pressure calculations
- **Realistic Variation**: Same conversation topic produces different responses based on needs state
- **Therapeutic Accuracy**: Based on real psychological frameworks (SDT, Attachment Theory)

---

#### **Helper Functions**

**`load_character_profile(filepath)`**:
- Reads JSON file
- Deserializes to `PsychologicalProfile` object
- Validates structure with Pydantic

**`save_character_profile(profile, filepath)`**:
- Serializes `PsychologicalProfile` to JSON
- Pretty-prints with indent=2
- Writes to file

---

### **`memory.py` - Vector Database Management**

**Purpose**: Manages semantic memory storage and retrieval using ChromaDB.

#### `MemoryStore` Class

**`__init__(self)`**:
1. Initializes Google embeddings model:
   ```python
   self.embeddings = GoogleGenerativeAIEmbeddings(
       model="models/text-embedding-004",
       google_api_key=os.getenv("GOOGLE_API_KEY")
   )
   ```
2. Creates persistent ChromaDB instance:
   ```python
   self.vector_store = Chroma(
       collection_name="character_backstory",
       embedding_function=self.embeddings,
       persist_directory="./chroma_db"  # Survives restarts
   )
   ```

**`add_memories(self, fragments: List[MemoryFragment])`**:
1. Iterates through memory fragments
2. Creates `Document` objects:
   - `page_content`: The description (what gets embedded)
   - `metadata`: All other fields (id, time_period, tags, importance)
3. Adds documents to ChromaDB
4. ChromaDB automatically:
   - Calls Google embedding API
   - Stores vectors
   - Persists to disk

**`retrieve_relevant(self, query: str, k: int = 3, min_importance: float = 0.0)`**:
1. Builds optional filter for importance threshold
2. Performs similarity search in ChromaDB:
   - Embeds the query using Google embeddings
   - Finds k nearest neighbors in vector space
3. Reconstructs `MemoryFragment` objects from results:
   - Splits comma-separated emotional tags back to list
   - Extracts all metadata fields
4. Returns list of relevant memories

**Why this works**: Semantic similarity means "being criticized by authority" matches "forced military enlistment" even without shared keywords.

---

#### `seed_memories(store)` Function

**What it does**: Populates vector DB if empty

**Process**:
1. Checks if memories already exist (queries for "war")
2. If empty, creates initial backstory fragments:
   ```python
   MemoryFragment(
       id="401",
       time_period="The War",
       description="Witnessed preventable death due to lack of supplies",
       emotional_tags=["Guilt", "Anger"],
       importance_score=0.9  # Core trauma
   )
   ```
3. Adds fragments to store

**Why seed**: Provides initial context for the character without requiring manual DB setup.

---

### **`knowledge_graph.py` - Neo4j Graph Operations**

**Purpose**: Manages concept relationships and opinion mapping in Neo4j.

#### `KnowledgeGraph` Class

**`__init__(self, uri, user, password)`**:
- Creates Neo4j driver connection
- Connection string example: `bolt://localhost:7687`

**`close(self)`**:
- Closes driver connection (cleanup)

**`check_connection(self)`**:
- Tests connection with simple query: `RETURN 1`
- Returns `True` if successful, `False` on error
- Used by `GameEngine` to decide if graph features are available

---

#### **Initialization**

**`ensure_relationship_exists(self, char_name, user_name)`**:
```cypher
MERGE (c:Character {name: $char_name})
MERGE (u:User {name: $user_name})
MERGE (c)-[r:TRUSTS]->(u)
ON CREATE SET r.level = 50.0
```
- **What it does**: Creates base nodes and relationship if they don't exist
- **Why**: Prevents errors when updating trust levels
- **Default trust**: 50.0 (neutral starting point)

---

#### **Learning Phase**

**`add_interaction_event(self, char_name, user_name, summary, sentiment)`**:
```cypher
CREATE (e:Event {summary: $summary, sentiment: $sentiment, timestamp: timestamp()})
CREATE (c)-[:EXPERIENCED]->(e)
CREATE (u)-[:PARTICIPATED_IN]->(e)
```
- **What it does**: Creates event nodes linked to both character and user
- **Graph structure**:
  ```
  (Character)-[:EXPERIENCED]->(Event)<-[:PARTICIPATED_IN]-(User)
  ```
- **Use case**: Build history of interactions for future analysis

---

#### **Growth Phase**

**`update_trust(self, char_name, user_name, delta)`**:
```cypher
MATCH (c:Character {name: $char_name})-[r:TRUSTS]->(u:User {name: $user_name})
SET r.level = r.level + $delta
RETURN r.level
```
- **What it does**: Updates trust level on the relationship edge
- **Dynamic**: Trust is a property that changes over time
- **Example**: `delta = +5.0` increases trust, `delta = -10.0` decreases it

---

#### **Indirect Querying (The Killer Feature)**

**`get_opinion_on_topic(self, char_name, topic)`**:
```cypher
MATCH path = (c:Character {name: $char_name})-[*1..2]-(target {name: $topic})
WHERE NOT 'User' IN labels(target)
RETURN path LIMIT 1
```
- **What it does**: Finds WHY the character cares about a topic
- **Path traversal**: Looks 1-2 relationships deep
- **Example query**: "Why does Elias hate the Empire?"
  - Finds: `Elias -[HATES]-> Empire -[DESTROYED]-> Home`
  - Explains: Elias hates the Empire because it destroyed his home
- **Returns**: Formatted relationship chain strings

---

#### **Visualization**

**`get_viz_data(self)`**:
```cypher
MATCH (n)-[r]->(m)
RETURN n, r, m LIMIT 100
```
- **What it does**: Exports graph data for dashboard visualization
- **Process**:
  1. Queries all nodes and relationships (limited to 100)
  2. Formats nodes: `{id, label, group}`
  3. Formats edges: `{from, to, label, arrows}`
  4. Returns JSON compatible with vis-network library
- **Used by**: Dashboard to render interactive knowledge graph

---

### **`state.py` - LangGraph State Definition**

**Purpose**: Defines the state structure passed between graph nodes.

```python
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    profile: dict
    memories: list
    subconscious_thought: str
```

**Field Breakdown**:

**`messages`**:
- **Type**: List of `BaseMessage` (LangChain message objects)
- **Annotation**: `add_messages` - special LangGraph reducer
- **What it does**: Automatically appends new messages (no overwrite)
- **Contains**: Full conversation history

**`profile`**:
- **Type**: `dict` (serialized `PsychologicalProfile`)
- **Why dict**: LangGraph state must be serializable
- **Updated by**: `delta_node`

**`memories`**:
- **Type**: `list` (serialized `MemoryFragment` objects)
- **Updated by**: `retrieve_node`
- **Lifespan**: Per-turn only (not persisted in state)

**`subconscious_thought`**:
- **Type**: `str`
- **Updated by**: `subconscious_node` and `delta_node`
- **Purpose**: Internal monologue passed to response generator

**`motivational`**:
- **Type**: `dict` (serialized `MotivationalState`)
- **Updated by**: `motivational_update_node`
- **Purpose**: Tracks needs, emotions, cognitive state, attachment, coping strategies
- **Influences**: Behavioral strategy selection that affects response generation

---

### **`graph.py` - LangGraph Workflow Builder**

**Purpose**: Constructs the LangGraph state machine.

#### `build_graph(memory_store)` Function

```python
def build_graph(memory_store, kg=None):  # Phase 8: KG injection
    workflow = StateGraph(AgentState)
    
    # Define Nodes
    workflow.add_node("retrieve", partial(retrieve_node, memory_store=memory_store, kg=kg))  # KG added
    workflow.add_node("motivational", motivational_update_node)
    workflow.add_node("subconscious", subconscious_node)
    workflow.add_node("delta", delta_node)
    workflow.add_node("generate", generate_node)
    
    # Define Edges (Linear Flow)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "motivational")
    workflow.add_edge("motivational", "subconscious")
    workflow.add_edge("subconscious", "delta")
    workflow.add_edge("delta", "generate")
    workflow.add_edge("generate", END)
    
    return workflow.compile()
```

**What happens**:
1. **StateGraph Creation**: Initialized with `AgentState` schema
2. **Node Registration**: Five nodes form the processing pipeline
3. **Dependency Injection**: `memory_store` and `kg` (Phase 8) injected via `functools.partial`
4. **5-Stage Pipeline**: `Retrieve → Motivational → Subconscious → Delta → Generate → END`
5. **Compilation**: LangGraph creates executable workflow

**Why this approach**:
- **Modularity**: Each node is testable in isolation
- **State Persistence**: State flows through all nodes automatically
- **Layered Psychology**: Motivational needs affect conscious thought
- **Easy Extension**: Could add conditional routing later
- **Observability**: Can inspect state between nodes for debugging

---

### **`motivational.py` - Emergent Behavioral System**

**Purpose**: Models deep psychological needs and selects emergent behavioral strategies.

#### `DEFAULT_MOTIVATIONAL` Constant

```python
DEFAULT_MOTIVATIONAL = MotivationalState(
    needs=CoreNeeds(belonging=0.5, autonomy=0.5, security=0.5, competence=0.5, novelty=0.5),
    emotions=EmotionalState(stress=0.2, arousal=0.5, shame=0.0, fear=0.0, longing=0.2),
    cognition=CognitiveState(cognitive_load=0.2, dissociation=0.0, focus_fragility=0.4),
    attachment=AttachmentSystem(style="avoidant", activation=0.3, ...),
    coping=CopingStyles(avoidance=0.7, intellectualization=0.6, ...),
    conflicts=[InternalConflict(name="Trust vs Survival", pressure=0.6, ...)],
    fatigue=0.1,
    active_strategy="neutral"
)
```
- **What it is**: Baseline psychological state for Elias
- **Why**: Provides initial values if no motivational state exists

---

#### `motivational_update_node(state)` Function

**What it does**: Updates deep psychological state and selects emergent behavioral strategy

**Process**:

**1. Hydrate or Initialize**:
- Loads `motivational` from state or uses default
- Deserializes dict to `MotivationalState` object

**2. Decay / Time-based Updates**:
```python
current_state.needs.security -= 0.01      # Needs drift toward deprivation
current_state.needs.novelty -= 0.02      # Conversation becomes routine
current_state.fatigue += 0.05            # Interaction cost
```
- **Why**: Simulates natural need depletion over time

**3. Reactive Updates (Heuristics)**:
- **Long inputs** → Increase cognitive load
- **Questions** → Challenge competence, increase stress
- **Positive words** ("thanks", "good", "trust") → Boost belonging, reduce shame/attachment activation
- All values clamped 0-1

**4. Calculate Pressures**:
```python
stress_pressure = emotions.stress * (1 + cognition.cognitive_load)
attn_pressure = attachment.activation (varies by style)
conflict_pressure = average of all conflict pressures
need_pressure = 1.0 - avg_need_score
```
- **Finds dominant factor**: Highest pressure determines strategy

**5. Select Emergent Strategy**:
If dominant pressure > 0.6 (activation threshold):

| Dominant Factor | Condition | Strategy |
|----------------|-----------|----------|
| Stress | High cognitive load | `"fragmented_thoughts"` |
| Stress | Normal load | `"defensive_curt"` |
| Attachment | Anxious style | `"over_explaining_clingy"` |
| Attachment | Avoidant style | `"shutdown_withdrawal"` |
| Dissociation | High | `"spaced_out_drifting"` |
| Conflict | High | `"mixed_signals_hesitant"` |
| Deprivation | Low autonomy | `"argumentative_assertive"` |
| Deprivation | Low belonging | `"vulnerable_seeking"` |
| Deprivation | Low security | `"hyper_vigilant"` |
| Deprivation | Other | `"needy_demanding"` |

**6. Return**:
```python
return {"motivational": current_state.model_dump()}
```
- Updates state with new motivational values and active strategy

**Why this matters**:
- **Emergent Behavior**: Character doesn't just respond to content, but to psychological state
- **Realistic Complexity**: "Why is Elias being defensive?" → Check his security needs and stress levels
- **Non-deterministic**: Same input can produce different responses based on accumulated fatigue/needs

---

### **`run_dashboard.py` - Web Server for Dashboard**

**Purpose**: HTTP server that serves the dashboard and provides chat API.

#### Components

**Imports**:
```python
import http.server
import socketserver
from main import GameEngine
```

**Global Configuration**:
```python
PORT = 8000
DIRECTORY = "dashboard"
engine = GameEngine()  # Single instance for all requests
```

**Why single instance**: Maintains conversation state across API calls

---

#### `Handler` Class (extends `SimpleHTTPRequestHandler`)

**`__init__(self, *args, **kwargs)`**:
- Sets directory to `"dashboard"`
- Serves static files (HTML, CSS, JS)

**`do_POST(self)`**:
- **Endpoint**: `/chat`
- **Process**:
  1. Reads POST body (JSON)
  2. Extracts `message` field
  3. Calls `engine.process_turn(user_msg)`
  4. Returns JSON response: `{"reply": "...", "status": "ok"}`
- **Error handling**: Returns 500 status on exception

**What this enables**: Browser can send messages via JavaScript `fetch()` API

---

#### Main Execution

```python
if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving Dashboard & API at http://localhost:{PORT}")
        httpd.serve_forever()
```

**Features**:
- **Reusable address**: Avoids "port already in use" errors on restart
- **Graceful shutdown**: Ctrl+C closes server cleanly
- **Dual purpose**: Serves static files AND handles API requests

---

## 🔄 Complete Flow Diagram

```
User Input
    ↓
GameEngine.process_turn()
    ├─ Append to chat_history
    └─ Save to chat_history.json  [Phase 8: Persistence]
    ↓
LangGraph Pipeline (5-Stage):
    ├─ retrieve_node
    │   ├─ Emotional analysis + Entity extraction (Gemini)  [Phase 8]
    │   ├─ Vector search (ChromaDB)
    │   └─ Semantic Graph RAG (Neo4j opinion paths)  [Phase 8]
    ├─ motivational_update_node
    │   ├─ Update needs/emotions/cognitive state
    │   ├─ Calculate pressures (stress, attachment, conflict, deprivation)
    │   └─ Select emergent behavioral strategy
    ├─ subconscious_node
    │   └─ Internal reflection (Gemini, influenced by motivational strategy)
    ├─ delta_node
    │   ├─ Calculate changes (Gemini)
    │   ├─ Update profile
    │   └─ Generate thought_process (used for event summary)  [Phase 8]
    └─ generate_node
        └─ Create response (Gemini, colored by active strategy)
    ↓
Update Knowledge Graph (Neo4j)
    ├─ Update trust edges
    └─ Log event with subconscious_thought as summary  [Phase 8]
    ↓
Update Motivational State
    ↓
Save state (character.json + live_state.json + chat_history.json)  [Phase 8]
    ↓
Display HUD / Return to dashboard
```

---

## 🎓 Key Architectural Patterns

### **1. Separation of Concerns**
- **Brain**: Pure reasoning logic
- **Memory**: Vector operations only
- **KnowledgeGraph**: Graph operations only
- **Schema**: Data definitions only
- **Main**: Orchestration only

### **2. Structured LLM Output**
- Pydantic schemas force LLM to return parseable data
- No regex parsing or string manipulation
- Type-safe with validation

### **3. Graceful Degradation**
- Neo4j optional (system works without it)
- Fallback memory retrieval on error
- Empty delta returns don't crash the system

### **4. State Immutability**
- Memories never change (immutable archive)
- Profile changes explicit (delta system)
- Old profile snapshot for comparison

### **5. Multi-Modal Output**
- Console HUD (human-readable)
- JSON export (machine-readable)
- Web dashboard (visual)

### **6. Phase 8 Enhancements**
- **Chat Persistence**: Conversation history saved to `chat_history.json` immediately on each turn
- **Semantic Graph RAG**: Entity extraction drives knowledge graph queries (no manual keyword matching)
- **Event Clarity**: Graph events use `subconscious_thought` (refined by delta_node) as summary source
- **Hybrid Retrieval**: Combines vector similarity (ChromaDB) + graph traversal (Neo4j) in single retrieve node

---

## 🧩 Extension Points

### **Add New Nodes**
In `graph.py`, add conditional routing:
```python
def should_reflect(state):
    return state['subconscious_thought'].contains("confused")

workflow.add_conditional_edges("delta", should_reflect, {
    True: "reflection_node",
    False: "generate"
})
```

### **Add New Memory Types**
In `schema.py`, create new fragment types:
```python
class SensoryMemory(MemoryFragment):
    sensory_details: str  # "smell of smoke", "sound of sirens"
```

### **Add New Graph Relationships**
In `knowledge_graph.py`, create domain-specific queries:
```python
def get_fears(self, char_name):
    """Find what the character fears."""
    query = "MATCH (c:Character {name: $char_name})-[:FEARS]->(x) RETURN x"
```

---

### **`motivational.py` - Emergent Behavior Engine (New)**

**Purpose**: Simulates internal needs, conflicts, and decision pressures to drive agency.

**Key Components**:

#### **State Models**
- **`MotivationalState`**:
  - `CoreNeeds`: Safety, Autonomy, Belonging, etc.
  - `EmotionalState`: Stress, Shame, Fear Vectors.
  - `CognitiveState`: Load, Dissociation.
  - `AttachmentSystem`: Interactions triggering insecurity.
  - `InternalConflict`: Active competing desires.

#### **`motivational_update_node`**
- **Inputs**: User message, retrieved memories, current profile.
- **Process**:
  1. **Decay/Regeneration**: Needs change over time.
  2. **Pressure Calculation**:
     - `stress_pressure`: Stress * Cognitive Load.
     - `conflict_pressure`: Active conflicting goals.
     - `need_pressure`: Unmet needs.
  3. **Strategy Selection**:
     - *High Stress + Load* -> "Fragmented Thoughts"
     - *High Shame + Anxious* -> "Over-explaining"
     - *High Dissociation* -> "Spaced Out"
- **Outputs**: `MotivationalState` updated with new vectors and selected strategy.

#### **Emergent Behavior Generation**
- The `generate_node` now receives the **Behavior Strategy** (e.g., "Defensive/Argumentative").
- Adjusts tone, grammar, and content based on this strategy, rather than just "replying".

---

## 📦 Phase 8: Persistence & RAG Refinement

### **8.1 Chat Persistence**

**File**: `chat_history.json`

**Implementation**:
- **`GameEngine.__init__`**: Loads existing chat history if file exists
- **`process_turn`**: Saves immediately after appending user message
- **Format**: JSON array of message objects with `role` and `content`

**Why immediate saving**: Ensures conversation history survives crashes/restarts

**Example**:
```json
[
  {"role": "human", "content": "Can you help me?"},
  {"role": "ai", "content": "I can try. What do you need?"}
]
```

---

### **8.2 Semantic Graph RAG**

**Schema Update**: `EmotionalQuery` now includes `entities_of_interest: List[str]`

**How it works**:
1. **LLM extracts entities** from user input (e.g., "Empire", "General Kael", "Home")
2. **For each entity**:
   - Calls `kg.get_opinion_on_topic("Elias", entity)`
   - Retrieves relationship paths from Neo4j
   - Example: `["-[HATES]->", "-[DESTROYED]->"]`
3. **Synthesizes "Graph Memory"**:
   - Creates synthetic `MemoryFragment` with path as description
   - Tags as `time_period="Present Knowledge"`
   - Importance score: 0.8
4. **Adds to memories list** alongside vector-retrieved memories

**Before (Phase 7)**: Keyword-based RAG in `main.py` checked for hardcoded entities
**After (Phase 8)**: Semantic extraction in `retrieve_node` - LLM decides what's relevant

**Benefit**: More flexible, doesn't require maintaining keyword lists

---

### **8.3 Event Logic Clarity**

**Issue**: Previously unclear what the "event summary" represented

**Solution**: Explicit documentation in `_update_graph`:
```python
# Event Summary Source: 'subconscious_thought' (Refined internal monologue from Delta Node)
thought = output.get('subconscious_thought', '')
if thought: 
    self.kg.add_interaction_event("Elias", user_id, thought, self.profile.current_mood)
```

**What this means**:
- The event summary is **NOT** the user input
- It's the **character's internal reflection** about the interaction
- This reflection comes from `delta_node.thought_process`
- Captures the psychological reasoning behind profile changes

**Example**:
- User says: "You're being naive about authority"
- Event summary: "User challenged my core belief. I felt defensive but recognized some truth in their words."

**Why this matters**: Graph events represent character's subjective experience, not objective interaction log

---

## 🔄 Phase 8 Integration Summary

| Feature | Before | After |
|---------|--------|-------|
| **Chat History** | In-memory only | Persisted to `chat_history.json` |
| **Graph RAG** | Keyword matching in main.py | Semantic entity extraction in retrieve_node |
| **Event Summary** | Unclear source | Explicitly `subconscious_thought` from delta_node |
| **Retrieval** | Vector only | Hybrid: Vector + Graph |

---

This architecture enables **emergent narrative complexity** through simple, composable components. Each file has a single responsibility, making the system maintainable and extensible.
