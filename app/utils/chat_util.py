# Add this to your imports
from datetime import timedelta, datetime
import logging

logger = logging.getLogger(__name__)

# Track active conversations with last activity time
active_conversations = {}

async def update_conversation_activity(conversation_id):
    """Update the last activity time for a conversation"""
    active_conversations[conversation_id] = datetime.utcnow()
    
async def cleanup_inactive_conversations():
    """Remove conversation rooms that have been inactive for over 24 hours"""
    current_time = datetime.utcnow()
    inactive_threshold = current_time - timedelta(hours=24)
    
    for conversation_id, last_activity in list(active_conversations.items()):
        if last_activity < inactive_threshold:
            # Remove from tracking
            del active_conversations[conversation_id]
            logger.info(f"Cleaned up inactive conversation room: {conversation_id}")