from fastapi_socketio import SocketManager # type: ignore
from app.core.config import settings

# This will be initialized in main.py
_socket_manager = None

def init_socket_manager(app):
    global _socket_manager
    if _socket_manager is None:
        # Get allowed origins from settings
        allowed_origins = []
        if settings.BACKEND_CORS_ORIGINS:
            if isinstance(settings.BACKEND_CORS_ORIGINS, str):
                allowed_origins = [settings.BACKEND_CORS_ORIGINS]
            else:
                allowed_origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
        
        # Add localhost for development
        if settings.ENVIRONMENT == "local":
            allowed_origins.extend([
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001"
            ])
        
        _socket_manager = SocketManager(
            app=app, 
            mount_location="/socket.io/", 
            cors_allowed_origins=allowed_origins if allowed_origins else "*",
            # Add configuration for better connection handling
            engineio_options={
                'ping_timeout': 60,
                'ping_interval': 25,
                'max_http_buffer_size': 1000000  # 1MB for file uploads
            }
        )
    return _socket_manager

def get_socket_manager():
    if _socket_manager is None:
        raise RuntimeError("Socket manager not initialized. Make sure init_socket_manager is called first.")
    return _socket_manager 