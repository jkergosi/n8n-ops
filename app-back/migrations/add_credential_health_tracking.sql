-- Migration: Add Credential Health Tracking
-- Description: Adds health tracking columns to credential_mappings table
-- Date: 2025-01-07

-- Add health tracking columns to credential_mappings
ALTER TABLE credential_mappings
ADD COLUMN IF NOT EXISTS last_test_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS last_test_status VARCHAR(20),  -- 'success', 'failed', 'unsupported'
ADD COLUMN IF NOT EXISTS last_test_error TEXT;

-- Add index for querying by test status
CREATE INDEX IF NOT EXISTS idx_credential_mappings_test_status ON credential_mappings(last_test_status);

-- Add comment for documentation
COMMENT ON COLUMN credential_mappings.last_test_at IS 'Timestamp of the last manual credential test';
COMMENT ON COLUMN credential_mappings.last_test_status IS 'Status of the last credential test: success, failed, or unsupported';
COMMENT ON COLUMN credential_mappings.last_test_error IS 'Error message from the last failed test, if any';
