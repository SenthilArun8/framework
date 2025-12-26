from fastapi import APIRouter
from ..core.world_state import WorldState
from ..utils.change_tracker import ChangeStream
from starlette.responses import StreamingResponse

router = APIRouter()
world = WorldState()

@router.get("/status")
def get_status():
    return {"running": world.ticker.running, "time": world.ticker.current_time}

@router.get("/stream")
async def stream_world_events():
    return StreamingResponse(ChangeStream.subscribe(), media_type="text/event-stream")

@router.post("/start")
def start_world():
    world.start()
    return {"status": "started"}

@router.post("/stop")
def stop_world():
    world.stop()
    return {"status": "stopped"}
