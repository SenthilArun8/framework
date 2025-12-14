# Living Character AI System

An advanced AI system that creates psychologically evolving characters with dynamic personalities, emotions, and relationships. Built with LangChain, Google Gemini, ChromaDB vector storage, Neo4j knowledge graphs, and a real-time web dashboard.

---

## 🎭 What Does This Do?

This system simulates a **living, breathing AI character** (named "Elias" - a medic/survivor) whose personality, mood, values, and relationships **evolve realistically** based on conversations. Unlike traditional chatbots that maintain static personalities, this character has:

- **Dynamic Psychology**: Values and beliefs that shift slowly based on interactions (simulating neuroplasticity)
- **Emotional Memory System**: Past experiences stored in a vector database, retrieved based on emotional resonance
- **Relationship Tracking**: Trust and respect levels that change based on user behavior
- **Knowledge Graph Integration**: Connections between concepts (e.g., "Elias -[HATES]-> Empire -[DESTROYED]-> Home")
- **Real-time Dashboard**: Web interface showing the character's internal state as it changes

---

## 🏗️ System Architecture

### **Core Components**

#### 1. **Brain Pipeline** (`brain.py`)
A 4-stage LangGraph processing pipeline powered by Google Gemini:

- **Retrieve Node**: Analyzes user input for emotional themes, retrieves relevant memories from vector DB
- **Subconscious Node**: Internal reflection considering memories, values, and current mood
- **Delta Node**: Calculates psychological changes (values, mood, trust) with realistic small increments
- **Generate Node**: Produces character response based on updated psychological state

#### 2. **Memory System** (`memory.py`)
- **ChromaDB Vector Store**: Stores character backstory as semantic embeddings
- **Google Embeddings**: `text-embedding-004` model for semantic similarity
- **Emotion-Based Retrieval**: Finds memories by emotional themes, not just keywords
- **Persistent Storage**: `./chroma_db` directory maintains memory across sessions

#### 3. **Knowledge Graph** (`knowledge_graph.py`)
- **Neo4j Graph Database**: Stores relationships between concepts and entities
- **Dynamic Opinion Mapping**: "Why does Elias hate the Empire?" → Traverses: `Elias -[HATES]-> Empire -[DESTROYED]-> Home`
- **Trust Evolution**: Updates relationship edges dynamically
- **Visualization Data**: Exports nodes/edges for dashboard rendering

#### 4. **Data Models** (`schema.py`)
- `PsychologicalProfile`: Character's mutable state (mood, values, goals, relationships)
- `MemoryFragment`: Immutable backstory chunks with emotional tags
- `PersonalityDelta`: Changes to apply after each interaction
- `EmotionalQuery`: Structured output for memory retrieval

#### 5. **State Management** (`state.py`, `graph.py`)
- **LangGraph StateGraph**: Chains the 4 brain nodes in sequence
- **AgentState**: Tracks conversation, profile, memories, and internal thoughts
- **Functional Pipeline**: `Retrieve → Subconscious → Delta → Generate`

#### 6. **Web Dashboard** (`dashboard/`, `run_dashboard.py`)
- **Real-time HUD**: Live visualization of character's internal state
- **Interactive Chat**: Send messages directly from the browser
- **Bento Grid Layout**: Psyche profile, chat stream, trust/respect meters, knowledge graph visualization, subconscious thoughts
- **Live Updates**: Polls `live_state.json` every 500ms for state changes

---

## 📂 Project Structure

```
framework/
├── main.py                   # CLI interface & game engine orchestration
├── run_dashboard.py          # Web server for dashboard (http://localhost:8000)
├── brain.py                  # 4-stage AI reasoning pipeline
├── memory.py                 # Vector DB memory management
├── knowledge_graph.py        # Neo4j graph operations
├── schema.py                 # Pydantic data models
├── state.py                  # LangGraph state definition
├── graph.py                  # LangGraph workflow builder
├── character.json            # Character's persistent psychological state
├── requirements.txt          # Python dependencies
├── .env                      # API keys and config
├── chroma_db/                # ChromaDB persistent storage
├── dashboard/
│   ├── index.html            # Dashboard UI
│   ├── style.css             # Styling
│   ├── script.js             # Real-time updates & chat
│   └── live_state.json       # Current character state (auto-generated)
└── README.md                 # This file
```

---

## 🚀 Setup

### **Prerequisites**
- Python 3.8+
- Google API Key ([Get one here](https://makersuite.google.com/app/apikey))
- Neo4j Database (Optional but recommended for knowledge graph features)

### **Installation**

1. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   Create a `.env` file in the project root:
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_neo4j_password
   ```

3. **Start Neo4j** (Optional):
   ```powershell
   # If using local Neo4j installation
   neo4j console
   ```

---

## 🎮 Usage

### **Option 1: Command Line Interface**

```powershell
python main.py
```

**Features:**
- Interactive chat with Elias
- Real-time HUD showing state changes:
  - 📂 Memory triggers
  - 🧠 Mood shifts
  - ⚖️ Value changes
  - 📈📉 Trust/respect updates
  - 💭 Internal thoughts
  - 🕸️ Knowledge graph connections

**Example output:**
```
==================================================
Chatting with Calmer Elias.
System: Interaction Sandbox Active (HUD Enabled).
==================================================

You: Can you help me?

📂 [Memory Triggered]: "Witnessed a preventable death due to lack of supplies..."
🕸️ [Graph Connection]: Elias -[:HATES]-> Empire
📈 [State Change] Trust: 17.40 -> 22.40
Elias: I can try. What do you need?
💭 [Internal Thought]: "User seems genuine. Cautiously optimistic."
```

### **Option 2: Web Dashboard**

```powershell
python run_dashboard.py
```

Then open: **http://localhost:8000**

**Features:**
- **Live State Visualization**: See character psychology update in real-time
- **Interactive Chat**: Type messages directly in the browser
- **Bento Grid Layout**:
  - Psyche Profile (mood, goals, values bar chart)
  - Chat Stream (conversation history)
  - Relationship Meters (trust/respect circular gauges)
  - Knowledge Graph (interactive Neo4j visualization)
  - Subconscious Thoughts (internal monologue stream)

---

## 🧠 How It Works

### **1. Neuroplasticity Simulation**
Values change slowly (±0.05 per interaction) to simulate realistic belief evolution:
```python
# Before: Pacifism = 0.9
# User challenges with: "Sometimes violence is necessary"
# After: Pacifism = 0.87 (small decrease)
```

### **2. Emotion-Based Memory Retrieval**
Not keyword matching - the system analyzes emotional themes:
```python
User: "You're being naive about authority."
→ LLM detects: ["condescension", "authority challenge"]
→ Searches memory for: "being belittled by a superior"
→ Retrieves: Memory of forced military enlistment
```

### **3. Ego & Resistance Modeling**
Character can resist change even if user is logically correct:
```python
# If trust is low, challenging core values might DECREASE trust
# Ego defense: "They're attacking what I believe in"
```

### **4. Knowledge Graph Reasoning**
Traverses concept connections to understand why character cares:
```
User mentions "Empire"
→ Graph: Elias -[HATES]-> Empire -[DESTROYED]-> Home
→ Response colored by this relationship chain
```

### **5. Persistent State**
Character state auto-saves to `character.json` after each interaction:
```json
{
  "current_mood": "Calmer",
  "values": {
    "pacifism": {"score": 0.9, "justification": "Violence creates more patients"},
    "authority_obedience": {"score": 0.22, "justification": "Orders got people killed"}
  },
  "relationships": {
    "User_123": {"trust_level": 17.4, "respect_level": 43.9}
  }
}
```

---

## 🛠️ Customization

### **Change the Character**
Edit `character.json` to modify Elias's base personality, or create a new character profile.

### **Add More Memories**
In `memory.py`, modify `seed_memories()`:
```python
fragments = [
    MemoryFragment(
        id="404", 
        time_period="Recent", 
        description="Your custom memory here",
        emotional_tags=["Hope", "Fear"],
        importance_score=0.8
    )
]
```

### **Adjust AI Model**
In `brain.py`, change the Gemini model:
```python
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",  # or "gemini-1.5-pro"
    temperature=0.2  # Lower = more consistent, Higher = more creative
)
```

### **Modify Graph Relationships**
In `knowledge_graph.py`, add custom relationship types or queries.

---

## 🔬 Advanced Features

### **Graph RAG (Retrieval-Augmented Generation)**
The system combines:
- **Vector Similarity**: ChromaDB finds semantically similar memories
- **Graph Traversal**: Neo4j finds conceptual relationships
- **Hybrid Context**: Both feed into Gemini for richer responses

### **Multi-Modal State Tracking**
- Console HUD (ANSI colors)
- JSON export (`live_state.json`)
- Web dashboard (live polling)

### **Resilient Architecture**
- Falls back gracefully if Neo4j is unavailable
- Auto-creates missing data structures
- Persistent storage survives crashes

---

## 📊 Dashboard Features

### **Real-Time Visualizations**
1. **Psyche Profile Card**
   - Current mood indicator
   - Active goals list
   - Core values bar chart (dynamic updates)

2. **Relationship Meters**
   - Circular gauges for trust/respect
   - Smooth animations on value changes

3. **Knowledge Graph**
   - Interactive Neo4j visualization using vis-network
   - Shows character concepts and relationships

4. **Subconscious Stream**
   - Internal thought display
   - Updates with each interaction

5. **Memory Feed**
   - Chips showing triggered memories
   - Color-coded by source (vector vs graph)

---

## 🐛 Troubleshooting

### **"Module not found" errors**
```powershell
pip install -r requirements.txt
```

### **Neo4j connection failed**
- System works without Neo4j (graph features disabled)
- Check Neo4j is running: `neo4j status`
- Verify credentials in `.env`

### **Dashboard shows "DISCONNECTED"**
- Run `python main.py` first to generate `live_state.json`
- Or run `python run_dashboard.py` for integrated experience

### **Gemini API errors**
- Verify `GOOGLE_API_KEY` in `.env`
- Check API quota: https://aistudio.google.com/app/apikey
- Update to newer model if deprecated: `gemini-2.0-flash-exp`

---

## 📚 Technical Stack

- **LangChain**: Orchestration framework
- **LangGraph**: State machine for multi-stage reasoning
- **Google Gemini**: LLM (gemini-2.5-flash)
- **ChromaDB**: Vector database for semantic memory
- **Neo4j**: Graph database for concept relationships
- **Pydantic**: Data validation and serialization
- **Python**: Core application logic
- **HTML/CSS/JS**: Real-time web dashboard
- **vis-network**: Interactive graph visualization

---

## 🎯 Use Cases

1. **Interactive Storytelling**: Characters that remember and evolve
2. **Therapy/Counseling Simulations**: Realistic emotional responses
3. **Game NPCs**: Dynamic personalities that react to player behavior
4. **Research**: Studying human-AI psychological dynamics
5. **Education**: Teaching about cognitive psychology and AI

---

## 🚧 Future Enhancements

- Multi-character interactions
- Voice synthesis integration
- Long-term memory consolidation (episodic → semantic)
- Personality disorder simulations
- Memory decay/forgetting mechanisms
- Dream/reflection cycles during idle time

---

## 📄 License

MIT

---

## 🙏 Acknowledgments

Built with LangChain, Google Gemini, ChromaDB, and Neo4j.
Inspired by research in cognitive psychology, affective computing, and narrative AI. 