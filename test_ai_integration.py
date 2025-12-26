"""
Test AI-driven autonomous behavior
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from world_engine.main import WorldSimulation


async def test_ai_decisions():
    """Test that characters make AI-driven decisions"""
    print("🧪 Testing AI Integration...")
    print()
    
    # Create simulation
    sim = WorldSimulation(
        tick_interval=2.0,  # 2 seconds per tick
        data_dir="world_data_ai_test",
        load_existing=False
    )
    
    # Run simulation
    await sim.run()

    # Run for 60 ticks
    async def stop_after_ticks():
        await asyncio.sleep(120)  # 2 minutes
        sim.ticker.stop()

    await asyncio.gather(
        sim.run(),
        stop_after_ticks()
    )

    # Check results
    print()
    print("=" * 60)
    print("✅ AI INTEGRATION TEST RESULTS")
    print("=" * 60)

    stats = sim.world_state.get_stats()
    queue_stats = sim.event_queue.get_stats()

    print(f"✓ Events generated: {queue_stats['total_scheduled']}")
    print(f"✓ Events processed: {queue_stats['total_processed']}")
    print(f"✓ Narrative tension: {sim.director.tension_level:.1f}/100")
    print()

    # Verify AI generated some events
    assert queue_stats['total_scheduled'] > 2, "AI didn't generate enough events!"

    print("🎉 AI integration successful!")

if __name__ == "__main__":
    asyncio.run(test_ai_decisions())
