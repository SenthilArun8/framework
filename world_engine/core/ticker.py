"""
World Ticker - The heartbeat of the simulation
Advances time and orchestrates all updates
"""
import asyncio
from typing import Callable, List, Awaitable
import logging

logger = logging.getLogger(__name__)


class WorldTicker:
    """
    Drives the simulation forward tick by tick.
    Each tick represents a unit of time in the world.
    """
    
    def __init__(self, tick_interval: float = 5.0, start_tick: int = 0):
        """
        Args:
            tick_interval: Real-world seconds between ticks
            start_tick: Starting tick number (for resuming)
        """
        self.tick_interval = tick_interval
        self.current_tick = start_tick
        self.callbacks: List[Callable[[int], Awaitable[None]]] = []
        self.running = False
        
        # Statistics
        self.total_ticks_processed = 0
        self.average_tick_duration = 0.0
        
    def register_callback(self, callback: Callable[[int], Awaitable[None]]) -> None:
        """
        Register a coroutine to be called each tick.
        
        Args:
            callback: Async function that takes tick number as argument
        """
        self.callbacks.append(callback)
        logger.info(f"Registered callback: {callback.__name__}")
        
    async def start(self) -> None:
        """
        Start the simulation loop.
        Runs indefinitely until stop() is called.
        """
        self.running = True
        logger.info(f"🌍 World simulation started at tick {self.current_tick}")
        logger.info(f"⏱️  Tick interval: {self.tick_interval}s")
        
        try:
            while self.running:
                await self._process_tick()
                await asyncio.sleep(self.tick_interval)
        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
            self.stop()
        except Exception as e:
            logger.error(f"Simulation error: {e}", exc_info=True)
            self.stop()
            raise
            
    async def _process_tick(self) -> None:
        """Process a single tick"""
        import time
        start_time = time.time()
        
        self.current_tick += 1
        logger.info(f"⏰ Tick {self.current_tick}")
        
        # Execute all registered callbacks
        for callback in self.callbacks:
            try:
                await callback(self.current_tick)
            except Exception as e:
                logger.error(
                    f"Error in callback {callback.__name__}: {e}",
                    exc_info=True
                )
        
        # Update statistics
        tick_duration = time.time() - start_time
        self.total_ticks_processed += 1
        self.average_tick_duration = (
            (self.average_tick_duration * (self.total_ticks_processed - 1) + 
             tick_duration) / self.total_ticks_processed
        )
        
        if tick_duration > self.tick_interval:
            logger.warning(
                f"⚠️  Tick took {tick_duration:.2f}s "
                f"(longer than interval {self.tick_interval}s)"
            )
            
    def stop(self) -> None:
        """Stop the simulation loop"""
        self.running = False
        logger.info(f"🛑 World simulation stopped at tick {self.current_tick}")
        logger.info(
            f"📊 Processed {self.total_ticks_processed} ticks, "
            f"avg duration: {self.average_tick_duration:.3f}s"
        )
        
    def get_stats(self) -> dict:
        """Get simulation statistics"""
        return {
            "current_tick": self.current_tick,
            "total_ticks": self.total_ticks_processed,
            "average_tick_duration": self.average_tick_duration,
            "running": self.running
        }