-- Fix primary key column name in users table
-- The users table was created with 'id' but the model expects 'user_id'

-- Create new users table with correct column name
CREATE TABLE users_new (
    user_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT,
    full_name VARCHAR(200),
    company VARCHAR(200),
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    is_admin BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    last_login TIMESTAMP WITH TIME ZONE,
    usage_quota INTEGER NOT NULL DEFAULT 100,
    usage_consumed INTEGER NOT NULL DEFAULT 0,
    user_role VARCHAR(20) DEFAULT 'user' NOT NULL,
    subscription_plan VARCHAR(20) DEFAULT 'free' NOT NULL,
    subscription_status VARCHAR(20) DEFAULT 'active' NOT NULL,
    stripe_customer_id VARCHAR(100),
    stripe_subscription_id VARCHAR(100),
    subscription_start_date TIMESTAMP WITH TIME ZONE,
    subscription_end_date TIMESTAMP WITH TIME ZONE,
    trial_end_date TIMESTAMP WITH TIME ZONE,
    company_size VARCHAR(50),
    industry VARCHAR(100),
    use_case TEXT,
    notification_preferences TEXT
);

-- Copy data from old table to new table
-- First, check if users table exists and copy basic columns
INSERT INTO users_new (
    user_id, email, password_hash, full_name, company,
    is_active, is_verified, is_admin, created_at, updated_at,
    last_login, usage_quota, usage_consumed
)
SELECT 
    CASE 
        WHEN user_id IS NOT NULL THEN user_id
        ELSE CAST(id AS VARCHAR(50))
    END as user_id,
    email,
    COALESCE(password_hash, ''),
    COALESCE(full_name, ''),
    company,
    COALESCE(is_active, true),
    COALESCE(is_verified, false),
    COALESCE(is_admin, false),
    COALESCE(created_at, CURRENT_TIMESTAMP),
    COALESCE(updated_at, CURRENT_TIMESTAMP),
    last_login,
    COALESCE(usage_quota, 100),
    COALESCE(usage_consumed, 0)
FROM users
WHERE EXISTS (SELECT 1 FROM users);

-- Update subscription columns if they exist in the old table
UPDATE users_new 
SET 
    user_role = COALESCE(old_users.user_role, 'user'),
    subscription_plan = COALESCE(old_users.subscription_plan, 'free'),
    subscription_status = COALESCE(old_users.subscription_status, 'active'),
    stripe_customer_id = old_users.stripe_customer_id,
    stripe_subscription_id = old_users.stripe_subscription_id,
    subscription_start_date = old_users.subscription_start_date,
    subscription_end_date = old_users.subscription_end_date,
    trial_end_date = old_users.trial_end_date,
    company_size = old_users.company_size,
    industry = old_users.industry,
    use_case = old_users.use_case,
    notification_preferences = old_users.notification_preferences
FROM users as old_users 
WHERE users_new.user_id = COALESCE(old_users.user_id, CAST(old_users.id AS VARCHAR(50)))
AND EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'users' AND column_name = 'user_role'
);

-- Drop old table
DROP TABLE users;

-- Rename new table to users
ALTER TABLE users_new RENAME TO users;

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);