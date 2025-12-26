# Living Character AI Framework

A sophisticated cognitive architecture for creating **dynamic, psychologically complex AI characters** that evolve over time. This framework goes beyond simple roleplay by simulating a character's internal drives, emotional needs, subconscious thoughts, and deep-seated memories.

It features a **real-time observability dashboard** that allows you to watch the character's "brain" work—seeing their active memories, shifting values, and emotional state as they interact with you.

---

## 🧠 Core Architecture

The system is built on **LangGraph** with a 7-stage cognitive pipeline that runs for every user interaction:

### 1. **Retrieve Node** (Contextual Grounding)
-   **Emotional Query Expansion**: The system analyzes the *emotional themes* of your message (e.g., "Abandonment", "Warmth") rather than just keywords.
-   **Vector Search**: Retrieves relevant episodic memories from **ChromaDB**.
-   **Semantic Graph RAG**: If specific entities are mentioned, it queries **Neo4j** to find the character's "opinion paths" (e.g., `Elias -[HATES]-> Empire -[DESTROYED]-> Home`).

### 2. **Motivational Node** (The "Id")
-   **Needs System**: Tracks 5 core needs (Belonging, Autonomy, Security, Competence, Novelty) which decay over time or react to intent.
-   **Intent Analysis**: An internal LLM classifies your intent (SUPPORT, CRITICISM, THREAT, etc.) to adjust emotional state.
-   **Strategy Blending**: Calculates "Pressures" (Stress, Attachment, Conflict) to create a **mixed behavioral strategy** (e.g., `60% Defensive + 40% Fragmented`).
-   **Cognitive Load**: Tracks mental capacity; high complexity inputs increase load, causing deeper dissociation or fragility.

### 3. **Subconscious Node** (The "Inner Voice")
-   Generates a raw, unfiltered internal monologue.
-   Reflects on the input without social constraints.
-   Decides if the user is trustworthy or manipulating reality ("Hypothesis Testing").

### 4. **Delta Node** (Neuroplasticity)
-   **Psychological Evolution**: Updates the character's **Mood**, **Core Values**, and **Relationship Metrics** (Trust/Respect).
-   **Scaffolding Logic**: If Cognitive Load is high, the character becomes more susceptible to external structure (compliant). If low, they assert **Autonomy**.
-   **Trust Damping**: Trust is harder to gain as it gets higher, but easily lost.

### 5. **Learning Node** (Memory Formation)
-   Analyzes the interaction to decide if it is **significant enough** to form a new permanent memory.
-   If meaningful, it commits a new memory fragment to the Vector DB.

### 6. **Generate Node** (Expression)
-   Produces the final spoken response.
-   Follows the **Active Strategy** (e.g., "Be curt and defensive", "Stutter and dissociate") derived from the Motivational Node.
-   Influenced by the Subconscious thought but not identical to it.

### 7. **Persist Node** (Side Effects)
-   Updates the **Neo4j Knowledge Graph** with new interaction events and relationship changes.
-   Saves the `PsychologicalProfile` to `character.json`.

---

## 💾 Dual-Memory System

1.  **Episodic Memory (ChromaDB)**
    *   Stores "backstory" and raw interaction logs.
    *   Retrieved via semantic similarity (embeddings).
    *   *Good for:* Vague feelings, specific past events ("The drone crash").

2.  **Semantic Memory (Neo4j)**
    *   Stores structured relationships and facts.
    *   *Good for:* Concrete opinions, social connections, and causality.
    *   *Visualized:* In the dashboard as a force-directed graph.

---

## 🖥️ Real-Time Dashboard

The framework runs a **Threading HTTP Server** (Port 8000) with **Server-Sent Events (SSE)** for zero-latency updates.

**Key Visualizations:**
-   **Psyche Panel**: Live bars for Mood, Values, and Needs.
-   **Relationship Meters**: Circular gauges for Trust and Respect (User-specific).
-   **Memory Feed**: Shows exactly which memories were triggered by the last message.
-   **Inner Thought**: Displays the raw subconscious monologue.
-   **Knowledge Graph**: Interactive visualization of the Neo4j database.
-   **Strategy Radar**: A radar chart showing the current blend of behavioral strategies.

---

## 📂 Project Structure

```text
framework/
├── src/
│   ├── brain.py          # Core LangGraph nodes (Retrieve, Subconscious, Delta, Generate, Learn, Persist)
│   ├── motivational.py   # Emergent psychology (Needs, Intent Analysis, Strategy Blending)
│   ├── memory.py         # ChromaDB wrapper
│   ├── knowledge_graph.py# Neo4j driver & querying logic
│   ├── graph.py          # StateGraph definition
│   ├── schema.py         # Pydantic models (MemoryFragment, PsychologicalProfile, MotivationalState)
│   └── state.py          # AgentState TypedDict
├── dashboard/
│   ├── index.html        # Dashboard UI
│   └── script.js         # Frontend logic (SSE, Charts)
├── data/
│   ├── character.json    # Persistent profile state
│   ├── chroma_db/        # Vector database files
│   └── chat_history.json # Chat log
├── run_dashboard.py      # Main Entry Point (HTTP Server + Chat API)
└── main.py              # Game Engine & CLI logic
```

---

## 🚀 Getting Started

### Prerequisites

1.  **Python 3.10+**
2.  **Google Gemini API Key**: Set `GOOGLE_API_KEY` in your environment or `.env` file.
3.  **Neo4j** (Optional but recommended):
    *   Set `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` in `.env`.
    *   Set `NEO4J_ENABLED=true`.

### Installation

```bash
pip install -r requirements.txt
```

### Running the System

**1. Dashboard Mode (Recommended)**
Start the server and UI:
```bash
python run_dashboard.py
```
*   Open `http://localhost:8000` in your browser.
*   The dashboard will connect via SSE.
*   Use the chat input at the bottom to interact.

**2. Console Mode (Headless)**
Run the engine in the terminal:
```bash
python main.py
```

### Resetting
To wipe memories and start fresh:
-   Click the **RESET** button in the dashboard.
-   Or call the `/reset_character` endpoint.
-   This restores `initial_character.json` and clears the Vector/Graph databases.

---

## 🛠️ Customization

-   **Character Backstory**: Edit `data/initial_character.json`.
-   **Psychological Baseline**: Modify `DEFAULT_MOTIVATIONAL` in `src/motivational.py` to change how the character reacts to stress (e.g., changing Attachment Style from "Avoidant" to "Anxious").
-   **Strategies**: Adjust `STRATEGY_MAP` in `src/brain.py` to define new behavioral outputs.
