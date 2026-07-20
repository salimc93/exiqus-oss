-- Migration 007: Add billing infrastructure tables
-- This migration creates tables for Stripe integration, invoices, payments, and usage tracking

-- Create invoices table for billing history
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    stripe_invoice_id VARCHAR(100) NOT NULL UNIQUE,
    stripe_customer_id VARCHAR(100) NOT NULL,
    amount_due INTEGER NOT NULL,
    amount_paid INTEGER DEFAULT 0 NOT NULL,
    currency VARCHAR(3) DEFAULT 'usd' NOT NULL,
    status VARCHAR(20) NOT NULL,
    billing_period_start TIMESTAMPTZ NOT NULL,
    billing_period_end TIMESTAMPTZ NOT NULL,
    description TEXT,
    invoice_url VARCHAR(500),
    invoice_pdf VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    due_date TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Create indexes for invoice queries
CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_stripe_invoice_id ON invoices(stripe_invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_billing_period_start ON invoices(billing_period_start);
CREATE INDEX IF NOT EXISTS idx_invoices_billing_period_end ON invoices(billing_period_end);
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at);
CREATE INDEX IF NOT EXISTS idx_invoices_due_date ON invoices(due_date);
CREATE INDEX IF NOT EXISTS idx_invoices_paid_at ON invoices(paid_at);

-- Create payments table for payment tracking
CREATE TABLE IF NOT EXISTS payments (
    payment_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    invoice_id VARCHAR(50),
    stripe_payment_intent_id VARCHAR(100) NOT NULL UNIQUE,
    stripe_customer_id VARCHAR(100) NOT NULL,
    amount INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'usd' NOT NULL,
    status VARCHAR(20) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    payment_method_details TEXT,
    failure_code VARCHAR(50),
    failure_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    processed_at TIMESTAMPTZ,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE SET NULL
);

-- Create indexes for payment queries
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payments_stripe_payment_intent_id ON payments(stripe_payment_intent_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at);
CREATE INDEX IF NOT EXISTS idx_payments_processed_at ON payments(processed_at);

-- Create billing usage records table for metered billing
CREATE TABLE IF NOT EXISTS billing_usage_records (
    record_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    usage_type VARCHAR(50) NOT NULL,
    usage_count INTEGER DEFAULT 1 NOT NULL,
    billing_period VARCHAR(10) NOT NULL,
    unit_cost VARCHAR(20) DEFAULT '0.00' NOT NULL,
    total_cost VARCHAR(20) DEFAULT '0.00' NOT NULL,
    request_metadata TEXT,
    stripe_usage_record_id VARCHAR(100),
    reported_to_stripe BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    reported_at TIMESTAMPTZ,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Create indexes for billing usage records
CREATE INDEX IF NOT EXISTS idx_billing_usage_records_user_id ON billing_usage_records(user_id);
CREATE INDEX IF NOT EXISTS idx_billing_usage_records_usage_type ON billing_usage_records(usage_type);
CREATE INDEX IF NOT EXISTS idx_billing_usage_records_billing_period ON billing_usage_records(billing_period);
CREATE INDEX IF NOT EXISTS idx_billing_usage_records_stripe_usage_record_id ON billing_usage_records(stripe_usage_record_id);
CREATE INDEX IF NOT EXISTS idx_billing_usage_records_created_at ON billing_usage_records(created_at);
CREATE INDEX IF NOT EXISTS idx_billing_usage_records_reported_at ON billing_usage_records(reported_at);

-- Create composite index for usage period queries
CREATE INDEX IF NOT EXISTS idx_billing_usage_user_period ON billing_usage_records(user_id, billing_period);

-- Create webhook events table for idempotency and audit trail
CREATE TABLE IF NOT EXISTS webhook_events (
    event_id VARCHAR(100) PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    event_data TEXT NOT NULL,
    processed BOOLEAN DEFAULT FALSE NOT NULL,
    processing_attempts INTEGER DEFAULT 0 NOT NULL,
    processing_result TEXT,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    processed_at TIMESTAMPTZ,
    last_attempt_at TIMESTAMPTZ
);

-- Create indexes for webhook events
CREATE INDEX IF NOT EXISTS idx_webhook_events_event_type ON webhook_events(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_events_created_at ON webhook_events(created_at);
CREATE INDEX IF NOT EXISTS idx_webhook_events_processed_at ON webhook_events(processed_at);
CREATE INDEX IF NOT EXISTS idx_webhook_events_last_attempt_at ON webhook_events(last_attempt_at);

-- Create composite index for unprocessed events
CREATE INDEX IF NOT EXISTS idx_webhook_events_unprocessed ON webhook_events(processed, created_at) WHERE processed = FALSE;

-- Update users table to add Stripe fields if they don't exist
-- (These fields may already exist from previous migrations)
DO $$
BEGIN
    -- Add stripe_customer_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'stripe_customer_id'
    ) THEN
        ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(100);
    END IF;
    
    -- Add stripe_subscription_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'stripe_subscription_id'
    ) THEN
        ALTER TABLE users ADD COLUMN stripe_subscription_id VARCHAR(100);
    END IF;
END $$;

-- Create indexes for Stripe fields on users table
CREATE INDEX IF NOT EXISTS idx_users_stripe_customer_id ON users(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_users_stripe_subscription_id ON users(stripe_subscription_id);

-- Create function to generate billing record IDs
CREATE OR REPLACE FUNCTION generate_billing_id(prefix TEXT) RETURNS TEXT AS $$
DECLARE
    timestamp_part TEXT;
    random_part TEXT;
BEGIN
    -- Get current timestamp in microseconds
    timestamp_part := EXTRACT(EPOCH FROM NOW() * 1000000)::BIGINT::TEXT;
    
    -- Generate random 6-character suffix
    random_part := SUBSTR(MD5(RANDOM()::TEXT), 1, 6);
    
    -- Combine prefix, timestamp, and random part
    RETURN prefix || '_' || timestamp_part || '_' || random_part;
END;
$$ LANGUAGE plpgsql;

-- Create function to get current billing period
CREATE OR REPLACE FUNCTION get_current_billing_period() RETURNS TEXT AS $$
BEGIN
    RETURN TO_CHAR(NOW(), 'YYYY-MM');
END;
$$ LANGUAGE plpgsql;

-- Create function to update usage quotas on subscription changes
CREATE OR REPLACE FUNCTION update_usage_quota_on_subscription_change() RETURNS TRIGGER AS $$
BEGIN
    -- Reset usage when subscription plan changes
    IF OLD.subscription_plan IS DISTINCT FROM NEW.subscription_plan THEN
        -- Reset usage consumed to 0 on plan change
        NEW.usage_consumed := 0;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for usage quota updates
DROP TRIGGER IF EXISTS trigger_update_usage_quota ON users;
CREATE TRIGGER trigger_update_usage_quota
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_usage_quota_on_subscription_change();

-- Create view for billing dashboard
CREATE OR REPLACE VIEW billing_dashboard AS
SELECT 
    u.user_id,
    u.email,
    u.full_name,
    u.company,
    u.subscription_plan,
    u.subscription_status,
    u.usage_quota,
    u.usage_consumed,
    u.stripe_customer_id,
    u.stripe_subscription_id,
    u.subscription_start_date,
    u.subscription_end_date,
    -- Calculate usage percentage
    CASE 
        WHEN u.usage_quota > 0 THEN ROUND((u.usage_consumed::DECIMAL / u.usage_quota) * 100, 2)
        ELSE 0
    END as usage_percentage,
    -- Get latest invoice
    (SELECT i.invoice_id FROM invoices i WHERE i.user_id = u.user_id ORDER BY i.created_at DESC LIMIT 1) as latest_invoice_id,
    (SELECT i.status FROM invoices i WHERE i.user_id = u.user_id ORDER BY i.created_at DESC LIMIT 1) as latest_invoice_status,
    -- Get total revenue from this user
    (SELECT COALESCE(SUM(i.amount_paid), 0) FROM invoices i WHERE i.user_id = u.user_id) as total_revenue_cents,
    -- Get payment failure count
    (SELECT COUNT(*) FROM payments p WHERE p.user_id = u.user_id AND p.status = 'failed') as failed_payment_count
FROM users u
WHERE u.subscription_plan != 'free' OR u.stripe_customer_id IS NOT NULL;

-- Add comments for documentation
COMMENT ON TABLE invoices IS 'Billing invoice records synced with Stripe for payment tracking';
COMMENT ON TABLE payments IS 'Payment attempt records for both successful and failed transactions';
COMMENT ON TABLE billing_usage_records IS 'Usage tracking for metered billing and quota enforcement';
COMMENT ON TABLE webhook_events IS 'Stripe webhook event tracking for idempotency and audit trails';
COMMENT ON VIEW billing_dashboard IS 'Consolidated billing view for admin dashboard and analytics';

-- Insert initial webhook event types for reference
INSERT INTO webhook_events (event_id, event_type, event_data, processed, processing_result, created_at)
VALUES 
    ('init_customer_subscription_created', 'customer.subscription.created', '{"type":"reference"}', TRUE, 'Reference event for documentation', NOW()),
    ('init_customer_subscription_updated', 'customer.subscription.updated', '{"type":"reference"}', TRUE, 'Reference event for documentation', NOW()),
    ('init_customer_subscription_deleted', 'customer.subscription.deleted', '{"type":"reference"}', TRUE, 'Reference event for documentation', NOW()),
    ('init_invoice_payment_succeeded', 'invoice.payment_succeeded', '{"type":"reference"}', TRUE, 'Reference event for documentation', NOW()),
    ('init_invoice_payment_failed', 'invoice.payment_failed', '{"type":"reference"}', TRUE, 'Reference event for documentation', NOW())
ON CONFLICT (event_id) DO NOTHING;