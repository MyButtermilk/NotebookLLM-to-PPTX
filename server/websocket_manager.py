"""
WebSocket connection manager for real-time updates.
"""

from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    """Manage WebSocket connections for job updates."""

    def __init__(self):
        # job_id -> list of websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()

        if job_id not in self.active_connections:
            self.active_connections[job_id] = []

        self.active_connections[job_id].append(websocket)

    def disconnect(self, job_id: str, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if job_id in self.active_connections:
            if websocket in self.active_connections[job_id]:
                self.active_connections[job_id].remove(websocket)

            # Clean up empty lists
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]

    async def broadcast(self, job_id: str, message: str):
        """Broadcast a message to all connections for a job."""
        if job_id not in self.active_connections:
            return

        # Send to all connected clients
        dead_connections = []

        for websocket in self.active_connections[job_id]:
            try:
                await websocket.send_text(message)
            except Exception:
                dead_connections.append(websocket)

        # Clean up dead connections
        for websocket in dead_connections:
            self.disconnect(job_id, websocket)
