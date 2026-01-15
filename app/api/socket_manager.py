import socketio
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# This will be initialized in main.py
_socket_manager = None

def init_socket_manager(app):
    global _socket_manager
    if _socket_manager is None:
        # Use python-socketio directly with AsyncServer for FastAPI
        # FastAPI's CORSMiddleware handles CORS headers
        _socket_manager = socketio.AsyncServer(
            async_mode='asgi',
            # No CORS configuration - let FastAPI handle it
            cors_allowed_origins=[],  # Empty list disables Socket.IO's CORS
            ping_timeout=60,
            ping_interval=25,
            max_http_buffer_size=1000000,  # 1MB for file uploads
            logger=True,  # Enable logging to debug connection issues
            engineio_logger=True
        )
        
        logger.info("Socket.IO server initialized")
    return _socket_manager

def get_socket_manager():
    if _socket_manager is None:
        raise RuntimeError("Socket manager not initialized. Make sure init_socket_manager is called first.")
    return _socket_manager 