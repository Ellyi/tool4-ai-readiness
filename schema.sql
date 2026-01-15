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

CREATE INDEX IF NOT EXISTS idx_readiness_created ON readiness_assessments(created_at);
CREATE INDEX IF NOT EXISTS idx_readiness_industry ON readiness_assessments(industry);
CREATE INDEX IF NOT EXISTS idx_readiness_score ON readiness_assessments(overall_score);
CREATE INDEX IF NOT EXISTS idx_patterns_type ON readiness_patterns(pattern_type);