-- ============================================================
-- Migration: Simplify users schema
-- Remove user_channels table, move telegram_id directly to users
-- ============================================================

BEGIN;

-- 1. Check if we have any data to migrate
DO $$
DECLARE
    user_count INTEGER;
    channel_count INTEGER;
    table_exists BOOLEAN;
BEGIN
    -- Check if user_channels table exists
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'user_channels'
    ) INTO table_exists;
    
    SELECT COUNT(*) INTO user_count FROM users;
    
    IF table_exists THEN
        SELECT COUNT(*) INTO channel_count FROM user_channels;
        RAISE NOTICE 'Current state:';
        RAISE NOTICE '  Users: %', user_count;
        RAISE NOTICE '  User channels: %', channel_count;
    ELSE
        RAISE NOTICE 'Table user_channels does not exist - will create new structure';
        RAISE NOTICE '  Users: %', user_count;
    END IF;
END $$;

-- 2. Add new columns to users table
ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS telegram_id BIGINT,
    ADD COLUMN IF NOT EXISTS username TEXT,
    ADD COLUMN IF NOT EXISTS first_name TEXT,
    ADD COLUMN IF NOT EXISTS last_name TEXT,
    ADD COLUMN IF NOT EXISTS phone TEXT,
    ADD COLUMN IF NOT EXISTS metadata JSONB;

-- 3. Migrate data from user_channels to users (if table exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'user_channels'
    ) THEN
        UPDATE users u
        SET 
            telegram_id = CAST(uc.channel_user_id AS BIGINT),
            username = uc.metadata->>'username',
            first_name = uc.metadata->>'first_name',
            last_name = uc.metadata->>'last_name',
            phone = uc.metadata->>'phone',
            metadata = uc.metadata
        FROM user_channels uc
        WHERE u.id = uc.user_id 
            AND uc.channel_type = 'telegram';
        
        RAISE NOTICE 'Data migrated from user_channels to users';
    ELSE
        RAISE NOTICE 'No user_channels table to migrate from - skipping data migration';
    END IF;
END $$;

-- 4. Make telegram_id UNIQUE (but not NOT NULL if no data was migrated)
DO $$
BEGIN
    -- Add unique constraint if not exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'users_telegram_id_unique'
    ) THEN
        -- Only set NOT NULL if we have data with telegram_id
        DECLARE
            has_telegram_data BOOLEAN;
        BEGIN
            SELECT EXISTS(SELECT 1 FROM users WHERE telegram_id IS NOT NULL) INTO has_telegram_data;
            
            IF has_telegram_data THEN
                ALTER TABLE users ALTER COLUMN telegram_id SET NOT NULL;
                RAISE NOTICE 'Set telegram_id as NOT NULL (data exists)';
            ELSE
                RAISE NOTICE 'telegram_id left as nullable (no data yet)';
            END IF;
        END;
        
        ALTER TABLE users ADD CONSTRAINT users_telegram_id_unique UNIQUE (telegram_id);
        RAISE NOTICE 'Added unique constraint on telegram_id';
    END IF;
END $$;

-- 5. Add index for fast lookups
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- 6. Update messages table - replace channel_id with user_id reference
DO $$
DECLARE
    has_channel_id BOOLEAN;
    has_user_id BOOLEAN;
BEGIN
    -- Check if channel_id column exists
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'messages' AND column_name = 'channel_id'
    ) INTO has_channel_id;
    
    -- Check if user_id column exists
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'messages' AND column_name = 'user_id'
    ) INTO has_user_id;
    
    IF has_channel_id AND NOT has_user_id THEN
        -- Old schema: migrate from channel_id to user_id
        ALTER TABLE messages ADD COLUMN user_id_new UUID;
        
        IF EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'user_channels'
        ) THEN
            UPDATE messages m
            SET user_id_new = uc.user_id
            FROM user_channels uc
            WHERE m.channel_id = uc.id;
        END IF;
        
        ALTER TABLE messages DROP COLUMN channel_id CASCADE;
        ALTER TABLE messages RENAME COLUMN user_id_new TO user_id;
        
        ALTER TABLE messages
            ADD CONSTRAINT messages_user_id_fkey 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        
        -- Only set NOT NULL if we have data
        DECLARE
            has_messages BOOLEAN;
        BEGIN
            SELECT EXISTS(SELECT 1 FROM messages WHERE user_id IS NOT NULL) INTO has_messages;
            IF has_messages THEN
                ALTER TABLE messages ALTER COLUMN user_id SET NOT NULL;
            END IF;
        END;
        
        RAISE NOTICE 'Messages table updated: channel_id -> user_id';
        
    ELSIF NOT has_user_id THEN
        -- No columns exist: create user_id from scratch
        ALTER TABLE messages ADD COLUMN user_id UUID;
        ALTER TABLE messages
            ADD CONSTRAINT messages_user_id_fkey 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Added user_id column to messages table';
    ELSE
        RAISE NOTICE 'Messages table already has user_id column - skipping';
    END IF;
END $$;

-- 7. Drop user_channels table
DROP TABLE IF EXISTS user_channels CASCADE;

-- 8. Add comments
COMMENT ON COLUMN users.telegram_id IS 'Telegram user ID - main identifier for quick lookups.';
COMMENT ON COLUMN users.username IS 'Telegram username';
COMMENT ON COLUMN users.first_name IS 'User first name from Telegram';
COMMENT ON COLUMN users.last_name IS 'User last name from Telegram';
COMMENT ON COLUMN users.phone IS 'Phone number if provided';
COMMENT ON COLUMN users.metadata IS 'Additional user data in JSON format';

-- 9. Final check
DO $$
DECLARE
    user_count INTEGER;
    message_count INTEGER;
    users_with_telegram INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT COUNT(*) INTO message_count FROM messages;
    SELECT COUNT(*) INTO users_with_telegram FROM users WHERE telegram_id IS NOT NULL;
    
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE '  Users: %', user_count;
    RAISE NOTICE '  Users with telegram_id: %', users_with_telegram;
    RAISE NOTICE '  Messages: %', message_count;
    RAISE NOTICE '==============================================';
END $$;

COMMIT;

-- Print success message
SELECT 'Migration completed! Old user_channels table removed, telegram_id moved to users table.' AS status;

