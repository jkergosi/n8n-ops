-- Migration: Add Git configuration fields to environments table
-- Created: 2025-12-04
-- Description: Moves Git configuration from tenant-level git_configs table to per-environment fields
--              This allows each environment (dev/staging/prod) to have its own Git repository configuration

-- Add Git configuration columns to environments table
ALTER TABLE environments ADD COLUMN IF NOT EXISTS git_repo_url VARCHAR(500);
ALTER TABLE environments ADD COLUMN IF NOT EXISTS git_branch VARCHAR(255) DEFAULT 'main';
ALTER TABLE environments ADD COLUMN IF NOT EXISTS git_pat TEXT;

-- Add index for querying by repo URL (useful for finding environments using a specific repo)
CREATE INDEX IF NOT EXISTS idx_environments_git_repo ON environments(git_repo_url) WHERE git_repo_url IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN environments.git_repo_url IS 'GitHub repository URL for workflow backup/sync (optional, per-environment)';
COMMENT ON COLUMN environments.git_branch IS 'Git branch to use for this environment (defaults to main)';
COMMENT ON COLUMN environments.git_pat IS 'Personal Access Token for GitHub authentication (encrypted, optional)';

-- Note: git_configs table is kept for backward compatibility during migration period
-- Existing git_configs data should be manually migrated to environments as needed
