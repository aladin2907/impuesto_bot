-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. users: Core user profiles with Telegram data
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL, -- Telegram user ID (main identifier)
    username TEXT, -- Telegram username
    first_name TEXT,
    last_name TEXT,
    phone TEXT, -- Phone number if provided
    subscription_status TEXT NOT NULL DEFAULT 'free', -- e.g., 'free', 'premium'
    subscription_expires_at TIMESTAMPTZ,
    role TEXT NOT NULL DEFAULT 'user', -- e.g., 'user', 'admin'
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB -- Additional user data
);
COMMENT ON TABLE users IS 'User profiles with Telegram identity and subscription data.';
COMMENT ON COLUMN users.telegram_id IS 'Telegram user ID - main identifier for quick lookups.';
COMMENT ON COLUMN users.last_seen_at IS 'Timestamp of the last interaction from the user.';

-- Add index for fast telegram_id lookups
CREATE INDEX idx_users_telegram_id ON users(telegram_id);


-- 3. dialogue_sessions: Groups conversations for context and summarization
CREATE TABLE dialogue_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);


-- 4. messages: Stores every individual message for history and analysis
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES dialogue_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    response_text TEXT,
    sources JSONB, -- Documents/chunks from Elastic used for the response
    is_relevant BOOLEAN NOT NULL DEFAULT true, -- Flag from the pre-filtering logic
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE messages IS 'Records every incoming query and outgoing response.';
COMMENT ON COLUMN messages.is_relevant IS 'Determined by a pre-processing filter to avoid running expensive logic on chit-chat.';


-- 5. user_tax_profile: Stores personal data for tax calculations
CREATE TABLE user_tax_profile (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE, -- One profile per user
    profile_data JSONB, -- Flexible JSON for various tax-related fields
    updated_at TIMESTAMPTZ
);
COMMENT ON TABLE user_tax_profile IS 'Stores sensitive, user-provided data for personalized tax calculations.';


-- 6. documents: Metadata for ingested source documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_url TEXT, -- URL if from the web
    file_name TEXT, -- Original file name
    document_type TEXT, -- e.g., 'tax_code', 'news_article', 'tg_discussion'
    status TEXT NOT NULL DEFAULT 'pending', -- e.g., 'pending', 'processing', 'completed', 'failed'
    last_processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE documents IS 'Metadata for source documents that are processed and indexed into Elasticsearch.';


-- 7. tax_deadlines: Structured tax calendar data for reminders
CREATE TABLE tax_deadlines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deadline_date DATE NOT NULL,
    tax_type TEXT NOT NULL, -- e.g., 'IRPF', 'IVA', 'Sociedades'
    description TEXT,
    applies_to TEXT[], -- e.g., ['autónomos', 'empresas']
    quarter TEXT, -- e.g., 'Q1', 'Q2', 'Q3', 'Q4'
    year INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE tax_deadlines IS 'Structured tax calendar data for deadline queries and reminders.';

CREATE INDEX idx_tax_deadlines_date ON tax_deadlines(deadline_date);
CREATE INDEX idx_tax_deadlines_type ON tax_deadlines(tax_type);


-- 8. sent_reminders: Track sent calendar reminders to avoid duplicates
CREATE TABLE sent_reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deadline_id UUID REFERENCES tax_deadlines(id) ON DELETE CASCADE,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    channel_type TEXT, -- 'telegram', 'whatsapp'
    channel_id TEXT, -- group_id or user_id
    message_id TEXT -- for tracking/deletion
);
COMMENT ON TABLE sent_reminders IS 'Tracks sent calendar reminders to avoid duplicate notifications.';

CREATE INDEX idx_sent_reminders_deadline ON sent_reminders(deadline_id);
CREATE INDEX idx_sent_reminders_sent_at ON sent_reminders(sent_at);
