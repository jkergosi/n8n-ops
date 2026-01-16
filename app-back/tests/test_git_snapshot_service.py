"""
Tests for Git Snapshot Service - Core snapshot operations

Tests:
- Hash computation is deterministic and credential-agnostic
- Workflow normalization removes env-specific fields
- Snapshot manifest structure
"""
import pytest
from app.services.git_snapshot_service import (
    normalize_workflow_for_hash,
    compute_workflow_hash,
    compute_overall_hash,
)
from app.schemas.snapshot_manifest import (
    generate_snapshot_id,
    SnapshotKind,
)


class TestWorkflowNormalization:
    """Tests for workflow normalization before hashing."""

    def test_normalize_removes_id_and_timestamps(self):
        """Normalization should remove id, createdAt, updatedAt."""
        workflow = {
            "id": "abc123",
            "name": "Test Workflow",
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-15T00:00:00Z",
            "nodes": [],
        }

        normalized = normalize_workflow_for_hash(workflow)

        assert "id" not in normalized
        assert "createdAt" not in normalized
        assert "updatedAt" not in normalized
        assert normalized["name"] == "Test Workflow"

    def test_normalize_removes_active_status(self):
        """Normalization should remove active status (varies per env)."""
        workflow = {
            "name": "Test",
            "active": True,
            "nodes": [],
        }

        normalized = normalize_workflow_for_hash(workflow)

        assert "active" not in normalized

    def test_normalize_removes_tags(self):
        """Normalization should remove tags (have different IDs per env)."""
        workflow = {
            "name": "Test",
            "tags": [{"id": "tag1", "name": "Production"}],
            "tagIds": ["tag1"],
            "nodes": [],
        }

        normalized = normalize_workflow_for_hash(workflow)

        assert "tags" not in normalized
        assert "tagIds" not in normalized

    def test_normalize_credentials_to_name_only(self):
        """Normalization should compare credentials by name only, not ID."""
        workflow = {
            "name": "Test",
            "nodes": [
                {
                    "name": "HTTP Node",
                    "type": "n8n-nodes-base.httpRequest",
                    "credentials": {
                        "httpBasicAuth": {
                            "id": "cred-123-dev",  # Different per env
                            "name": "My API Creds",
                        }
                    }
                }
            ],
        }

        normalized = normalize_workflow_for_hash(workflow)

        node = normalized["nodes"][0]
        assert node["credentials"]["httpBasicAuth"] == {"name": "My API Creds"}

    def test_normalize_removes_node_position(self):
        """Normalization should remove UI/position fields from nodes."""
        workflow = {
            "name": "Test",
            "nodes": [
                {
                    "name": "Start",
                    "position": [100, 200],
                    "positionAbsolute": [100, 200],
                }
            ],
        }

        normalized = normalize_workflow_for_hash(workflow)

        node = normalized["nodes"][0]
        assert "position" not in node
        assert "positionAbsolute" not in node


class TestHashComputation:
    """Tests for workflow and overall hash computation."""

    def test_same_workflow_same_hash(self):
        """Same workflow content should produce same hash."""
        workflow = {
            "name": "Test Workflow",
            "nodes": [{"name": "Start", "type": "n8n-nodes-base.start"}],
        }

        hash1 = compute_workflow_hash(workflow)
        hash2 = compute_workflow_hash(workflow)

        assert hash1 == hash2
        assert hash1.startswith("sha256:")

    def test_different_workflow_different_hash(self):
        """Different workflow content should produce different hash."""
        workflow1 = {"name": "Workflow 1", "nodes": []}
        workflow2 = {"name": "Workflow 2", "nodes": []}

        hash1 = compute_workflow_hash(workflow1)
        hash2 = compute_workflow_hash(workflow2)

        assert hash1 != hash2

    def test_hash_ignores_id_changes(self):
        """Hash should be same regardless of workflow ID."""
        workflow1 = {"id": "id-1", "name": "Test", "nodes": []}
        workflow2 = {"id": "id-2", "name": "Test", "nodes": []}

        hash1 = compute_workflow_hash(workflow1)
        hash2 = compute_workflow_hash(workflow2)

        assert hash1 == hash2

    def test_hash_ignores_credential_id_changes(self):
        """Hash should be same regardless of credential IDs."""
        workflow1 = {
            "name": "Test",
            "nodes": [{
                "name": "HTTP",
                "credentials": {"auth": {"id": "cred-dev-123", "name": "API Key"}}
            }],
        }
        workflow2 = {
            "name": "Test",
            "nodes": [{
                "name": "HTTP",
                "credentials": {"auth": {"id": "cred-prod-456", "name": "API Key"}}
            }],
        }

        hash1 = compute_workflow_hash(workflow1)
        hash2 = compute_workflow_hash(workflow2)

        assert hash1 == hash2

    def test_overall_hash_deterministic(self):
        """Overall hash should be deterministic regardless of input order."""
        hashes = ["sha256:aaa", "sha256:bbb", "sha256:ccc"]

        overall1 = compute_overall_hash(hashes)
        overall2 = compute_overall_hash(list(reversed(hashes)))

        assert overall1 == overall2
        assert overall1.startswith("sha256:")


class TestSnapshotManifest:
    """Tests for snapshot manifest generation."""

    def test_generate_snapshot_id_is_uuid(self):
        """Snapshot ID should be a valid UUID format."""
        snapshot_id = generate_snapshot_id()

        # Should be 36 chars (8-4-4-4-12)
        assert len(snapshot_id) == 36
        assert snapshot_id.count("-") == 4

    def test_generate_snapshot_id_unique(self):
        """Each call should generate a unique ID."""
        ids = [generate_snapshot_id() for _ in range(100)]

        assert len(set(ids)) == 100  # All unique

    def test_snapshot_kind_values(self):
        """SnapshotKind enum should have expected values."""
        assert SnapshotKind.ONBOARDING.value == "onboarding"
        assert SnapshotKind.PROMOTION.value == "promotion"
        assert SnapshotKind.BACKUP.value == "backup"
        assert SnapshotKind.ROLLBACK.value == "rollback"
