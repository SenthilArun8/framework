"""
Quick test script to verify the world engine works
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from world_engine.main import WorldSimulation


async def test_basic_simulation():
    """Run simulation for 30 ticks and verify it works"""
    print("🧪 Testing World Engine...")
    print()
    
    # Create simulation
    sim = WorldSimulation(
        tick_interval=1.0,  # Fast for testing
        data_dir="world_data_test",
        load_existing=False
    )
    
    # Run for 30 ticks
    async def stop_after_ticks():
        await asyncio.sleep(32)  # Give a buffer to ensure > 30 ticks
        sim.ticker.stop()
    
    # Run both tasks
    await asyncio.gather(
        sim.run(),
        stop_after_ticks()
    )
    
    # Verify results
    print()
    print("=" * 60)
    print("✅ TEST RESULTS")
    print("=" * 60)
    
    stats = sim.world_state.get_stats()
    ticker_stats = sim.ticker.get_stats()
    queue_stats = sim.event_queue.get_stats()
    
    print(f"✓ Ticks processed: {ticker_stats['total_ticks']}")
    print(f"✓ Events processed: {queue_stats['total_processed']}")
    print(f"✓ Characters: {stats['characters']['total']}")
    print(f"✓ Locations: {stats['locations']}")
    print()
    
    # Check that events were processed
    assert queue_stats['total_processed'] > 0, "No events were processed!"
    assert ticker_stats['total_ticks'] >= 30, "Not enough ticks processed!"
    
    print("🎉 All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_basic_simulation())