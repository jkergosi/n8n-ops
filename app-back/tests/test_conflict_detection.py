"""
Unit tests for conflict detection in canonical reconciliation service.

Tests the conflict detection logic that identifies when workflows have been
modified both in n8n environment AND in Git independently.
"""
import pytest
from typing import Dict, Any, Optional
from datetime import datetime

from app.services.canonical_reconciliation_service import CanonicalReconciliationService
from app.schemas.canonical_workflow import WorkflowDiffStatus


class TestComputeDiffStatusBasic:
    """Basic tests for _compute_diff_status method."""

    @pytest.mark.unit
    def test_unchanged_when_hashes_identical(self):
        """Should return UNCHANGED when Git hashes are identical."""
        source_git = {"git_content_hash": "hash123"}
        target_git = {"git_content_hash": "hash123"}
        source_mapping = {"env_content_hash": "hash123"}
        target_mapping = {"env_content_hash": "hash123"}

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        assert result == WorkflowDiffStatus.UNCHANGED

    @pytest.mark.unit
    def test_added_when_target_git_missing(self):
        """Should return ADDED when workflow exists in source but not in target Git."""
        source_git = {"git_content_hash": "hash123"}
        target_git = None
        source_mapping = {"env_content_hash": "hash123"}
        target_mapping = None

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        assert result == WorkflowDiffStatus.ADDED

    @pytest.mark.unit
    def test_target_only_when_source_git_missing(self):
        """Should return TARGET_ONLY when workflow exists in target but not in source Git."""
        source_git = None
        target_git = {"git_content_hash": "hash456"}
        source_mapping = None
        target_mapping = {"env_content_hash": "hash456"}

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        assert result == WorkflowDiffStatus.TARGET_ONLY

    @pytest.mark.unit
    def test_unchanged_when_both_git_states_missing(self):
        """Should return UNCHANGED when both Git states are missing."""
        result = CanonicalReconciliationService._compute_diff_status(
            None, None, None, None
        )

        assert result == WorkflowDiffStatus.UNCHANGED


class TestComputeDiffStatusModified:
    """Tests for MODIFIED status detection."""

    @pytest.mark.unit
    def test_modified_when_git_hashes_differ_no_local_changes(self):
        """Should return MODIFIED when Git hashes differ but no local changes in source."""
        source_git = {"git_content_hash": "hash123"}
        target_git = {"git_content_hash": "hash456"}
        source_mapping = {"env_content_hash": "hash123"}  # Matches source Git
        target_mapping = {"env_content_hash": "hash456"}

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        assert result == WorkflowDiffStatus.MODIFIED

    @pytest.mark.unit
    def test_modified_when_source_git_newer_no_conflict(self):
        """Should return MODIFIED when source Git is ahead of target Git."""
        source_git = {"git_content_hash": "hash_new"}
        target_git = {"git_content_hash": "hash_old"}
        source_mapping = {"env_content_hash": "hash_new"}  # Synced with source Git
        target_mapping = {"env_content_hash": "hash_old"}  # Synced with target Git

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        assert result == WorkflowDiffStatus.MODIFIED


class TestComputeDiffStatusTargetHotfix:
    """Tests for TARGET_HOTFIX status detection."""

    @pytest.mark.unit
    def test_target_hotfix_when_target_git_modified_directly(self):
        """Should return TARGET_HOTFIX when target was modified in Git (hotfix scenario)."""
        source_git = {"git_content_hash": "hash123"}
        target_git = {"git_content_hash": "hash_hotfix"}
        source_mapping = {"env_content_hash": "hash123"}  # Source env synced with source Git
        target_mapping = {"env_content_hash": "hash123"}  # Target env matches source Git

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        assert result == WorkflowDiffStatus.TARGET_HOTFIX

    @pytest.mark.unit
    def test_target_hotfix_clear_scenario(self):
        """Should detect TARGET_HOTFIX when target Git differs but target env is in sync with old source Git."""
        # Scenario: Target was in sync with source, then target Git was hotfixed
        source_git = {"git_content_hash": "source_v1"}
        target_git = {"git_content_hash": "target_hotfix"}
        source_mapping = {"env_content_hash": "source_v1"}
        target_mapping = {"env_content_hash": "source_v1"}  # Still at old sync point

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        assert result == WorkflowDiffStatus.TARGET_HOTFIX


class TestComputeDiffStatusConflict:
    """Tests for CONFLICT status detection - the core conflict scenarios."""

    @pytest.mark.unit
    def test_conflict_when_both_source_env_and_target_git_modified(self):
        """Should return CONFLICT when source env has local changes AND target Git has different changes."""
        source_git = {"git_content_hash": "hash_original"}
        target_git = {"git_content_hash": "hash_target_modified"}
        source_mapping = {"env_content_hash": "hash_source_modified"}  # Source env changed
        target_mapping = {"env_content_hash": "hash_original"}

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        assert result == WorkflowDiffStatus.CONFLICT

    @pytest.mark.unit
    def test_conflict_classic_divergence(self):
        """Should detect CONFLICT in classic divergence scenario."""
        # Scenario: Both sides modified independently from a common base
        source_git = {"git_content_hash": "base_v1"}
        target_git = {"git_content_hash": "target_v2"}
        source_mapping = {"env_content_hash": "source_v2"}  # Local changes
        target_mapping = {"env_content_hash": "base_v1"}

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        assert result == WorkflowDiffStatus.CONFLICT

    @pytest.mark.unit
    def test_conflict_when_all_hashes_differ(self):
        """Should detect CONFLICT when all four hashes are different."""
        source_git = {"git_content_hash": "hash1"}
        target_git = {"git_content_hash": "hash2"}
        source_mapping = {"env_content_hash": "hash3"}
        target_mapping = {"env_content_hash": "hash4"}

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        # This is a conflict: source env differs from source git, target git differs from source git
        assert result == WorkflowDiffStatus.CONFLICT

    @pytest.mark.unit
    def test_conflict_when_target_env_also_modified(self):
        """Should detect CONFLICT even when target env also has local changes."""
        source_git = {"git_content_hash": "base"}
        target_git = {"git_content_hash": "target_git_change"}
        source_mapping = {"env_content_hash": "source_env_change"}
        target_mapping = {"env_content_hash": "target_env_change"}

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        # Conflict: source env changed from source git, target git changed from source git
        assert result == WorkflowDiffStatus.CONFLICT


class TestComputeDiffStatusNoConflict:
    """Tests verifying that non-conflict scenarios are correctly identified."""

    @pytest.mark.unit
    def test_no_conflict_when_only_source_env_modified(self):
        """Should NOT return CONFLICT when only source env has changes (target Git unchanged)."""
        source_git = {"git_content_hash": "hash123"}
        target_git = {"git_content_hash": "hash123"}  # Target Git same as source Git
        source_mapping = {"env_content_hash": "hash_modified"}  # Source env changed
        target_mapping = {"env_content_hash": "hash123"}

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        # No conflict because target Git hasn't changed
        assert result == WorkflowDiffStatus.UNCHANGED

    @pytest.mark.unit
    def test_no_conflict_when_only_target_git_modified(self):
        """Should NOT return CONFLICT when only target Git changed (no source env changes)."""
        source_git = {"git_content_hash": "hash123"}
        target_git = {"git_content_hash": "hash_target_modified"}
        source_mapping = {"env_content_hash": "hash123"}  # Source env in sync
        target_mapping = {"env_content_hash": "hash123"}

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        # This is TARGET_HOTFIX, not a conflict
        assert result == WorkflowDiffStatus.TARGET_HOTFIX

    @pytest.mark.unit
    def test_no_conflict_when_source_env_missing(self):
        """Should NOT return CONFLICT when source env mapping is missing."""
        source_git = {"git_content_hash": "hash123"}
        target_git = {"git_content_hash": "hash456"}
        source_mapping = None  # No source env mapping
        target_mapping = {"env_content_hash": "hash456"}

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        # Without source env hash, can't detect local changes, so MODIFIED
        assert result == WorkflowDiffStatus.MODIFIED

    @pytest.mark.unit
    def test_no_conflict_when_source_env_matches_source_git(self):
        """Should NOT return CONFLICT when source env is in sync with source Git."""
        source_git = {"git_content_hash": "hash123"}
        target_git = {"git_content_hash": "hash456"}
        source_mapping = {"env_content_hash": "hash123"}  # Synced with source Git
        target_mapping = {"env_content_hash": "hash789"}

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        # No local changes in source, so MODIFIED (not conflict)
        assert result == WorkflowDiffStatus.MODIFIED


class TestBuildConflictMetadata:
    """Tests for _build_conflict_metadata helper function."""

    @pytest.mark.unit
    def test_builds_metadata_for_conflict_scenario(self):
        """Should build conflict metadata when conflict is detected."""
        source_git = {
            "git_content_hash": "source_git_hash",
            "updated_at": "2024-01-10T10:00:00Z"
        }
        target_git = {
            "git_content_hash": "target_git_hash",
            "updated_at": "2024-01-15T10:00:00Z"
        }
        source_mapping = {
            "env_content_hash": "source_env_hash",
            "updated_at": "2024-01-12T10:00:00Z"
        }
        target_mapping = {
            "env_content_hash": "target_env_hash",
            "updated_at": "2024-01-11T10:00:00Z"
        }

        metadata = CanonicalReconciliationService._build_conflict_metadata(
            source_git, target_git, source_mapping, target_mapping
        )

        assert metadata is not None
        assert metadata["source_git_hash"] == "source_git_hash"
        assert metadata["target_git_hash"] == "target_git_hash"
        assert metadata["source_env_hash"] == "source_env_hash"
        assert metadata["target_env_hash"] == "target_env_hash"
        assert metadata["conflict_type"] == "divergent_changes"
        assert "conflict_detected_at" in metadata
        assert metadata["description"] == "Source environment and target Git have independent modifications"

    @pytest.mark.unit
    def test_includes_timestamps_when_available(self):
        """Should include timestamps in metadata when available."""
        source_git = {
            "git_content_hash": "hash1",
            "updated_at": "2024-01-10T10:00:00Z"
        }
        target_git = {
            "git_content_hash": "hash2",
            "updated_at": "2024-01-15T10:00:00Z"
        }
        source_mapping = {
            "env_content_hash": "hash3",
            "updated_at": "2024-01-12T10:00:00Z"
        }
        target_mapping = {
            "env_content_hash": "hash4",
            "updated_at": "2024-01-14T10:00:00Z"
        }

        metadata = CanonicalReconciliationService._build_conflict_metadata(
            source_git, target_git, source_mapping, target_mapping
        )

        assert metadata["source_git_updated_at"] == "2024-01-10T10:00:00Z"
        assert metadata["target_git_updated_at"] == "2024-01-15T10:00:00Z"
        assert metadata["source_env_updated_at"] == "2024-01-12T10:00:00Z"
        assert metadata["target_env_updated_at"] == "2024-01-14T10:00:00Z"

    @pytest.mark.unit
    def test_returns_none_when_no_conflict(self):
        """Should return None when no conflict is detected."""
        source_git = {"git_content_hash": "hash123"}
        target_git = {"git_content_hash": "hash123"}
        source_mapping = {"env_content_hash": "hash123"}
        target_mapping = {"env_content_hash": "hash123"}

        metadata = CanonicalReconciliationService._build_conflict_metadata(
            source_git, target_git, source_mapping, target_mapping
        )

        assert metadata is None

    @pytest.mark.unit
    def test_returns_none_when_only_target_git_changed(self):
        """Should return None when only target Git has changes (not a conflict)."""
        source_git = {"git_content_hash": "hash123"}
        target_git = {"git_content_hash": "hash_different"}
        source_mapping = {"env_content_hash": "hash123"}  # No local changes
        target_mapping = {"env_content_hash": "hash123"}

        metadata = CanonicalReconciliationService._build_conflict_metadata(
            source_git, target_git, source_mapping, target_mapping
        )

        assert metadata is None

    @pytest.mark.unit
    def test_returns_none_when_source_env_matches_source_git(self):
        """Should return None when source env is synced with source Git."""
        source_git = {"git_content_hash": "hash123"}
        target_git = {"git_content_hash": "hash456"}
        source_mapping = {"env_content_hash": "hash123"}  # Matches source Git
        target_mapping = {"env_content_hash": "hash456"}

        metadata = CanonicalReconciliationService._build_conflict_metadata(
            source_git, target_git, source_mapping, target_mapping
        )

        assert metadata is None

    @pytest.mark.unit
    def test_handles_missing_timestamps_gracefully(self):
        """Should handle missing timestamps without errors."""
        source_git = {"git_content_hash": "hash1"}
        target_git = {"git_content_hash": "hash2"}
        source_mapping = {"env_content_hash": "hash3"}
        target_mapping = {"env_content_hash": "hash4"}

        metadata = CanonicalReconciliationService._build_conflict_metadata(
            source_git, target_git, source_mapping, target_mapping
        )

        assert metadata is not None
        assert "source_git_updated_at" not in metadata
        assert "target_git_updated_at" not in metadata
        assert "source_env_updated_at" not in metadata
        assert "target_env_updated_at" not in metadata

    @pytest.mark.unit
    def test_handles_none_source_mapping(self):
        """Should return None when source mapping is None."""
        source_git = {"git_content_hash": "hash1"}
        target_git = {"git_content_hash": "hash2"}
        source_mapping = None
        target_mapping = {"env_content_hash": "hash4"}

        metadata = CanonicalReconciliationService._build_conflict_metadata(
            source_git, target_git, source_mapping, target_mapping
        )

        assert metadata is None


class TestConflictDetectionEdgeCases:
    """Edge case tests for conflict detection."""

    @pytest.mark.unit
    def test_handles_none_values_gracefully(self):
        """Should handle None values without errors."""
        result = CanonicalReconciliationService._compute_diff_status(
            None, None, None, None
        )
        assert result == WorkflowDiffStatus.UNCHANGED

    @pytest.mark.unit
    def test_handles_missing_git_content_hash_field(self):
        """Should handle missing git_content_hash field."""
        source_git = {}  # Missing git_content_hash
        target_git = {"git_content_hash": "hash456"}
        source_mapping = {"env_content_hash": "hash123"}
        target_mapping = {"env_content_hash": "hash456"}

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        # Should handle gracefully
        assert result in [
            WorkflowDiffStatus.UNCHANGED,
            WorkflowDiffStatus.MODIFIED,
            WorkflowDiffStatus.TARGET_ONLY,
            WorkflowDiffStatus.ADDED,
            WorkflowDiffStatus.TARGET_HOTFIX,
            WorkflowDiffStatus.CONFLICT
        ]

    @pytest.mark.unit
    def test_handles_missing_env_content_hash_field(self):
        """Should handle missing env_content_hash field."""
        source_git = {"git_content_hash": "hash123"}
        target_git = {"git_content_hash": "hash456"}
        source_mapping = {}  # Missing env_content_hash
        target_mapping = {"env_content_hash": "hash456"}

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        # Without source env hash, can't detect local changes
        assert result == WorkflowDiffStatus.MODIFIED

    @pytest.mark.unit
    def test_same_hash_across_all_sources(self):
        """Should return UNCHANGED when all sources have the same hash."""
        same_hash = "identical_hash"
        source_git = {"git_content_hash": same_hash}
        target_git = {"git_content_hash": same_hash}
        source_mapping = {"env_content_hash": same_hash}
        target_mapping = {"env_content_hash": same_hash}

        result = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        assert result == WorkflowDiffStatus.UNCHANGED


class TestConflictDetectionIntegration:
    """Integration-style tests verifying the complete conflict detection flow."""

    @pytest.mark.unit
    def test_realistic_conflict_scenario_dev_to_staging(self):
        """Test realistic conflict scenario: DEV environment has local changes, STAGING Git has hotfix."""
        # Initial state: Both at v1
        # DEV env: User modified locally to v2
        # STAGING Git: Hotfix applied directly to Git (v3)

        source_git = {"git_content_hash": "v1_hash", "updated_at": "2024-01-01T10:00:00Z"}
        target_git = {"git_content_hash": "v3_hotfix_hash", "updated_at": "2024-01-10T15:00:00Z"}
        source_mapping = {"env_content_hash": "v2_local_hash", "updated_at": "2024-01-08T12:00:00Z"}
        target_mapping = {"env_content_hash": "v1_hash", "updated_at": "2024-01-01T10:00:00Z"}

        status = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        metadata = CanonicalReconciliationService._build_conflict_metadata(
            source_git, target_git, source_mapping, target_mapping
        )

        assert status == WorkflowDiffStatus.CONFLICT
        assert metadata is not None
        assert metadata["source_git_hash"] == "v1_hash"
        assert metadata["target_git_hash"] == "v3_hotfix_hash"
        assert metadata["source_env_hash"] == "v2_local_hash"
        assert metadata["conflict_type"] == "divergent_changes"

    @pytest.mark.unit
    def test_realistic_no_conflict_scenario_linear_progression(self):
        """Test realistic no-conflict scenario: Linear progression from DEV to STAGING."""
        # DEV Git: v2 (synced)
        # DEV env: v2 (synced with Git)
        # STAGING Git: v1 (old)
        # STAGING env: v1 (synced with its Git)

        source_git = {"git_content_hash": "v2_hash"}
        target_git = {"git_content_hash": "v1_hash"}
        source_mapping = {"env_content_hash": "v2_hash"}  # DEV synced
        target_mapping = {"env_content_hash": "v1_hash"}  # STAGING synced

        status = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        metadata = CanonicalReconciliationService._build_conflict_metadata(
            source_git, target_git, source_mapping, target_mapping
        )

        # No conflict: DEV is ahead, but no divergent changes
        assert status == WorkflowDiffStatus.MODIFIED
        assert metadata is None

    @pytest.mark.unit
    def test_realistic_no_conflict_scenario_fast_forward(self):
        """Test realistic no-conflict scenario: Fast-forward merge possible."""
        # Scenario where target can simply fast-forward to source
        source_git = {"git_content_hash": "v3_hash"}
        target_git = {"git_content_hash": "v2_hash"}
        source_mapping = {"env_content_hash": "v3_hash"}
        target_mapping = {"env_content_hash": "v2_hash"}

        status = CanonicalReconciliationService._compute_diff_status(
            source_git, target_git, source_mapping, target_mapping
        )

        assert status == WorkflowDiffStatus.MODIFIED
        # This should be safe to promote (fast-forward)

    @pytest.mark.unit
    def test_metadata_contains_all_required_fields(self):
        """Test that conflict metadata contains all required fields for resolution."""
        source_git = {
            "git_content_hash": "source_hash",
            "updated_at": "2024-01-05T10:00:00Z"
        }
        target_git = {
            "git_content_hash": "target_hash",
            "updated_at": "2024-01-10T10:00:00Z"
        }
        source_mapping = {
            "env_content_hash": "source_env_hash",
            "updated_at": "2024-01-08T10:00:00Z"
        }
        target_mapping = {
            "env_content_hash": "target_env_hash",
            "updated_at": "2024-01-06T10:00:00Z"
        }

        metadata = CanonicalReconciliationService._build_conflict_metadata(
            source_git, target_git, source_mapping, target_mapping
        )

        # Verify all required fields for UI and resolution
        required_fields = [
            "conflict_detected_at",
            "source_git_hash",
            "target_git_hash",
            "source_env_hash",
            "target_env_hash",
            "conflict_type",
            "description"
        ]

        for field in required_fields:
            assert field in metadata, f"Missing required field: {field}"

        # Verify timestamp fields
        timestamp_fields = [
            "source_git_updated_at",
            "target_git_updated_at",
            "source_env_updated_at",
            "target_env_updated_at"
        ]

        for field in timestamp_fields:
            assert field in metadata, f"Missing timestamp field: {field}"
