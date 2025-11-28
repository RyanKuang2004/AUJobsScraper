from typing import Dict, Any, List
from .base_database import BaseDatabase


class ConversationDatabase(BaseDatabase):
    """Database class for managing conversation history in Supabase."""
    
    def save_message(self, session_id: str, message_type: str, message: str) -> Dict[str, Any]:
        """
        Add a message to the conversations table.
        
        Args:
            session_id: The unique identifier for the conversation session
            message_type: Type of message ('user' or 'assistant')
            message: The message content
            
        Returns:
            The inserted record
        """
        insert_payload = {
            "session_id": session_id,
            "type": message_type,
            "message": message
        }
        
        response = self.supabase.table("conversations").insert(insert_payload).execute()
        return response.data[0] if response.data else {}
    
    def get_messages(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieve all messages for a given session.
        
        Args:
            session_id: The unique identifier for the conversation session
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message records ordered by creation time
        """
        response = self.supabase.table("conversations") \
            .select("*") \
            .eq("session_id", session_id) \
            .order("created_at", desc=False) \
            .limit(limit) \
            .execute()
        
        return response.data
    
    def clear_session(self, session_id: str) -> bool:
        """
        Delete all messages for a given session.
        
        Args:
            session_id: The unique identifier for the conversation session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.supabase.table("conversations") \
                .delete() \
                .eq("session_id", session_id) \
                .execute()
            return True
        except Exception as e:
            print(f"Error clearing session {session_id}: {e}")
            return False
    
    def get_all_sessions(self) -> List[str]:
        """
        Get a list of all unique session IDs.
        
        Returns:
            List of unique session IDs
        """
        response = self.supabase.table("conversations") \
            .select("session_id") \
            .execute()
        
        # Extract unique session IDs
        session_ids = set()
        if response.data:
            for row in response.data:
                session_ids.add(row.get("session_id"))
        
        return list(session_ids)
    
    def get_session_count(self, session_id: str) -> int:
        """
        Get the message count for a specific session.
        
        Args:
            session_id: The unique identifier for the conversation session
            
        Returns:
            Number of messages in the session
        """
        response = self.supabase.table("conversations") \
            .select("id", count="exact") \
            .eq("session_id", session_id) \
            .execute()
        
        return response.count if hasattr(response, 'count') else len(response.data)
