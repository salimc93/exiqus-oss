-- PostgreSQL initialization script for GitHub Analyzer
-- This script sets up the database with proper permissions and extensions

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
SET timezone = 'UTC';

-- Create indexes for better performance
-- Note: Tables will be created by migrations, this just sets up the environment

-- Grant necessary permissions to the application user
GRANT ALL PRIVILEGES ON DATABASE github_analyzer TO github_analyzer;
GRANT ALL PRIVILEGES ON SCHEMA public TO github_analyzer;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO github_analyzer;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO github_analyzer;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO github_analyzer;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO github_analyzer;