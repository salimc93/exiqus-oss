-- Add user management and admin features to users table
-- This migration adds subscription awareness, user roles, and admin analytics

-- Add new columns to users table for subscription management
ALTER TABLE users ADD COLUMN user_role VARCHAR(20) DEFAULT 'user' NOT NULL;
ALTER TABLE users ADD COLUMN subscription_plan VARCHAR(20) DEFAULT 'free' NOT NULL;
ALTER TABLE users ADD COLUMN subscription_status VARCHAR(20) DEFAULT 'active' NOT NULL;
ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(100);
ALTER TABLE users ADD COLUMN stripe_subscription_id VARCHAR(100);
ALTER TABLE users ADD COLUMN subscription_start_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN subscription_end_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN trial_end_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN company_size VARCHAR(50);
ALTER TABLE users ADD COLUMN industry VARCHAR(100);
ALTER TABLE users ADD COLUMN use_case TEXT;
ALTER TABLE users ADD COLUMN notification_preferences TEXT;