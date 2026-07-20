-- Add pr_count column to pr_analysis_records table
-- This column tracks the number of PRs analyzed in each request

ALTER TABLE pr_analysis_records
ADD COLUMN IF NOT EXISTS pr_count INTEGER NOT NULL DEFAULT 0;

-- Add comment for documentation
COMMENT ON COLUMN pr_analysis_records.pr_count IS 'Number of PRs analyzed in this request';
