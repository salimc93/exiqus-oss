-- Create usage records table for tracking API usage
CREATE TABLE usage_records (
    record_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    endpoint VARCHAR(100) NOT NULL,
    method VARCHAR(10) NOT NULL,
    repository_url TEXT,
    tokens_consumed INTEGER NOT NULL DEFAULT 0,
    cost_incurred VARCHAR(20) NOT NULL DEFAULT '0.00',
    response_time_ms INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_usage_records_user_id ON usage_records(user_id);
CREATE INDEX idx_usage_records_created_at ON usage_records(created_at);
CREATE INDEX idx_usage_records_endpoint ON usage_records(endpoint);
