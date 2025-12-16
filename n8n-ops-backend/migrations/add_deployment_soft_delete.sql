-- Add soft delete fields to deployments table
ALTER TABLE deployments 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS deleted_by_user_id UUID REFERENCES users(id);

-- Create index for efficient filtering of non-deleted deployments
CREATE INDEX IF NOT EXISTS idx_deployments_deleted_at ON deployments(deleted_at) WHERE deleted_at IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN deployments.deleted_at IS 'Timestamp when deployment was soft deleted. NULL means not deleted.';
COMMENT ON COLUMN deployments.deleted_by_user_id IS 'User ID who deleted the deployment. NULL if not deleted.';

