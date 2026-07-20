-- Migration: Add key_prefix column to api_keys table
-- Description: Add indexed prefix column for O(1) API key lookups, fixing performance vulnerability
-- Date: 2025-01-06

-- Add key_prefix column to api_keys table
ALTER TABLE api_keys ADD COLUMN key_prefix VARCHAR(12) NOT NULL DEFAULT 'legacy';

-- Remove the default constraint after adding the column
ALTER TABLE api_keys ALTER COLUMN key_prefix DROP DEFAULT;

-- Create unique index on key_prefix for O(1) lookups
CREATE UNIQUE INDEX idx_api_keys_key_prefix ON api_keys(key_prefix);

-- Note: Existing keys will need to be migrated to have unique prefixes
-- This can be done in a separate data migration script