"""
Supabase service for database operations
Uses Supabase REST API (PostgREST) instead of direct psycopg2
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from supabase import create_client, Client
from app.config.settings import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """Service for interacting with Supabase via REST API"""

    def __init__(self):
        """Initialize Supabase client"""
        self.client: Optional[Client] = None

    def connect(self) -> bool:
        """Establish connection to Supabase"""
        try:
            # Prefer service_role key (bypasses RLS)
            key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
            self.client = create_client(
                settings.SUPABASE_URL,
                key
            )
            logger.info("Connected to Supabase REST API")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            return False

    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by telegram_id"""
        try:
            if not self.client:
                return None
            result = self.client.table('users') \
                .select('*') \
                .eq('telegram_id', telegram_id) \
                .limit(1) \
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user by telegram_id: {e}")
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
        """Create new user, returns user_id (UUID) or None"""
        try:
            if not self.client:
                return None
            result = self.client.table('users').insert({
                'telegram_id': telegram_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'subscription_status': 'free',
                'role': 'user',
                'last_seen_at': datetime.utcnow().isoformat(),
                'metadata': metadata or {}
            }).execute()

            if result.data:
                user_id = result.data[0]['id']
                logger.info(f"Created user telegram_id={telegram_id}: {user_id}")
                return user_id
            return None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
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
        """Get existing user or create new one"""
        user = self.get_user_by_telegram_id(telegram_id)

        if user:
            self.update_last_seen(user['id'])
            return user

        user_id = self.create_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            metadata=metadata
        )

        if user_id:
            return self.get_user_by_telegram_id(telegram_id)
        return None

    def update_last_seen(self, user_id: str) -> bool:
        """Update user's last_seen_at timestamp"""
        try:
            if not self.client:
                return False
            self.client.table('users') \
                .update({'last_seen_at': datetime.utcnow().isoformat()}) \
                .eq('id', user_id) \
                .execute()
            return True
        except Exception as e:
            logger.error(f"Error updating last_seen: {e}")
            return False

    def create_dialogue_session(self, user_id: str) -> Optional[str]:
        """Create a new dialogue session"""
        try:
            if not self.client:
                return None
            now = datetime.utcnow().isoformat()
            result = self.client.table('dialogue_sessions').insert({
                'user_id': user_id,
                'created_at': now,
                'updated_at': now
            }).execute()

            if result.data:
                return result.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None

    def get_or_create_active_session(self, user_id: str, max_idle_hours: int = 24) -> Optional[str]:
        """Get active session or create new one if last session is too old"""
        try:
            if not self.client:
                return None

            result = self.client.table('dialogue_sessions') \
                .select('id, updated_at') \
                .eq('user_id', user_id) \
                .order('updated_at', desc=True) \
                .limit(1) \
                .execute()

            if result.data:
                session = result.data[0]
                updated = datetime.fromisoformat(session['updated_at'].replace('Z', '+00:00'))
                now = datetime.utcnow().replace(tzinfo=updated.tzinfo)
                if (now - updated).total_seconds() / 3600 < max_idle_hours:
                    return session['id']

            return self.create_dialogue_session(user_id)
        except Exception as e:
            logger.error(f"Error getting/creating active session: {e}")
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
        """Save a message to the database"""
        try:
            if not self.client:
                return False

            self.client.table('messages').insert({
                'session_id': session_id,
                'user_id': user_id,
                'query_text': query_text,
                'response_text': response_text,
                'sources': sources or [],
                'is_relevant': is_relevant,
                'created_at': datetime.utcnow().isoformat()
            }).execute()

            # Update session's updated_at
            self.client.table('dialogue_sessions') \
                .update({'updated_at': datetime.utcnow().isoformat()}) \
                .eq('id', session_id) \
                .execute()

            return True
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return False

    def get_user_messages(
        self,
        user_id: str,
        limit: int = 10,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's message history"""
        try:
            if not self.client:
                return []

            query = self.client.table('messages') \
                .select('*, dialogue_sessions(created_at)') \
                .eq('user_id', user_id)

            if session_id:
                query = query.eq('session_id', session_id)

            result = query.order('created_at', desc=True) \
                .limit(limit) \
                .execute()

            return result.data or []
        except Exception as e:
            logger.error(f"Error getting user messages: {e}")
            return []

    def close(self):
        """Close connection (no-op for REST API)"""
        pass


# Global instance
supabase_service = SupabaseService()
