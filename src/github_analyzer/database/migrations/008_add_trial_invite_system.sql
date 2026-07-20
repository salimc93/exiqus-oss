-- Add trial/invite system fields to users table and create audit log table
-- Trial system fields
ALTER TABLE users ADD COLUMN is_trial BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN trial_plan VARCHAR(50);
ALTER TABLE users ADD COLUMN trial_analyses_limit INTEGER;
ALTER TABLE users ADD COLUMN analyses_consumed INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN invite_token VARCHAR(100) UNIQUE;
ALTER TABLE users ADD COLUMN invite_token_expires TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN has_completed_onboarding BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN trial_value VARCHAR(50);

-- Create index for invite token lookups
CREATE INDEX idx_users_invite_token ON users(invite_token) WHERE invite_token IS NOT NULL;

-- Create audit log table for tracking administrative actions
CREATE TABLE audit_logs (
    log_id VARCHAR(50) PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    admin_id VARCHAR(50) REFERENCES users(user_id),
    target_user_id VARCHAR(50) REFERENCES users(user_id),
    target_email VARCHAR(255),
    action_metadata TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for audit log queries
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_admin_id ON audit_logs(admin_id);
CREATE INDEX idx_audit_logs_target_user_id ON audit_logs(target_user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);