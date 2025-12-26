"""
World Engine - Main Entry Point
Autonomous world simulation that runs continuously
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from world_engine.core.ticker import WorldTicker
from world_engine.core.event_queue import EventQueue
from world_engine.core.world_state import WorldState
from world_engine.entities.character import WorldCharacter, CharacterState
from world_engine.entities.location import Location
from world_engine.entities.event import Event, EventType, EventStatus
from world_engine.entities.faction import Faction, FactionType, FactionRelation
from world_engine.ai.action_generator import ActionGenerator
from world_engine.ai.director import NarrativeDirector
from world_engine.ai.autonomous_pipeline import AutonomousPipeline

# Setup logging
log_dir = Path("world_engine/logs")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / 'simulation.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class WorldSimulation:
    """
    Main simulation orchestrator.
    Coordinates ticker, event queue, and world state.
    """
    
    def __init__(
        self,
        tick_interval: float = 5.0,
        data_dir: str = "world_data",
        load_existing: bool = True
    ):
        logger.info("🌍 Initializing World Simulation...")
        
        # Core components
        self.world_state = WorldState(data_dir=data_dir)
        self.event_queue = EventQueue()
        self.ticker = WorldTicker(
            tick_interval=tick_interval,
            start_tick=0
        )
        
        # AI components
        self.action_generator = ActionGenerator()
        self.director = NarrativeDirector()
        self.autonomous_pipeline = AutonomousPipeline()
        
        # Load existing world or create new
        if load_existing:
            try:
                self.world_state.load_from_disk()
                self.ticker.current_tick = self.world_state.current_tick
            except Exception as e:
                logger.warning(f"Could not load existing world: {e}")
                logger.info("Creating new world...")
                self._create_demo_world()
        else:
            self._create_demo_world()
        
        # Register callbacks
        self._register_callbacks()
        
        logger.info("✅ World Simulation initialized")
    
    def _register_callbacks(self) -> None:
        """Register tick callbacks"""
        self.ticker.register_callback(self._on_tick)
        self.ticker.register_callback(self._process_events)
        self.ticker.register_callback(self._update_characters)
        self.ticker.register_callback(self._director_events)
        self.ticker.register_callback(self._autosave)
    
    async def _on_tick(self, tick: int) -> None:
        """Called every tick - update world state"""
        self.world_state.current_tick = tick
        
        # Log world status every 10 ticks
        if tick % 10 == 0:
            stats = self.world_state.get_stats()
            logger.info(
                f"📊 World Status: "
                f"{stats['characters']['active']} active characters, "
                f"{stats['events']['active']} active events"
            )
    
    async def _process_events(self, tick: int) -> None:
        """Process scheduled events"""
        # Process due events
        processed = await self.event_queue.process_due_events(
            tick,
            executor=self._execute_event
        )
        
        # Update active events (complete those that are done)
        self.event_queue.update_active_events(tick)
    
    async def _execute_event(self, event: Event) -> None:
        """
        Execute an event - apply its effects to the world.
        This is where event logic lives.
        """
        logger.info(f"⚡ Executing: {event.title}")
        
        if event.type == EventType.CHARACTER_TRAVEL:
            # Character arrives at destination
            char_id = event.participants[0]
            destination = event.impact.get("destination")
            if destination:
                # ✅ NEW: Pass current tick to move_character
                success = self.world_state.move_character(
                    char_id,
                    destination,
                    self.world_state.current_tick  # Add this parameter
                )
                if success:
                    event.impact["success"] = True
        
        elif event.type == EventType.CHARACTER_ACTION:
            # Generic character action
            action_type = event.impact.get("action_type")
            logger.info(f"  Character action: {action_type}")
            # TODO: Record to objective world
        
        elif event.type == EventType.CHARACTER_INTERACTION:
            # Characters meet/interact
            logger.info(f"  {len(event.participants)} characters interacting")
            # TODO: Record to objective world
        
        # Add event to world state
        self.world_state.add_event(event)
    
    async def _update_characters(self, tick: int) -> None:
        """
        Update character states using AI.
        """
        active_chars = self.world_state.get_active_characters()
        
        for character in active_chars:
            # Skip if character is busy with an active event
            if character.state in [CharacterState.TRAVELING, CharacterState.IN_CONVERSATION]:
                continue
            
            # ✅ CHANGED: Increase minimum wait time from 5 to 10 ticks
            ticks_since_last = tick - character.last_action_tick
            if ticks_since_last < 10:  # Wait longer between actions
                continue
            
            # Let AI decide what to do
            action = await self.autonomous_pipeline.process_character(
                character,
                self.world_state,
                tick
            )
            
            if action:
                # Create event from action
                event = self.action_generator.create_event_from_action(
                    character,
                    action,
                    tick
                )
                
                # Schedule event
                self.event_queue.schedule(event)
                
                # Update character state
                character.last_action_tick = tick
                if action['action_type'] == 'TRAVEL':
                    character.state = CharacterState.TRAVELING
                    character.destination = action.get('target')

    async def _director_events(self, tick: int) -> None:
        """Let narrative director create world events"""
        # Check every 20 ticks
        if tick % 20 != 0:
            return
        
        should_generate = await self.director.should_generate_event(
            self.world_state,
            tick
        )
        
        if should_generate:
            event = await self.director.generate_world_event(
                self.world_state,
                tick
            )
            
            if event:
                self.event_queue.schedule(event)
    
    async def _autosave(self, tick: int) -> None:
        """Autosave world state periodically"""
        if tick % 50 == 0:  # Every 50 ticks
            self.world_state.save_to_disk()
    
    def _create_demo_world(self) -> None:
        """Create a richer demo world"""
        logger.info("🏗️  Creating demo world...")
        
        self.world_state.world_name = "Demo World"
        
        # Create locations
        locations = [
            Location(
                id="village_alpha",
                name="Village Alpha",
                type="city",
                coordinates=(10.0, 20.0),
                description="A peaceful mountain village with hot springs",
                atmosphere="peaceful",
                connected_to=["village_beta", "forest_clearing"],
                travel_times={"village_beta": 10, "forest_clearing": 5}
            ),
            Location(
                id="village_beta",
                name="Village Beta",
                type="city",
                coordinates=(30.0, 40.0),
                description="A bustling trade hub with colorful markets",
                atmosphere="energetic",
                connected_to=["village_alpha", "ancient_ruins"],
                travel_times={"village_alpha": 10, "ancient_ruins": 15}
            ),
            Location(
                id="forest_clearing",
                name="Forest Clearing",
                type="wilderness",
                coordinates=(5.0, 15.0),
                description="A quiet glade surrounded by ancient trees",
                atmosphere="mysterious",
                connected_to=["village_alpha", "ancient_ruins"],
                travel_times={"village_alpha": 5, "ancient_ruins": 8}
            ),
            Location(
                id="ancient_ruins",
                name="Ancient Ruins",
                type="dungeon",
                coordinates=(35.0, 30.0),
                description="Crumbling stone structures overgrown with vines",
                atmosphere="eerie",
                connected_to=["village_beta", "forest_clearing"],
                travel_times={"village_beta": 15, "forest_clearing": 8}
            )
        ]
        
        for loc in locations:
            self.world_state.add_location(loc)
        
        # Create factions
        faction_alpha = Faction(
            id="faction_alpha",
            name="Alpha Clan",
            type=FactionType.TRIBE,
            description="Peaceful mountain dwellers",
            power_level=40.0,
            controlled_locations=["village_alpha"],
            relations={"faction_beta": FactionRelation.FRIENDLY}
        )
        
        faction_beta = Faction(
            id="faction_beta",
            name="Beta Traders",
            type=FactionType.GUILD,
            description="Wealthy merchant guild",
            power_level=60.0,
            controlled_locations=["village_beta"],
            relations={"faction_alpha": FactionRelation.FRIENDLY}
        )
        
        self.world_state.add_faction(faction_alpha)
        self.world_state.add_faction(faction_beta)
        
        # Create characters
        char_a = WorldCharacter(
            id="char_a",
            profile_path="data/characters/char_a.json",
            location_id="village_alpha",
            state=CharacterState.IDLE,
            active_goals=["Explore ancient ruins", "Learn about local history", "Make friends"]
        )
        
        char_b = WorldCharacter(
            id="char_b",
            profile_path="data/characters/char_b.json",
            location_id="village_beta",
            state=CharacterState.IDLE,
            active_goals=["Establish trade routes", "Gather rare goods", "Build reputation"]
        )
        
        self.world_state.add_character(char_a)
        self.world_state.add_character(char_b)
        
        # ✅ NEW: Create initial beliefs about starting positions
        current_tick = 0
        
        # Record initial positions to objective world
        fact_a = self.world_state.objective_world.record_fact(
            tick=current_tick,
            fact_type="character_spawned",
            subject="char_a",
            data={"location": "village_alpha"},
            observers=set()
        )
        
        fact_b = self.world_state.objective_world.record_fact(
            tick=current_tick,
            fact_type="character_spawned",
            subject="char_b",
            data={"location": "village_beta"},
            observers=set()
        )
        
        # Each character knows their own location with certainty
        from world_engine.epistemic.information_artifacts import ArtifactType, ReliabilityLevel
        
        artifact_a_self = self.world_state.artifact_store.create_artifact(
            tick=current_tick,
            artifact_type=ArtifactType.DIRECT_OBSERVATION,
            subject="char_a",
            claim=f"char_a is at village_alpha",
            data={"location": "village_alpha"},
            source="char_a",
            reliability=ReliabilityLevel.CERTAIN,
            known_by={"char_a"}
        )
        
        artifact_b_self = self.world_state.artifact_store.create_artifact(
            tick=current_tick,
            artifact_type=ArtifactType.DIRECT_OBSERVATION,
            subject="char_b",
            claim=f"char_b is at village_beta",
            data={"location": "village_beta"},
            source="char_b",
            reliability=ReliabilityLevel.CERTAIN,
            known_by={"char_b"}
        )
        
        # Form beliefs
        self.world_state.belief_graph.form_belief(
            "char_a",
            artifact_a_self,
            current_tick,
            trust_in_source=1.0,
            base_skepticism=0.0
        )
        
        self.world_state.belief_graph.form_belief(
            "char_b",
            artifact_b_self,
            current_tick,
            trust_in_source=1.0,
            base_skepticism=0.0
        )
        
        # Save initial state
        self.world_state.save_to_disk()
        
        logger.info("✅ Demo world created with 4 locations and initial beliefs")
    
    async def run(self) -> None:
        """Start the simulation"""
        try:
            await self.ticker.start()
        except KeyboardInterrupt:
            logger.info("🛑 Simulation interrupted by user")
            self._shutdown()
        except Exception as e:
            logger.error(f"❌ Simulation error: {e}", exc_info=True)
            self._shutdown()
            raise
    
    def _shutdown(self) -> None:
        """Clean shutdown"""
        logger.info("💾 Saving world state before shutdown...")
        self.world_state.save_to_disk()
        
        # Print final stats
        stats = self.world_state.get_stats()
        ticker_stats = self.ticker.get_stats()
        queue_stats = self.event_queue.get_stats()
        
        logger.info("📊 Final Statistics:")
        logger.info(f"  World: {stats['world_name']}")
        logger.info(f"  Total Ticks: {ticker_stats['total_ticks']}")
        logger.info(f"  Events Processed: {queue_stats['total_processed']}")
        logger.info(f"  Characters: {stats['characters']['total']}")
        logger.info(f"  Locations: {stats['locations']}")
        
        logger.info("👋 Goodbye!")


async def main():
    """Entry point"""
    # Create logs directory
    Path("world_engine/logs").mkdir(parents=True, exist_ok=True)
    
    # Create simulation
    sim = WorldSimulation(
        tick_interval=3.0,  # 3 seconds per tick for testing
        data_dir="world_data",
        load_existing=False  # Set to True to load existing world
    )
    
    # Run simulation
    await sim.run()




if __name__ == "__main__":
    print("=" * 60)
    print("🌍 AUTONOMOUS WORLD SIMULATION")
    print("=" * 60)
    print()
    print("Starting simulation...")
    print("Press Ctrl+C to stop")
    print()
    
    asyncio.run(main())