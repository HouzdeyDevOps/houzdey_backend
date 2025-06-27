from fastapi_socketio import SocketManager # type: ignore

# This will be initialized in main.py
_socket_manager = None

def init_socket_manager(app):
    global _socket_manager
    if _socket_manager is None:
        _socket_manager = SocketManager(
            app=app, 
            mount_location="/socket.io/", 
            cors_allowed_origins="*",
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