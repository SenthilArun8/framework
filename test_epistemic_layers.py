"""
Test the new epistemic layer system
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from world_engine.main import WorldSimulation


async def test_belief_system():
    """Test that beliefs diverge from objective reality"""
    print("🧪 Testing Epistemic Layers...")
    print()
    
    # Create simulation
    sim = WorldSimulation(
        tick_interval=2.0,
        data_dir="world_data_epistemic_test",
        load_existing=False
    )
    
    # Let it run for a bit
    async def stop_after_ticks():
        await asyncio.sleep(40)  # 20 ticks
        sim.ticker.stop()
    
    await asyncio.gather(
        sim.run(),
        stop_after_ticks()
    )
    
    # Check epistemic stats
    print()
    print("=" * 60)
    print("✅ EPISTEMIC LAYER TEST RESULTS")
    print("=" * 60)
    
    world_stats = sim.world_state.get_stats()
    objective_stats = sim.world_state.objective_world.get_stats()
    
    print(f"✓ Objective facts recorded: {objective_stats['total_facts']}")
    print(f"✓ Information artifacts: {len(sim.world_state.artifact_store.artifacts)}")
    
    # Check each character's beliefs
    for char_id in sim.world_state.characters:
        belief_stats = sim.world_state.belief_graph.get_stats(char_id)
        print(f"\n✓ {char_id} beliefs:")
        print(f"  - Total beliefs: {belief_stats['total_beliefs']}")
        print(f"  - High confidence: {belief_stats['high_confidence']}")
        print(f"  - Contradictions: {belief_stats['contradictions']}")
        
        # Compare believed vs actual location
        believed_other = None
        other_char = [c for c in sim.world_state.characters if c != char_id][0]
        
        believed_loc = sim.world_state.get_character_believed_location(
            char_id,
            other_char,
            sim.world_state.current_tick
        )
        actual_loc = sim.world_state.get_character_objective_location(other_char)
        if believed_loc != actual_loc:
            print(f"  ⚠️  BELIEF DIVERGENCE: Believes {other_char} is at {believed_loc}, "
                  f"actually at {actual_loc}")
        else:
            print(f"  ✓ Belief matches reality for {other_char}'s location")
        
if __name__ == "__main__":
    asyncio.run(test_belief_system())
