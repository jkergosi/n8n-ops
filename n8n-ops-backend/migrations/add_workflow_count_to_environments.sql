-- Migration: Add workflow_count column to environments table
-- Created: 2025-12-03
-- Description: Adds a cached workflow count field to track the number of workflows in each environment

-- Add workflow_count column to environments table
ALTER TABLE environments ADD COLUMN IF NOT EXISTS workflow_count INTEGER DEFAULT 0;

-- Add index for performance (useful for filtering/sorting by workflow count)
CREATE INDEX IF NOT EXISTS idx_environments_workflow_count ON environments(workflow_count);

-- Add comment for documentation
COMMENT ON COLUMN environments.workflow_count IS 'Cached count of workflows in this environment, updated when workflows are queried';

-- Initialize existing records with 0 (they will be updated on next query)
UPDATE environments SET workflow_count = 0 WHERE workflow_count IS NULL;
