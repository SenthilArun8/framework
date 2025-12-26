from dotenv import load_dotenv
load_dotenv()

import sys
import json
import os

# PHASE 13: Refactoring - Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from langchain_core.messages import HumanMessage
from src.graph import build_graph
from src.memory import MemoryStore, MemoryFragment, seed_memories
from src.schema import PsychologicalProfile, load_character_profile, save_character_profile, MotivationalState
from src.knowledge_graph import KnowledgeGraph
from src.motivational import DEFAULT_MOTIVATIONAL

BACKGROUND_FILE = "character.json"
CHAT_LOG_FILE = "data/chat_history.json"

# --- COLOR SCHEME ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m' # Orange/Yellow
    FAIL = '\033[91m'    # Red
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class GameEngine:
    def __init__(self):
        print(f"{Colors.HEADER}Initialize Living Character System...{Colors.ENDC}")
        # 1. Load Data
        try:
            self.profile = load_character_profile(BACKGROUND_FILE)
        except FileNotFoundError:
            print(f"{Colors.FAIL}Error: {BACKGROUND_FILE} not found. Creating default.{Colors.ENDC}")
            from schema import CoreValue, RelationshipState, PersonalityTraits
            self.profile = PsychologicalProfile(
                current_mood="Neutral",
                emotional_volatility=0.5,
                values={
                    "autonomy": CoreValue(name="Autonomy", score=0.8, justification="I must be free."),
                    "pacifism": CoreValue(name="Pacifism", score=0.6, justification="Violence is a last resort.")
                },
                goals=["Survive", "Understanding"],
                relationships={
                    "User_123": RelationshipState(user_id="User_123", trust_level=50.0, respect_level=50.0, shared_history_summary="Met recently.")
                },
                traits=PersonalityTraits(emotional_volatility=0.6, focus_fragility=0.4)
            )
        
        # New: Motivational State (Ephemeral for now, or could save to json)
        self.motivational = DEFAULT_MOTIVATIONAL.model_copy(deep=True)

        # 2. Memory
        self.memory_store = MemoryStore()
        seed_memories(self.memory_store)
        
        # 3. Knowledge Graph
        # ... (KG init unchanged)
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_pass = os.getenv("NEO4J_PASSWORD", "password")
        neo4j_enabled = os.getenv("NEO4J_ENABLED", "false").lower() == "true"
        
        if neo4j_enabled:
            self.kg = KnowledgeGraph(neo4j_uri, neo4j_user, neo4j_pass)
            if self.kg.check_connection():
                print(f"{Colors.GREEN}Connected to Knowledge Graph.{Colors.ENDC}")
                print(f"{Colors.GREEN}Connected to Knowledge Graph.{Colors.ENDC}")
                self.kg.ensure_relationship_exists(self.profile.name, "User_123")
            else:
                print(f"{Colors.WARNING}Knowledge Graph Unreachable (Skipping GraphRAG).{Colors.ENDC}")
                self.kg = None
        else:
            print(f"{Colors.WARNING}Neo4j disabled (set NEO4J_ENABLED=true to enable).{Colors.ENDC}")
            self.kg = None

        # 4. Build Graph
        self.app = build_graph(self.memory_store, self.kg)
        
        # 5. Load Chat History
        if os.path.exists(CHAT_LOG_FILE):
            try:
                with open(CHAT_LOG_FILE, "r") as f:
                    self.chat_history = json.load(f)
            except Exception:
                self.chat_history = []
        else:
            self.chat_history = []
        
        # Ensure 'User_123' exists in relationships with default values if not present
        if "User_123" not in self.profile.relationships:
             from schema import RelationshipState
             self.profile.relationships["User_123"] = RelationshipState(trust_level=50.0, respect_level=50.0)

        # Initial Dashboard Dump (so widget isn't empty on load)
        self.dump_dashboard({
            "triggered_memories": [], 
            "subconscious": "System Initialized.",
            "graph_logs": []
        })
        
        self.dashboard_callback = None

    def set_dashboard_callback(self, callback):
        self.dashboard_callback = callback

    def process_turn(self, user_input):
        if not self.profile: return None, None
        
        self.chat_history.append({"role": "human", "content": user_input})
        # Save History immediately
        with open(CHAT_LOG_FILE, "w") as f:
            json.dump(self.chat_history, f, indent=2)
            
        old_profile = self.profile.model_copy(deep=True)
        
        inputs = {
            "messages": [HumanMessage(content=user_input)],
            "profile": self.profile.model_dump(),
            "memories": [], 
            "subconscious_thought": "",
            "motivational": self.motivational.model_dump(),
            "old_profile": old_profile.model_dump() # Phase 9: Passed for Delta Node/Persist Node
        }
        
        # INTERMEDIATE DUMP (Phase 12 Fix)
        # Update dashboard immediately so the user's message persists during the "Thinking" phase.
        # Otherwise, the frontend polling overwrites the optimistic UI with stale data.
        self.dump_dashboard({
            "triggered_memories": [],
            "subconscious": "Thinking...",
            "graph_logs": [],
            "old_profile": old_profile,
            "motivational": self.motivational
        })
        
        graph_logs = []
        # Retrieval (Now handled by brain.py via Semantic Graph RAG)
        
        # Run Graph
        try:
            print(f"[DEBUG] Invoking LangGraph with inputs...")
            output = self.app.invoke(inputs)
            print(f"[DEBUG] LangGraph execution completed successfully")
        except Exception as e:
            import traceback
            error_msg = f"Graph Execution Failed: {e}\n{traceback.format_exc()}"
            print(f"{Colors.FAIL}[ERROR] {error_msg}{Colors.ENDC}")
            # Log to file as well
            with open("logs/graph_errors.txt", "a") as f:
                from datetime import datetime
                f.write(f"\n[{datetime.now()}] {error_msg}\n")
            return None, None
            
        # Update Profile
        if isinstance(output['profile'], dict):
             self.profile = PsychologicalProfile(**output['profile'])
        else:
             self.profile = output['profile']
        
        # Update Motivational State
        if output.get("motivational"):
            if isinstance(output['motivational'], dict):
                self.motivational = MotivationalState(**output['motivational'])
            else:
                self.motivational = output['motivational']

        bot_msg = output['messages'][-1].content
        self.chat_history.append({"role": "ai", "content": bot_msg})
        
        # Persistence is now handled by persist_node in the graph!
        # no more _update_graph or save_character_profile here.
        
        # Prepare Analysis Data
        analysis = {
            "triggered_memories": output.get('memories', []),
            "subconscious": output.get('subconscious_thought', 'N/A'),
            "graph_logs": graph_logs,
            "old_profile": old_profile,
            "motivational": self.motivational
        }
        self.dump_dashboard(analysis)
        return bot_msg, analysis

    def reset_game(self):
        """Resets the character to default state."""
        print(f"{Colors.WARNING}⚠️  RESETTING GAME STATE...{Colors.ENDC}")
        from src.schema import CoreValue, RelationshipState, PersonalityTraits
        
        # 1. Reset Profile
        # 1. Reset Profile
        INITIAL_FILE = "initial_character.json"
        try:
            # Copy template to active file
            import shutil
            if os.path.exists(INITIAL_FILE):
                shutil.copy(INITIAL_FILE, BACKGROUND_FILE)
                self.profile = load_character_profile(BACKGROUND_FILE)
            else:
                # Fallback if template missing
                print(f"{Colors.FAIL}Error: {INITIAL_FILE} missing. Using hardcoded backup.{Colors.ENDC}")
                self.profile = PsychologicalProfile(
                    name="Leo", # Fallback Name
                    current_mood="Neutral",
                    emotional_volatility=0.6,
                )
                save_character_profile(self.profile, BACKGROUND_FILE)
        except Exception as e:
             print(f"{Colors.FAIL}Reset Error: {e}{Colors.ENDC}")
        
        # 2. Reset Chat History
        self.chat_history = []
        with open(CHAT_LOG_FILE, "w") as f:
            json.dump(self.chat_history, f)
            
        # 3. Reset Motivational State
        self.motivational = DEFAULT_MOTIVATIONAL.model_copy(deep=True)
        
        # 4. Reset Vector Memory
        if self.memory_store:
            self.memory_store.clear_memories()
            from src.memory import seed_memories
            seed_memories(self.memory_store)

        if self.kg:
            self.kg.clear_database()
            self.kg.ensure_relationship_exists(self.profile.name, "User_123")
            
        # 5. Dump Dashboard
        self.dump_dashboard({
            "triggered_memories": [], 
            "subconscious": "System Reset Complete.",
            "graph_logs": [],
            "old_profile": self.profile,
            "motivational": self.motivational
        })
        return "Character Reset Successfully."

    def dump_dashboard(self, analysis):
        # Fetch Graph Viz Data
        viz_data = {"nodes": [], "edges": []}
        if self.kg:
            viz_data = self.kg.get_viz_data()
            print(f"📊 [Dashboard]: Sending {len(viz_data['nodes'])} nodes, {len(viz_data['edges'])} edges to frontend.")
            
        state = {
            "profile": self.profile.model_dump(),
            "chat_log": self.chat_history,
            "last_turn": {
                "memories": [m if isinstance(m, dict) else m.model_dump() for m in analysis['triggered_memories']],
                "subconscious": analysis.get('subconscious', ''),
                "graph_connections": analysis.get('graph_logs', [])
            },
            "motivational": analysis.get("motivational").model_dump() if analysis.get("motivational") else None,
            "knowledge_graph": viz_data
        }
        
        # Callback for SSE (Phase 21 Optimization)
        if hasattr(self, 'dashboard_callback') and self.dashboard_callback:
            try:
                self.dashboard_callback(state)
            except Exception as e:
                print(f"Callback Error: {e}")

        try:
             if not os.path.exists("dashboard"): os.makedirs("dashboard")
             
             # Atomic Write (Phase 12)
             # Prevent race condition where JS reads partially written file
             tmp_file = "dashboard/live_state.tmp"
             final_file = "dashboard/live_state.json"
             
             with open(tmp_file, "w") as f:
                json.dump(state, f, default=str)
                
             try:
                 os.replace(tmp_file, final_file)
                 print("📊 [Dashboard]: State Dumped Successfully.")
             except OSError:
                 # Windows fallback if file is locked
                 import shutil
                 shutil.move(tmp_file, final_file)
             
        except Exception as e:
            print(f"HUD Dump Error: {e}")
            # Final Fallback
            try:
                with open("dashboard/live_state.json", "w") as f:
                    json.dump(state, f, default=str)
            except: pass

def main():
    engine = GameEngine()
    print("\n" + "="*50)
    print(f"Chatting with {Colors.BOLD}{engine.profile.current_mood}{Colors.ENDC} {engine.profile.name}.")
    print(f"{Colors.HEADER}System: Interaction Sandbox Active (HUD Enabled).{Colors.ENDC}")
    print("="*50 + "\n")

    while True:
        user_input = input(f"{Colors.BOLD}You: {Colors.ENDC}")
        if user_input.lower() in ["quit", "exit"]:
            if engine.kg: engine.kg.close()
            break
        
        result = engine.process_turn(user_input)
        if result and result[0]:
            msg, analysis = result
            
            # --- HUD CONSOLE VISUALIZATION ---
            print("")
            # Memories
            for m in analysis['triggered_memories']:
                desc = m.get('description', '') if isinstance(m, dict) else m.description
                snippet = (desc[:75] + '...') if len(desc) > 75 else desc
                print(f"{Colors.BLUE}📂 [Memory Triggered]: \"{snippet}\"{Colors.ENDC}")
            
            # Mood
            old_p = analysis['old_profile']
            new_p = engine.profile
            if old_p.current_mood != new_p.current_mood:
                 print(f"{Colors.HEADER}🧠 [State Change] Mood: '{old_p.current_mood}' -> '{new_p.current_mood}'{Colors.ENDC}")
            
            # Stats (Simplified loop)
            user_id = "User_123"
            if user_id in new_p.relationships:
                new_rel = new_p.relationships[user_id]
                old_rel = old_p.relationships[user_id]
                if abs(new_rel.trust_level - old_rel.trust_level) > 0.001:
                    diff = new_rel.trust_level - old_rel.trust_level
                    color = Colors.GREEN if diff > 0 else Colors.FAIL
                    print(f"{color}📈 [State Change] Trust: {old_rel.trust_level:.2f} -> {new_rel.trust_level:.2f}{Colors.ENDC}")

            print(f"{Colors.BOLD}Elias: {msg}{Colors.ENDC}")
            print(f"{Colors.CYAN}💭 [Internal Thought]: \"{analysis['subconscious']}\"{Colors.ENDC}")
            print("-" * 30 + "\n")

if __name__ == "__main__":
    main()
