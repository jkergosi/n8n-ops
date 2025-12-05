-- Migration: Add last_backup column to environments table
-- Created: 2025-12-04
-- Description: Adds a timestamp column to track when the last successful backup was performed
--              This allows incremental backups by only syncing workflows updated since last backup

-- Add last_backup column to environments table
ALTER TABLE environments ADD COLUMN IF NOT EXISTS last_backup TIMESTAMP WITH TIME ZONE;

-- Add index for querying by last backup time
CREATE INDEX IF NOT EXISTS idx_environments_last_backup ON environments(last_backup) WHERE last_backup IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN environments.last_backup IS 'Timestamp of the last successful workflow backup to GitHub';
