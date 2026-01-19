CREATE TABLE IF NOT EXISTS readiness_assessments (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    email VARCHAR(255),
    answers JSONB NOT NULL,
    overall_score INTEGER NOT NULL,
    category_scores JSONB NOT NULL,
    readiness_level VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS readiness_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(100) NOT NULL,
    pattern_data JSONB NOT NULL,
    frequency INTEGER DEFAULT 1,
    avg_score DECIMAL(5,2),
    last_updated TIMESTAMP DEFAULT NOW(),
    UNIQUE(pattern_type, pattern_data)
);

CREATE TABLE IF NOT EXISTS readiness_insights (
    id SERIAL PRIMARY KEY,
    insight_type VARCHAR(50),
    insight_text TEXT NOT NULL,
    confidence DECIMAL(3,2),
    supporting_data JSONB,
    generated_at TIMESTAMP DEFAULT NOW()
);

-- Sessions table for Nuru handoff
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    assessment_id INTEGER REFERENCES readiness_assessments(id),
    user_context JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '24 hours',
    accessed_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_readiness_created ON readiness_assessments(created_at);
CREATE INDEX IF NOT EXISTS idx_readiness_industry ON readiness_assessments(industry);
CREATE INDEX IF NOT EXISTS idx_readiness_score ON readiness_assessments(overall_score);
CREATE INDEX IF NOT EXISTS idx_patterns_type ON readiness_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_insights_type ON readiness_insights(insight_type);
CREATE INDEX IF NOT EXISTS idx_insights_date ON readiness_insights(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_expires_at ON sessions(expires_at);