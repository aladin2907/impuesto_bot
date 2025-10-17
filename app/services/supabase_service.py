"""
Supabase service for database operations
Simplified user management with direct telegram_id lookup
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.config.settings import settings


class SupabaseService:
    """Service for interacting with Supabase PostgreSQL database"""
    
    def __init__(self):
        """Initialize database connection"""
        self.connection = None
    
    def connect(self) -> bool:
        """Establish connection to Supabase PostgreSQL"""
        try:
            self.connection = psycopg2.connect(
                settings.SUPABASE_DB_URL,
                cursor_factory=RealDictCursor
            )
            print("Connected to Supabase PostgreSQL")
            return True
        except Exception as e:
            print(f"Failed to connect to Supabase: {e}")
            return False
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user by telegram_id - simple single query!
        Returns user dict or None
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM users
                WHERE telegram_id = %s
            """, (telegram_id,))
            
            return cursor.fetchone()
            
        except Exception as e:
            print(f"Error getting user by telegram_id: {e}")
            return None
    
    def create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create new user with telegram data
        Returns user_id (UUID) or None
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO users 
                (telegram_id, username, first_name, last_name, phone, 
                 subscription_status, role, last_seen_at, metadata)
                VALUES (%s, %s, %s, %s, %s, 'free', 'user', NOW(), %s)
                RETURNING id
            """, (
                telegram_id,
                username,
                first_name,
                last_name,
                phone,
                psycopg2.extras.Json(metadata or {})
            ))
            
            user_id = cursor.fetchone()['id']
            self.connection.commit()
            print(f"Created new user with telegram_id {telegram_id}: {user_id}")
            return user_id
            
        except Exception as e:
            print(f"Error creating user: {e}")
            self.connection.rollback()
            return None
    
    def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get existing user or create new one - super simple now!
        Returns full user dict
        """
        # Try to get existing user
        user = self.get_user_by_telegram_id(telegram_id)
        
        if user:
            # Update last_seen_at
            self.update_last_seen(user['id'])
            return user
        
        # Create new user
        user_id = self.create_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            metadata=metadata
        )
        
        if user_id:
            # Return created user
            return self.get_user_by_telegram_id(telegram_id)
        
        return None
    
    def update_last_seen(self, user_id: str) -> bool:
        """Update user's last_seen_at timestamp"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE users
                SET last_seen_at = NOW()
                WHERE id = %s
            """, (user_id,))
            self.connection.commit()
            return True
            
        except Exception as e:
            print(f"Error updating last_seen: {e}")
            self.connection.rollback()
            return False
    
    def get_user_subscription_status(self, user_id: str) -> str:
        """Get user's subscription status"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT subscription_status, subscription_expires_at
                FROM users
                WHERE id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return 'free'
            
            # Check if premium expired
            if result['subscription_status'] == 'premium':
                if result['subscription_expires_at'] and result['subscription_expires_at'] < datetime.now():
                    # Expired, update to free
                    cursor.execute("""
                        UPDATE users SET subscription_status = 'free'
                        WHERE id = %s
                    """, (user_id,))
                    self.connection.commit()
                    return 'free'
            
            return result['subscription_status']
            
        except Exception as e:
            print(f"Error getting subscription status: {e}")
            return 'free'
    
    def create_dialogue_session(self, user_id: str) -> Optional[str]:
        """Create a new dialogue session"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO dialogue_sessions (user_id, created_at, updated_at)
                VALUES (%s, NOW(), NOW())
                RETURNING id
            """, (user_id,))
            
            session_id = cursor.fetchone()['id']
            self.connection.commit()
            return session_id
            
        except Exception as e:
            print(f"Error creating session: {e}")
            self.connection.rollback()
            return None
    
    def get_or_create_active_session(self, user_id: str, max_idle_hours: int = 24) -> Optional[str]:
        """
        Get active session or create new one if last session is too old
        """
        try:
            cursor = self.connection.cursor()
            
            # Get most recent session
            cursor.execute("""
                SELECT id, updated_at
                FROM dialogue_sessions
                WHERE user_id = %s
                ORDER BY updated_at DESC
                LIMIT 1
            """, (user_id,))
            
            result = cursor.fetchone()
            
            if result:
                # Check if session is still active (within max_idle_hours)
                time_diff = datetime.now() - result['updated_at']
                if time_diff.total_seconds() / 3600 < max_idle_hours:
                    return result['id']
            
            # Create new session
            return self.create_dialogue_session(user_id)
            
        except Exception as e:
            print(f"Error getting/creating active session: {e}")
            return None
    
    def save_message(
        self,
        session_id: str,
        user_id: str,
        query_text: str,
        response_text: Optional[str] = None,
        sources: Optional[List[Dict]] = None,
        is_relevant: bool = True
    ) -> bool:
        """
        Save a message to the database
        Now with user_id instead of channel_id - much simpler!
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO messages 
                (session_id, user_id, query_text, response_text, sources, is_relevant, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (
                session_id,
                user_id,
                query_text,
                response_text,
                psycopg2.extras.Json(sources or []),
                is_relevant
            ))
            
            # Update session's updated_at
            cursor.execute("""
                UPDATE dialogue_sessions
                SET updated_at = NOW()
                WHERE id = %s
            """, (session_id,))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            print(f"Error saving message: {e}")
            self.connection.rollback()
            return False
    
    def get_user_messages(
        self,
        user_id: str,
        limit: int = 10,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user's message history
        Optionally filter by session_id
        """
        try:
            cursor = self.connection.cursor()
            
            if session_id:
                cursor.execute("""
                    SELECT m.*, ds.created_at as session_started
                    FROM messages m
                    JOIN dialogue_sessions ds ON m.session_id = ds.id
                    WHERE m.user_id = %s AND m.session_id = %s
                    ORDER BY m.created_at DESC
                    LIMIT %s
                """, (user_id, session_id, limit))
            else:
                cursor.execute("""
                    SELECT m.*, ds.created_at as session_started
                    FROM messages m
                    JOIN dialogue_sessions ds ON m.session_id = ds.id
                    WHERE m.user_id = %s
                    ORDER BY m.created_at DESC
                    LIMIT %s
                """, (user_id, limit))
            
            return cursor.fetchall() or []
            
        except Exception as e:
            print(f"Error getting user messages: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()


# Global instance
supabase_service = SupabaseService()
