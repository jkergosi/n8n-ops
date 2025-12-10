-- Migration: Add is_production and allow_upload flags, make n8n_type optional
-- Date: 2024-12-XX
-- Description: 
--   - Makes n8n_type nullable (optional metadata for display/sorting)
--   - Adds is_production boolean flag for business logic (replaces type === 'production' checks)
--   - Adds allow_upload boolean flag for feature flags (replaces type === 'dev' checks)

-- Make n8n_type nullable (it's now optional metadata, not required)
ALTER TABLE environments ALTER COLUMN n8n_type DROP NOT NULL;

-- Add is_production flag (default false for existing records)
ALTER TABLE environments ADD COLUMN IF NOT EXISTS is_production BOOLEAN NOT NULL DEFAULT false;

-- Add allow_upload flag (default true for existing 'dev' environments, false otherwise)
ALTER TABLE environments ADD COLUMN IF NOT EXISTS allow_upload BOOLEAN NOT NULL DEFAULT false;

-- Set defaults for existing records based on current n8n_type
UPDATE environments 
SET is_production = (n8n_type = 'production'),
    allow_upload = (n8n_type = 'dev' OR n8n_type IS NULL)
WHERE n8n_type IS NOT NULL;

-- For environments with NULL type, set reasonable defaults
UPDATE environments 
SET allow_upload = true
WHERE n8n_type IS NULL AND allow_upload = false;

-- Add indexes for the new flags
CREATE INDEX IF NOT EXISTS idx_environments_is_production ON environments (is_production);
CREATE INDEX IF NOT EXISTS idx_environments_allow_upload ON environments (allow_upload);

-- Add comments explaining the fields
COMMENT ON COLUMN environments.n8n_type IS 'Optional metadata for categorization/display (e.g., dev, staging, production, qa). Not used for business logic.';
COMMENT ON COLUMN environments.is_production IS 'Business logic flag: true if this is a production environment. Used for pipeline rules (e.g., disallow placeholder credentials).';
COMMENT ON COLUMN environments.allow_upload IS 'Feature flag: true if workflows can be uploaded/backed up to GitHub from this environment.';

