-- Migration: Add salt column to api_keys table
-- Description: Add a separate salt column for improved security in API key hashing
-- Date: 2025-01-06

-- Add salt column to api_keys table
ALTER TABLE api_keys ADD COLUMN salt VARCHAR(32) NOT NULL DEFAULT 'temporary_salt';

-- Remove the default constraint after adding the column
-- This is a two-step process to handle existing rows
ALTER TABLE api_keys ALTER COLUMN salt DROP DEFAULT;

-- Create index on salt for faster lookups (optional, but can help with verification)
CREATE INDEX idx_api_keys_salt ON api_keys(salt);