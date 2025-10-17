"""
Tests for SupabaseService - simplified user management
Testing user creation, retrieval, and message storage
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.services.supabase_service import SupabaseService
from datetime import datetime


@pytest.fixture
def mock_connection():
    """Mock database connection"""
    connection = Mock()
    cursor = Mock()
    connection.cursor.return_value = cursor
    return connection, cursor


@pytest.fixture
def supabase_service(mock_connection):
    """Create SupabaseService with mocked connection"""
    service = SupabaseService()
    service.connection = mock_connection[0]
    return service


class TestUserOperations:
    """Test user creation and retrieval"""
    
    def test_get_user_by_telegram_id_existing_user(self, supabase_service, mock_connection):
        """Test retrieving existing user by telegram_id"""
        _, cursor = mock_connection
        
        # Mock existing user
        cursor.fetchone.return_value = {
            'id': 'user-uuid-123',
            'telegram_id': 123456789,
            'username': 'testuser',
            'first_name': 'Test',
            'subscription_status': 'free',
            'last_seen_at': datetime.now()
        }
        
        user = supabase_service.get_user_by_telegram_id(123456789)
        
        assert user is not None
        assert user['telegram_id'] == 123456789
        assert user['username'] == 'testuser'
        cursor.execute.assert_called_once()
        
    def test_get_user_by_telegram_id_not_found(self, supabase_service, mock_connection):
        """Test retrieving non-existent user"""
        _, cursor = mock_connection
        cursor.fetchone.return_value = None
        
        user = supabase_service.get_user_by_telegram_id(999999)
        
        assert user is None
    
    def test_create_user_success(self, supabase_service, mock_connection):
        """Test creating new user"""
        connection, cursor = mock_connection
        
        # Mock successful insert
        cursor.fetchone.return_value = {'id': 'new-user-uuid'}
        
        user_id = supabase_service.create_user(
            telegram_id=123456789,
            username='newuser',
            first_name='New',
            last_name='User'
        )
        
        assert user_id == 'new-user-uuid'
        cursor.execute.assert_called()
        connection.commit.assert_called_once()
    
    def test_get_or_create_user_existing(self, supabase_service, mock_connection):
        """Test get_or_create with existing user"""
        _, cursor = mock_connection
        
        # Mock existing user
        cursor.fetchone.return_value = {
            'id': 'existing-uuid',
            'telegram_id': 123456789,
            'username': 'existing'
        }
        
        user_data = supabase_service.get_or_create_user(
            telegram_id=123456789,
            username='existing'
        )
        
        assert user_data is not None
        assert user_data['id'] == 'existing-uuid'
    
    def test_get_or_create_user_new(self, supabase_service, mock_connection):
        """Test get_or_create with new user"""
        connection, cursor = mock_connection
        
        # First call returns None (user doesn't exist)
        # Second call returns new user id
        cursor.fetchone.side_effect = [
            None,  # get_user_by_telegram_id returns None
            {'id': 'new-uuid'},  # create_user returns new id
            {  # Second get_user_by_telegram_id returns created user
                'id': 'new-uuid',
                'telegram_id': 987654321,
                'username': 'newbie'
            }
        ]
        
        user_data = supabase_service.get_or_create_user(
            telegram_id=987654321,
            username='newbie'
        )
        
        assert user_data is not None
        assert user_data['telegram_id'] == 987654321
        connection.commit.assert_called()
    
    def test_update_last_seen(self, supabase_service, mock_connection):
        """Test updating user's last_seen_at timestamp"""
        connection, cursor = mock_connection
        
        result = supabase_service.update_last_seen(user_id='user-123')
        
        assert result is True
        cursor.execute.assert_called()
        connection.commit.assert_called_once()
    
    def test_get_user_subscription_status(self, supabase_service, mock_connection):
        """Test getting subscription status"""
        _, cursor = mock_connection
        
        cursor.fetchone.return_value = {
            'subscription_status': 'premium',
            'subscription_expires_at': None
        }
        
        status = supabase_service.get_user_subscription_status('user-123')
        
        assert status == 'premium'


class TestSessionOperations:
    """Test dialogue session management"""
    
    def test_create_dialogue_session(self, supabase_service, mock_connection):
        """Test creating new dialogue session"""
        connection, cursor = mock_connection
        
        cursor.fetchone.return_value = {'id': 'session-uuid'}
        
        session_id = supabase_service.create_dialogue_session('user-123')
        
        assert session_id == 'session-uuid'
        cursor.execute.assert_called()
        connection.commit.assert_called_once()
    
    def test_get_or_create_active_session_existing(self, supabase_service, mock_connection):
        """Test getting existing active session"""
        _, cursor = mock_connection
        
        cursor.fetchone.return_value = {
            'id': 'existing-session',
            'updated_at': datetime.now()
        }
        
        session_id = supabase_service.get_or_create_active_session('user-123')
        
        assert session_id == 'existing-session'
    
    def test_get_or_create_active_session_new(self, supabase_service, mock_connection):
        """Test creating new session when none exists"""
        connection, cursor = mock_connection
        
        # First call returns None (no active session)
        # Second call returns new session id
        cursor.fetchone.side_effect = [None, {'id': 'new-session'}]
        
        session_id = supabase_service.get_or_create_active_session('user-123')
        
        assert session_id == 'new-session'
        connection.commit.assert_called()


class TestMessageOperations:
    """Test message storage"""
    
    def test_save_message_success(self, supabase_service, mock_connection):
        """Test saving message successfully"""
        connection, cursor = mock_connection
        
        result = supabase_service.save_message(
            session_id='session-123',
            user_id='user-123',
            query_text='What is IVA?',
            response_text='IVA is Value Added Tax...',
            sources=[{'doc_id': 'doc1', 'score': 0.95}],
            is_relevant=True
        )
        
        assert result is True
        # Should call execute twice: INSERT message + UPDATE session
        assert cursor.execute.call_count == 2
        connection.commit.assert_called_once()
    
    def test_save_message_without_response(self, supabase_service, mock_connection):
        """Test saving query without response yet"""
        connection, cursor = mock_connection
        
        result = supabase_service.save_message(
            session_id='session-123',
            user_id='user-123',
            query_text='Hello bot',
            is_relevant=False
        )
        
        assert result is True
        connection.commit.assert_called_once()
    
    def test_save_message_failure(self, supabase_service, mock_connection):
        """Test message save failure handling"""
        connection, cursor = mock_connection
        
        # Simulate database error
        cursor.execute.side_effect = Exception("Database error")
        
        result = supabase_service.save_message(
            session_id='session-123',
            user_id='user-123',
            query_text='Test query'
        )
        
        assert result is False
        connection.rollback.assert_called_once()


class TestConnectionManagement:
    """Test database connection handling"""
    
    @patch('app.services.supabase_service.psycopg2.connect')
    def test_connect_success(self, mock_connect):
        """Test successful database connection"""
        mock_connect.return_value = Mock()
        
        service = SupabaseService()
        result = service.connect()
        
        assert result is True
        assert service.connection is not None
    
    @patch('app.services.supabase_service.psycopg2.connect')
    def test_connect_failure(self, mock_connect):
        """Test connection failure handling"""
        mock_connect.side_effect = Exception("Connection failed")
        
        service = SupabaseService()
        result = service.connect()
        
        assert result is False
    
    def test_close_connection(self, supabase_service):
        """Test closing database connection"""
        supabase_service.close()
        
        supabase_service.connection.close.assert_called_once()


class TestIntegrationScenarios:
    """Test complete workflows"""
    
    def test_complete_user_message_flow(self, supabase_service, mock_connection):
        """Test full flow: get/create user -> get/create session -> save message"""
        connection, cursor = mock_connection
        
        # Mock responses for complete flow
        cursor.fetchone.side_effect = [
            # get_user_by_telegram_id (new user)
            None,
            # create_user
            {'id': 'user-new'},
            # get_user_by_telegram_id again (returns created user)
            {'id': 'user-new', 'telegram_id': 111222333, 'username': 'testbot'},
            # get_or_create_active_session (no session)
            None,
            # create_dialogue_session
            {'id': 'session-new'}
        ]
        
        # Step 1: Get or create user
        user = supabase_service.get_or_create_user(
            telegram_id=111222333,
            username='testbot'
        )
        assert user['id'] == 'user-new'
        
        # Step 2: Get or create session
        session_id = supabase_service.get_or_create_active_session(user['id'])
        assert session_id == 'session-new'
        
        # Step 3: Save message
        result = supabase_service.save_message(
            session_id=session_id,
            user_id=user['id'],
            query_text='Test query',
            response_text='Test response'
        )
        assert result is True
        
        # Verify commits were called
        assert connection.commit.call_count >= 3

