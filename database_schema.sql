-- ============================================================
-- CAAA Scraper Database Schema
-- PostgreSQL 14+
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABLE 1: searches
-- Stores user search queries and their parameters
-- ============================================================

CREATE TABLE searches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Search parameters (stored as JSONB for flexibility)
    search_params JSONB NOT NULL,
    
    -- Quick access fields (denormalized for performance)
    keyword TEXT,
    listserv VARCHAR(50),
    date_from DATE,
    date_to DATE,
    
    -- Search metadata
    total_messages_found INTEGER DEFAULT 0,
    total_relevant_found INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Indexes
    CONSTRAINT searches_status_check CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

CREATE INDEX idx_searches_created_at ON searches(created_at DESC);
CREATE INDEX idx_searches_keyword ON searches USING gin(to_tsvector('english', keyword));
CREATE INDEX idx_searches_status ON searches(status);


-- ============================================================
-- TABLE 2: messages
-- Stores scraped message metadata and content
-- ============================================================

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- CAAA message identifier (unique per message)
    caaa_message_id VARCHAR(50) UNIQUE NOT NULL,
    
    -- Message metadata
    post_date DATE NOT NULL,
    from_name TEXT,
    from_email TEXT,
    listserv VARCHAR(50) NOT NULL,
    subject TEXT NOT NULL,
    
    -- Message content
    body TEXT,
    body_length INTEGER,
    has_attachment BOOLEAN DEFAULT FALSE,
    
    -- Scraping metadata
    fetched_at TIMESTAMP DEFAULT NOW(),
    fetch_url TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_messages_caaa_id ON messages(caaa_message_id);
CREATE INDEX idx_messages_post_date ON messages(post_date DESC);
CREATE INDEX idx_messages_listserv ON messages(listserv);
CREATE INDEX idx_messages_subject ON messages USING gin(to_tsvector('english', subject));
CREATE INDEX idx_messages_body ON messages USING gin(to_tsvector('english', body));


-- ============================================================
-- TABLE 3: analyses
-- Stores AI relevance analysis for message + search combinations
-- ============================================================

CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Foreign keys
    search_id UUID NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    
    -- AI analysis results
    is_relevant BOOLEAN NOT NULL,
    confidence DECIMAL(3,2) CHECK (confidence >= 0 AND confidence <= 1), -- 0.00 to 1.00
    ai_reasoning TEXT,
    
    -- AI metadata
    ai_model VARCHAR(50), -- e.g., 'gpt-4', 'gpt-3.5-turbo'
    ai_tokens_used INTEGER,
    ai_cost_usd DECIMAL(10,6),
    
    -- User feedback (for improving AI)
    user_feedback VARCHAR(20), -- null, 'helpful', 'not_helpful'
    user_feedback_at TIMESTAMP,
    
    -- Timestamps
    analyzed_at TIMESTAMP DEFAULT NOW(),
    
    -- Unique constraint: one analysis per search + message combo
    CONSTRAINT unique_search_message UNIQUE (search_id, message_id),
    CONSTRAINT analyses_user_feedback_check CHECK (user_feedback IN ('helpful', 'not_helpful'))
);

CREATE INDEX idx_analyses_search_id ON analyses(search_id);
CREATE INDEX idx_analyses_message_id ON analyses(message_id);
CREATE INDEX idx_analyses_relevant ON analyses(is_relevant);
CREATE INDEX idx_analyses_confidence ON analyses(confidence DESC);


-- ============================================================
-- TABLE 4: search_results (junction table)
-- Links searches to messages found for that search
-- ============================================================

CREATE TABLE search_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Foreign keys
    search_id UUID NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    
    -- Result metadata
    result_position INTEGER, -- Position in search results (1, 2, 3...)
    result_page INTEGER, -- Which page of results (1-10)
    
    -- Timestamps
    found_at TIMESTAMP DEFAULT NOW(),
    
    -- Unique constraint: one entry per search + message combo
    CONSTRAINT unique_search_result UNIQUE (search_id, message_id)
);

CREATE INDEX idx_search_results_search_id ON search_results(search_id);
CREATE INDEX idx_search_results_message_id ON search_results(message_id);


-- ============================================================
-- VIEW: relevant_results
-- Convenient view for getting relevant messages for a search
-- ============================================================

CREATE VIEW relevant_results AS
SELECT 
    s.id as search_id,
    s.keyword,
    s.created_at as search_date,
    m.caaa_message_id,
    m.post_date,
    m.from_name,
    m.subject,
    m.body,
    a.is_relevant,
    a.confidence,
    a.ai_reasoning,
    a.user_feedback,
    sr.result_position
FROM searches s
JOIN search_results sr ON s.id = sr.search_id
JOIN messages m ON sr.message_id = m.id
JOIN analyses a ON s.id = a.search_id AND m.id = a.message_id
WHERE a.is_relevant = TRUE
ORDER BY s.created_at DESC, sr.result_position ASC;


-- ============================================================
-- FUNCTION: Update updated_at timestamp
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_messages_updated_at BEFORE UPDATE ON messages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- Sample Queries (for reference)
-- ============================================================

-- Get all relevant messages for a search
-- SELECT * FROM relevant_results WHERE search_id = 'YOUR-UUID';

-- Get message deduplication check
-- SELECT COUNT(*) FROM messages WHERE caaa_message_id = '21783907';

-- Get search stats
-- SELECT 
--     s.keyword,
--     s.total_messages_found,
--     COUNT(DISTINCT a.id) FILTER (WHERE a.is_relevant = TRUE) as relevant_count,
--     AVG(a.confidence) FILTER (WHERE a.is_relevant = TRUE) as avg_confidence
-- FROM searches s
-- LEFT JOIN analyses a ON s.id = a.search_id
-- GROUP BY s.id, s.keyword, s.total_messages_found;

