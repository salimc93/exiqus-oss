-- Add batch_id column to analysis_results table for batch tracking
ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS batch_id VARCHAR(36);

-- Create index for efficient batch queries
CREATE INDEX IF NOT EXISTS idx_analysis_results_batch_id ON analysis_results(batch_id);