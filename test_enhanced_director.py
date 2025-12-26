"""Test enhanced director capabilities"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from world_engine.main import WorldSimulation


async def test_enhanced_director():
    """Test director with drama analysis and tension management"""
    print("🎬 Testing Enhanced Director...")
    print()
    
    sim = WorldSimulation(
        tick_interval=0.1,  # Fast interval
        data_dir="world_data_director_test",
        load_existing=False
    )
    
    # Run loop manually for speed
    print("Running 20 ticks fast...")
    for i in range(20):
        # Emulate ticker callbacks
        await sim._on_tick(i)
        await sim._process_events(i)
        await sim._update_characters(i)
        await sim._director_events(i)
        # Skip autosave for speed
        
        # Minimal sleep to allow async tasks to settle if any
        await asyncio.sleep(0.01)
    
    # Check results
    print()
    print("=" * 60)
    print("✅ ENHANCED DIRECTOR TEST RESULTS")
    print("=" * 60)
    
    director_stats = sim.director.get_stats()
    
    print(f"✓ Catalysts created: {director_stats['catalysts_created']}")
    print(f"✓ Opportunities identified: {director_stats['opportunities_identified']}")
    
    # Handle both new and old return formats if needed, but we expect new now
    tension_stats = director_stats.get('tension', {})
    if isinstance(tension_stats, dict):
        print(f"\n📊 Tension Management:")
        print(f"  - Current tension: {tension_stats.get('current_tension', 0):.1f}/100")
        print(f"  - Arc phase: {tension_stats.get('arc_phase', 'unknown')}")
        print(f"  - Trend: {tension_stats.get('trend', 'unknown')}")
        
    story_stats = director_stats.get('story_arcs', {})
    if isinstance(story_stats, dict):
        print(f"\n📖 Story Arcs:")
        print(f"  - Active arcs: {story_stats.get('active_arcs', 0)}")
        print(f"  - Completed arcs: {story_stats.get('completed_arcs', 0)}")
    
    # verification assertions
    assert 'tension' in director_stats, "Tension stats missing"
    assert 'story_arcs' in director_stats, "Story arc stats missing"
    
    print("\n🎉 Enhanced director working!")


if __name__ == "__main__":
    asyncio.run(test_enhanced_director())