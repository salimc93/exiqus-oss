-- Migration 009: API Key Monetization - Phase 1
-- Add quota tracking fields to api_keys and usage_records tables

-- Add quota fields to api_keys table
ALTER TABLE api_keys
ADD COLUMN monthly_quota INTEGER NOT NULL DEFAULT 0,
ADD COLUMN monthly_usage INTEGER NOT NULL DEFAULT 0,
ADD COLUMN last_quota_reset TIMESTAMP WITH TIME ZONE;

-- Add API tracking fields to usage_records table
ALTER TABLE usage_records
ADD COLUMN api_key_id VARCHAR(50) REFERENCES api_keys(key_id),
ADD COLUMN is_api_request BOOLEAN DEFAULT FALSE;

-- Create index for API key usage queries
CREATE INDEX idx_usage_records_api_key_id ON usage_records(api_key_id);
CREATE INDEX idx_usage_records_is_api_request ON usage_records(is_api_request);

-- Create api_usage_overages table for billing
CREATE TABLE api_usage_overages (
    overage_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id),
    api_key_id VARCHAR(50) NOT NULL REFERENCES api_keys(key_id),
    billing_month DATE NOT NULL,
    overage_count INTEGER NOT NULL,
    amount_charged VARCHAR(20) NOT NULL,
    stripe_invoice_id VARCHAR(255),
    payment_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(api_key_id, billing_month)
);

-- Create indexes for overage queries
CREATE INDEX idx_api_usage_overages_user_id ON api_usage_overages(user_id);
CREATE INDEX idx_api_usage_overages_billing_month ON api_usage_overages(billing_month);
CREATE INDEX idx_api_usage_overages_payment_status ON api_usage_overages(payment_status);