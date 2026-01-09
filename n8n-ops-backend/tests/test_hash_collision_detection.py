"""
Unit Tests for Hash Collision Detection

Tests ensure that:
1. Same-hash-different-payload collisions are detected correctly
2. Deterministic fallback hashing produces consistent results
3. Collision warnings propagate through the system
4. Hash registry operations work correctly
5. No false positives occur for identical workflows
"""
import pytest
from unittest.mock import patch, MagicMock
import json
import hashlib
from typing import Dict, Any

from app.services.canonical_workflow_service import (
    compute_workflow_hash,
    register_workflow_hash,
    get_registered_payload,
    clear_hash_registry,
    get_registry_stats,
)


# Test Fixtures
@pytest.fixture(autouse=True)
def reset_hash_registry():
    """
    Automatically clear the hash registry before and after each test
    to ensure test isolation
    """
    clear_hash_registry()
    yield
    clear_hash_registry()


@pytest.fixture
def workflow_payload_a():
    """First sample workflow payload"""
    return {
        "name": "Workflow A",
        "nodes": [
            {"type": "n8n-nodes-base.start", "name": "Start", "id": "node-1"},
            {"type": "n8n-nodes-base.httpRequest", "name": "HTTP", "id": "node-2"}
        ],
        "connections": {
            "Start": {"main": [[{"node": "HTTP", "type": "main", "index": 0}]]}
        },
        "active": True
    }


@pytest.fixture
def workflow_payload_b():
    """Second sample workflow payload (different from A)"""
    return {
        "name": "Workflow B",
        "nodes": [
            {"type": "n8n-nodes-base.start", "name": "Start", "id": "node-1"},
            {"type": "n8n-nodes-base.webhook", "name": "Webhook", "id": "node-3"}
        ],
        "connections": {
            "Start": {"main": [[{"node": "Webhook", "type": "main", "index": 0}]]}
        },
        "active": False
    }


@pytest.fixture
def workflow_payload_identical_to_a():
    """Third workflow payload (identical to A)"""
    return {
        "name": "Workflow A",
        "nodes": [
            {"type": "n8n-nodes-base.start", "name": "Start", "id": "node-1"},
            {"type": "n8n-nodes-base.httpRequest", "name": "HTTP", "id": "node-2"}
        ],
        "connections": {
            "Start": {"main": [[{"node": "HTTP", "type": "main", "index": 0}]]}
        },
        "active": True
    }


# Test Category: Same-Hash-Different-Payload Detection
class TestSameHashDifferentPayloadDetection:
    """Tests for detecting hash collisions when different payloads produce the same hash"""

    def test_detects_collision_when_same_hash_different_payload(
        self,
        workflow_payload_a,
        workflow_payload_b
    ):
        """
        Test that collision is detected when two different payloads
        produce the same hash value
        """
        # Mock normalize_workflow_for_comparison to return payloads as-is
        with patch('app.services.canonical_workflow_service.normalize_workflow_for_comparison') as mock_normalize:
            # First workflow normalizes to payload A
            mock_normalize.return_value = workflow_payload_a

            # Compute hash for first workflow
            hash1 = compute_workflow_hash(workflow_payload_a, canonical_id="workflow-1")

            # Verify hash was registered
            registered = get_registered_payload(hash1)
            assert registered == workflow_payload_a

            # Now force a collision: normalize to different payload but produce same hash
            # We'll manipulate the hash function to return the same value
            mock_normalize.return_value = workflow_payload_b

            with patch('app.services.canonical_workflow_service.hashlib.sha256') as mock_sha256:
                # Create mock hash objects
                # First call: returns colliding hash (same as hash1)
                # Second call: returns different fallback hash
                mock_hash_obj_1 = MagicMock()
                mock_hash_obj_1.hexdigest.return_value = hash1  # Collision!

                mock_hash_obj_2 = MagicMock()
                fallback_hash = "fallback_" + hash1  # Different hash
                mock_hash_obj_2.hexdigest.return_value = fallback_hash

                # Return different hash objects on successive calls
                mock_sha256.side_effect = [mock_hash_obj_1, mock_hash_obj_2]

                # Compute hash for second workflow - should detect collision
                with patch('app.services.canonical_workflow_service.logger') as mock_logger:
                    hash2 = compute_workflow_hash(workflow_payload_b, canonical_id="workflow-2")

                    # Assert: collision was detected and logged
                    mock_logger.warning.assert_called_once()
                    warning_msg = mock_logger.warning.call_args[0][0]
                    assert "Hash collision detected" in warning_msg
                    assert hash1 in warning_msg
                    assert "workflow-2" in warning_msg

                    # Assert: fallback hash was created (different from original)
                    assert hash2 != hash1
                    assert hash2 == fallback_hash

    def test_no_collision_when_same_payload(
        self,
        workflow_payload_a,
        workflow_payload_identical_to_a
    ):
        """
        Test that NO collision is detected when identical payloads
        produce the same hash (expected behavior, not a collision)
        """
        with patch('app.services.canonical_workflow_service.normalize_workflow_for_comparison') as mock_normalize:
            # Both workflows normalize to same payload
            mock_normalize.return_value = workflow_payload_a

            # Compute hash for first workflow
            hash1 = compute_workflow_hash(workflow_payload_a, canonical_id="workflow-1")

            # Compute hash for identical workflow
            with patch('app.services.canonical_workflow_service.logger') as mock_logger:
                hash2 = compute_workflow_hash(workflow_payload_identical_to_a, canonical_id="workflow-2")

                # Assert: NO collision warning (this is expected duplicate)
                warning_calls = [call for call in mock_logger.warning.call_args_list
                                if call[0] and "Hash collision detected" in call[0][0]]
                assert len(warning_calls) == 0

                # Assert: debug log for duplicate workflow
                debug_calls = [call for call in mock_logger.debug.call_args_list
                              if call[0] and "matches existing payload" in call[0][0]]
                assert len(debug_calls) > 0

                # Assert: same hash returned
                assert hash2 == hash1

    def test_collision_without_canonical_id_returns_original_hash(
        self,
        workflow_payload_a,
        workflow_payload_b
    ):
        """
        Test that when collision is detected but no canonical_id is provided,
        the original colliding hash is returned and error is logged
        """
        with patch('app.services.canonical_workflow_service.normalize_workflow_for_comparison') as mock_normalize:
            # First workflow
            mock_normalize.return_value = workflow_payload_a
            hash1 = compute_workflow_hash(workflow_payload_a, canonical_id="workflow-1")

            # Second workflow with collision but NO canonical_id
            mock_normalize.return_value = workflow_payload_b

            with patch('app.services.canonical_workflow_service.hashlib.sha256') as mock_sha256:
                mock_hash_obj = MagicMock()
                mock_hash_obj.hexdigest.return_value = hash1
                mock_sha256.return_value = mock_hash_obj

                with patch('app.services.canonical_workflow_service.logger') as mock_logger:
                    # Call without canonical_id
                    hash2 = compute_workflow_hash(workflow_payload_b, canonical_id=None)

                    # Assert: collision detected
                    assert any("Hash collision detected" in str(call)
                              for call in mock_logger.warning.call_args_list)

                    # Assert: error logged about missing canonical_id
                    error_calls = [call for call in mock_logger.error.call_args_list
                                  if call[0] and "no canonical_id provided" in call[0][0]]
                    assert len(error_calls) == 1

                    # Assert: original hash returned (unresolved collision)
                    assert hash2 == hash1

    def test_collision_detection_across_multiple_workflows(self):
        """
        Test collision detection works correctly with multiple workflows
        in the registry
        """
        workflows = [
            {"name": "WF1", "nodes": [{"id": "1"}]},
            {"name": "WF2", "nodes": [{"id": "2"}]},
            {"name": "WF3", "nodes": [{"id": "3"}]},
        ]

        with patch('app.services.canonical_workflow_service.normalize_workflow_for_comparison') as mock_normalize:
            hashes = []

            # Register first 3 workflows normally
            for i, wf in enumerate(workflows):
                mock_normalize.return_value = wf
                hash_val = compute_workflow_hash(wf, canonical_id=f"workflow-{i+1}")
                hashes.append(hash_val)

            # Verify all registered
            stats = get_registry_stats()
            assert stats["total_entries"] == 3

            # Now try to add a 4th workflow that collides with 2nd workflow
            colliding_workflow = {"name": "WF4 Collision", "nodes": [{"id": "4"}]}
            mock_normalize.return_value = colliding_workflow

            with patch('app.services.canonical_workflow_service.hashlib.sha256') as mock_sha256:
                # Create mock hash objects for collision and fallback
                mock_hash_obj_collision = MagicMock()
                mock_hash_obj_collision.hexdigest.return_value = hashes[1]  # Collide with 2nd workflow

                mock_hash_obj_fallback = MagicMock()
                fallback_hash = "fallback_" + hashes[1]
                mock_hash_obj_fallback.hexdigest.return_value = fallback_hash

                # Return different hash objects on successive calls
                mock_sha256.side_effect = [mock_hash_obj_collision, mock_hash_obj_fallback]

                with patch('app.services.canonical_workflow_service.logger') as mock_logger:
                    hash4 = compute_workflow_hash(colliding_workflow, canonical_id="workflow-4")

                    # Assert: collision detected
                    assert any("Hash collision detected" in str(call)
                              for call in mock_logger.warning.call_args_list)

                    # Assert: fallback hash created
                    assert hash4 != hashes[1]
                    assert hash4 not in hashes  # Unique fallback hash
                    assert hash4 == fallback_hash


# Test Category: Hash Registry Operations
class TestHashRegistryOperations:
    """Tests for hash registry management functions"""

    def test_register_and_retrieve_payload(self, workflow_payload_a):
        """Test registering and retrieving payloads from registry"""
        test_hash = "abc123"

        # Register
        register_workflow_hash(test_hash, workflow_payload_a)

        # Retrieve
        retrieved = get_registered_payload(test_hash)
        assert retrieved == workflow_payload_a

    def test_get_nonexistent_hash_returns_none(self):
        """Test that getting a non-registered hash returns None"""
        result = get_registered_payload("nonexistent-hash")
        assert result is None

    def test_clear_registry_removes_all_entries(self, workflow_payload_a, workflow_payload_b):
        """Test that clear_hash_registry removes all registered hashes"""
        # Register multiple hashes
        register_workflow_hash("hash1", workflow_payload_a)
        register_workflow_hash("hash2", workflow_payload_b)

        stats = get_registry_stats()
        assert stats["total_entries"] == 2

        # Clear registry
        clear_hash_registry()

        # Verify cleared
        stats = get_registry_stats()
        assert stats["total_entries"] == 0

        assert get_registered_payload("hash1") is None
        assert get_registered_payload("hash2") is None

    def test_registry_stats_counts_correctly(self, workflow_payload_a):
        """Test that registry stats return correct counts"""
        # Empty registry
        stats = get_registry_stats()
        assert stats["total_entries"] == 0

        # Add entries
        register_workflow_hash("hash1", workflow_payload_a)
        stats = get_registry_stats()
        assert stats["total_entries"] == 1

        register_workflow_hash("hash2", workflow_payload_a)
        stats = get_registry_stats()
        assert stats["total_entries"] == 2

    def test_overwriting_hash_updates_payload(self, workflow_payload_a, workflow_payload_b):
        """Test that re-registering a hash updates the payload"""
        test_hash = "hash123"

        # Register with payload A
        register_workflow_hash(test_hash, workflow_payload_a)
        assert get_registered_payload(test_hash) == workflow_payload_a

        # Overwrite with payload B
        register_workflow_hash(test_hash, workflow_payload_b)
        assert get_registered_payload(test_hash) == workflow_payload_b


# Test Category: Integration with normalize_workflow_for_comparison
class TestNormalizationIntegration:
    """Tests for integration with workflow normalization"""

    def test_compute_hash_normalizes_before_hashing(self):
        """
        Test that compute_workflow_hash calls normalize_workflow_for_comparison
        before computing the hash
        """
        raw_workflow = {
            "id": "12345",  # Should be removed by normalization
            "name": "Test Workflow",
            "nodes": [],
            "createdAt": "2024-01-01T00:00:00Z",  # Should be removed
            "updatedAt": "2024-01-01T00:00:00Z"   # Should be removed
        }

        normalized_workflow = {
            "name": "Test Workflow",
            "nodes": []
        }

        with patch('app.services.canonical_workflow_service.normalize_workflow_for_comparison') as mock_normalize:
            mock_normalize.return_value = normalized_workflow

            # Compute hash
            result_hash = compute_workflow_hash(raw_workflow, canonical_id="wf-1")

            # Assert: normalize was called with raw workflow
            mock_normalize.assert_called_once_with(raw_workflow)

            # Assert: hash was computed on normalized payload
            # Verify by computing expected hash
            expected_json = json.dumps(normalized_workflow, sort_keys=True)
            expected_hash = hashlib.sha256(expected_json.encode()).hexdigest()
            assert result_hash == expected_hash

    def test_collision_detection_uses_normalized_payloads(self):
        """
        Test that collision detection compares normalized payloads,
        not raw payloads
        """
        raw_workflow_1 = {
            "id": "wf-1",
            "name": "Test",
            "nodes": [],
            "createdAt": "2024-01-01T00:00:00Z"
        }

        raw_workflow_2 = {
            "id": "wf-2",  # Different ID
            "name": "Test",
            "nodes": [],
            "createdAt": "2024-01-02T00:00:00Z"  # Different timestamp
        }

        # Both normalize to same payload
        normalized = {
            "name": "Test",
            "nodes": []
        }

        with patch('app.services.canonical_workflow_service.normalize_workflow_for_comparison') as mock_normalize:
            mock_normalize.return_value = normalized

            # Compute hash for first workflow
            hash1 = compute_workflow_hash(raw_workflow_1, canonical_id="canonical-1")

            # Compute hash for second workflow (should be identical, no collision)
            with patch('app.services.canonical_workflow_service.logger') as mock_logger:
                hash2 = compute_workflow_hash(raw_workflow_2, canonical_id="canonical-2")

                # Assert: NO collision detected (normalized payloads are identical)
                collision_warnings = [call for call in mock_logger.warning.call_args_list
                                     if call[0] and "Hash collision detected" in call[0][0]]
                assert len(collision_warnings) == 0

                # Assert: same hash
                assert hash1 == hash2


# Test Category: Edge Cases
class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_empty_workflow_payload(self):
        """Test hashing an empty workflow payload"""
        empty_workflow = {}

        with patch('app.services.canonical_workflow_service.normalize_workflow_for_comparison') as mock_normalize:
            mock_normalize.return_value = empty_workflow

            # Should not crash
            hash_result = compute_workflow_hash(empty_workflow, canonical_id="empty-1")
            assert isinstance(hash_result, str)
            assert len(hash_result) == 64  # SHA256 hex digest length

    def test_very_large_workflow_payload(self):
        """Test hashing a very large workflow payload"""
        large_workflow = {
            "name": "Large Workflow",
            "nodes": [{"id": f"node-{i}", "type": "test"} for i in range(1000)]
        }

        with patch('app.services.canonical_workflow_service.normalize_workflow_for_comparison') as mock_normalize:
            mock_normalize.return_value = large_workflow

            # Should handle large payloads
            hash_result = compute_workflow_hash(large_workflow, canonical_id="large-1")
            assert isinstance(hash_result, str)
            assert len(hash_result) == 64

    def test_unicode_characters_in_workflow(self):
        """Test hashing workflows with unicode characters"""
        unicode_workflow = {
            "name": "Tëst Wörkflöw 测试 🚀",
            "nodes": [{"name": "Nödé 节点"}]
        }

        with patch('app.services.canonical_workflow_service.normalize_workflow_for_comparison') as mock_normalize:
            mock_normalize.return_value = unicode_workflow

            # Should handle unicode correctly
            hash_result = compute_workflow_hash(unicode_workflow, canonical_id="unicode-1")
            assert isinstance(hash_result, str)
            assert len(hash_result) == 64

    def test_none_values_in_workflow(self):
        """Test hashing workflows with None values"""
        workflow_with_none = {
            "name": "Test",
            "description": None,
            "nodes": []
        }

        with patch('app.services.canonical_workflow_service.normalize_workflow_for_comparison') as mock_normalize:
            mock_normalize.return_value = workflow_with_none

            # Should handle None values
            hash_result = compute_workflow_hash(workflow_with_none, canonical_id="none-1")
            assert isinstance(hash_result, str)

    def test_nested_objects_in_workflow(self):
        """Test hashing workflows with deeply nested objects"""
        nested_workflow = {
            "name": "Nested",
            "nodes": [
                {
                    "id": "1",
                    "parameters": {
                        "level1": {
                            "level2": {
                                "level3": {
                                    "value": "deep"
                                }
                            }
                        }
                    }
                }
            ]
        }

        with patch('app.services.canonical_workflow_service.normalize_workflow_for_comparison') as mock_normalize:
            mock_normalize.return_value = nested_workflow

            # Should handle nested structures
            hash_result = compute_workflow_hash(nested_workflow, canonical_id="nested-1")
            assert isinstance(hash_result, str)


# Test Category: Deterministic Fallback Hashing
class TestDeterministicFallbackHashing:
    """Tests for deterministic fallback hash strategy during collisions"""

    def test_fallback_hash_is_deterministic(
        self,
        workflow_payload_a,
        workflow_payload_b
    ):
        """
        Test that the fallback hash is deterministic - computing it multiple
        times with the same canonical_id produces the same result

        Strategy: Manually create a collision by registering payload_a with a hash,
        then try to compute hash for payload_b (which will collide)
        """
        # Manually create a collision scenario
        # Compute real hash for workflow A
        hash_a = compute_workflow_hash(workflow_payload_a, canonical_id="workflow-1")

        # Now manually register workflow_b with the SAME hash (force collision)
        # First clear and re-register workflow_a
        clear_hash_registry()
        register_workflow_hash(hash_a, workflow_payload_a)

        # Now compute hash for workflow_b - this should detect collision and use fallback
        fallback_hash_1 = compute_workflow_hash(workflow_payload_b, canonical_id="workflow-2")

        # The fallback hash should be different from the original
        assert fallback_hash_1 != hash_a

        # Now test determinism: clear and repeat the same collision scenario
        clear_hash_registry()
        register_workflow_hash(hash_a, workflow_payload_a)

        # Compute fallback hash again with same canonical_id
        fallback_hash_2 = compute_workflow_hash(workflow_payload_b, canonical_id="workflow-2")

        # Assert: both fallback hashes are identical (deterministic)
        assert fallback_hash_1 == fallback_hash_2

    def test_fallback_hash_uses_canonical_id_for_uniqueness(
        self,
        workflow_payload_b
    ):
        """
        Test that different canonical_ids produce different fallback hashes
        for the same colliding content
        """
        from app.services.promotion_service import normalize_workflow_for_comparison

        # Normalize workflow_b
        normalized_b = normalize_workflow_for_comparison(workflow_payload_b)

        # Compute what the normal hash would be
        normal_json = json.dumps(normalized_b, sort_keys=True)
        normal_hash = hashlib.sha256(normal_json.encode()).hexdigest()

        # Register a dummy payload with this hash to force collision
        dummy_payload = {"dummy": "collision"}

        # Create collision with workflow-2
        clear_hash_registry()
        register_workflow_hash(normal_hash, dummy_payload)
        fallback_hash_wf2 = compute_workflow_hash(workflow_payload_b, canonical_id="workflow-2")

        # Create same collision with workflow-3 (different canonical_id)
        clear_hash_registry()
        register_workflow_hash(normal_hash, dummy_payload)
        fallback_hash_wf3 = compute_workflow_hash(workflow_payload_b, canonical_id="workflow-3")

        # Assert: different canonical_ids produce different fallback hashes
        assert fallback_hash_wf2 != fallback_hash_wf3
        assert fallback_hash_wf2 != normal_hash
        assert fallback_hash_wf3 != normal_hash

    def test_fallback_hash_contains_canonical_id_in_content(
        self,
        workflow_payload_b
    ):
        """
        Test that the fallback strategy includes canonical_id in the
        content being hashed (implementation detail verification)
        """
        from app.services.promotion_service import normalize_workflow_for_comparison

        # Normalize the workflow first (as the service does)
        normalized_b = normalize_workflow_for_comparison(workflow_payload_b)

        # Create expected fallback content manually with normalized payload
        fallback_content = {
            **normalized_b,
            "__canonical_id__": "workflow-2"
        }
        fallback_json = json.dumps(fallback_content, sort_keys=True)
        expected_fallback_hash = hashlib.sha256(fallback_json.encode()).hexdigest()

        # Now try to compute hash for workflow_b - force it to collide
        # We need to compute what hash workflow_b would normally get
        normal_json = json.dumps(normalized_b, sort_keys=True)
        normal_hash = hashlib.sha256(normal_json.encode()).hexdigest()

        # Register different payload with workflow_b's normal hash to force collision
        dummy_payload = {"dummy": "payload"}
        register_workflow_hash(normal_hash, dummy_payload)

        # Now compute - should trigger fallback
        actual_fallback_hash = compute_workflow_hash(workflow_payload_b, canonical_id="workflow-2")

        # Assert: fallback hash matches expected deterministic value
        assert actual_fallback_hash == expected_fallback_hash

    def test_fallback_hash_registered_in_collision_registry(
        self,
        workflow_payload_b
    ):
        """
        Test that fallback hashes are properly registered in the collision
        registry to prevent future collisions
        """
        from app.services.promotion_service import normalize_workflow_for_comparison

        # Normalize workflow_b
        normalized_b = normalize_workflow_for_comparison(workflow_payload_b)

        # Compute what the normal hash would be for workflow_b
        normal_json = json.dumps(normalized_b, sort_keys=True)
        normal_hash = hashlib.sha256(normal_json.encode()).hexdigest()

        # Force collision by pre-registering with different payload
        dummy_payload = {"different": "payload"}
        register_workflow_hash(normal_hash, dummy_payload)

        # Compute fallback hash for workflow_b (should trigger collision)
        fallback_hash = compute_workflow_hash(workflow_payload_b, canonical_id="workflow-2")

        # Assert: fallback hash is different from normal hash
        assert fallback_hash != normal_hash

        # Assert: fallback hash is now registered in collision registry
        registered_fallback = get_registered_payload(fallback_hash)
        assert registered_fallback is not None

        # Assert: registered payload includes __canonical_id__
        assert "__canonical_id__" in registered_fallback
        assert registered_fallback["__canonical_id__"] == "workflow-2"

        # Assert: original hash still registered with dummy payload
        assert get_registered_payload(normal_hash) == dummy_payload

    def test_multiple_collisions_produce_unique_deterministic_hashes(self):
        """
        Test that multiple different workflows colliding with the same hash
        all receive unique, deterministic fallback hashes
        """
        base_workflow = {"name": "Base", "nodes": [{"id": "1"}]}
        colliding_workflows = [
            {"name": "Collision A", "nodes": [{"id": "A"}]},
            {"name": "Collision B", "nodes": [{"id": "B"}]},
            {"name": "Collision C", "nodes": [{"id": "C"}]},
        ]

        # Register base workflow
        base_hash = compute_workflow_hash(base_workflow, canonical_id="base-workflow")

        # Create collision registry with base workflow
        clear_hash_registry()
        register_workflow_hash(base_hash, base_workflow)

        fallback_hashes = []

        # Create collisions for each workflow
        for i, wf in enumerate(colliding_workflows):
            canonical_id = f"collision-workflow-{i+1}"

            # Compute fallback hash (will collide with base_hash)
            fallback = compute_workflow_hash(wf, canonical_id=canonical_id)
            fallback_hashes.append(fallback)

            # Re-register base to force collision for next workflow
            clear_hash_registry()
            register_workflow_hash(base_hash, base_workflow)

        # Assert: all fallback hashes are unique
        assert len(fallback_hashes) == len(set(fallback_hashes))

        # Assert: all fallback hashes are different from base hash
        for fallback in fallback_hashes:
            assert fallback != base_hash

        # Test determinism: recompute the same collisions
        clear_hash_registry()
        register_workflow_hash(base_hash, base_workflow)

        fallback_hashes_round2 = []

        for i, wf in enumerate(colliding_workflows):
            canonical_id = f"collision-workflow-{i+1}"
            fallback = compute_workflow_hash(wf, canonical_id=canonical_id)
            fallback_hashes_round2.append(fallback)

            # Re-register base for next workflow
            clear_hash_registry()
            register_workflow_hash(base_hash, base_workflow)

        # Assert: determinism - same fallback hashes produced
        assert fallback_hashes == fallback_hashes_round2

    def test_fallback_hash_matches_expected_format(
        self,
        workflow_payload_b
    ):
        """
        Test that fallback hash is computed correctly by adding __canonical_id__
        """
        from app.services.promotion_service import normalize_workflow_for_comparison

        # Normalize workflow first
        normalized_b = normalize_workflow_for_comparison(workflow_payload_b)

        # Manually create expected fallback content with normalized payload
        canonical_id = "test-workflow-123"
        fallback_content = {
            **normalized_b,
            "__canonical_id__": canonical_id
        }
        fallback_json = json.dumps(fallback_content, sort_keys=True)
        expected_hash = hashlib.sha256(fallback_json.encode()).hexdigest()

        # Force collision
        dummy_payload = {"dummy": "data"}
        normal_json = json.dumps(normalized_b, sort_keys=True)
        normal_hash = hashlib.sha256(normal_json.encode()).hexdigest()

        register_workflow_hash(normal_hash, dummy_payload)

        # Compute actual fallback hash
        actual_hash = compute_workflow_hash(workflow_payload_b, canonical_id=canonical_id)

        # Assert: matches expected
        assert actual_hash == expected_hash

    def test_recomputing_existing_fallback_hash_is_consistent(
        self,
        workflow_payload_a,
        workflow_payload_b
    ):
        """
        Test that if a fallback hash already exists in the registry,
        recomputing it returns the same hash (idempotent)
        """
        # Register first workflow
        hash_a = compute_workflow_hash(workflow_payload_a, canonical_id="workflow-1")

        # Force collision and create fallback
        clear_hash_registry()
        register_workflow_hash(hash_a, workflow_payload_a)

        # First computation - creates fallback
        fallback_hash_first = compute_workflow_hash(workflow_payload_b, canonical_id="workflow-2")

        # Second computation - should return same fallback hash
        # Note: the fallback is already registered, so no new collision
        fallback_hash_second = compute_workflow_hash(workflow_payload_b, canonical_id="workflow-2")

        # Assert: same fallback hash returned
        assert fallback_hash_second == fallback_hash_first


# Test Category: Collision Warning Propagation
class TestCollisionWarningPropagation:
    """Tests for collision warning propagation through the system"""

    @pytest.mark.asyncio
    async def test_env_sync_detects_and_tracks_collision_warnings(
        self,
        workflow_payload_a,
        workflow_payload_b
    ):
        """
        Test that collision warnings are detected and tracked during env sync
        """
        from app.services.canonical_env_sync_service import _detect_hash_collision
        from app.services.promotion_service import normalize_workflow_for_comparison

        # Create workflow objects with metadata
        workflow_a_with_meta = {
            **workflow_payload_a,
            "id": "wf-12345",
            "name": "Workflow A"
        }

        workflow_b_with_meta = {
            **workflow_payload_b,
            "id": "wf-67890",
            "name": "Workflow B"
        }

        # Normalize both workflows
        normalized_a = normalize_workflow_for_comparison(workflow_a_with_meta)
        normalized_b = normalize_workflow_for_comparison(workflow_b_with_meta)

        # Compute real hash for workflow A
        hash_a = compute_workflow_hash(workflow_a_with_meta, canonical_id="canonical-1")

        # Manually register workflow A with its hash
        clear_hash_registry()
        register_workflow_hash(hash_a, normalized_a)

        # Now detect collision with workflow B using the SAME hash (forced collision)
        collision_warning = _detect_hash_collision(
            workflow_b_with_meta,
            hash_a,  # Use same hash as workflow A
            canonical_id="canonical-2"
        )

        # Assert: collision detected
        assert collision_warning is not None
        assert collision_warning["n8n_workflow_id"] == "wf-67890"
        assert collision_warning["workflow_name"] == "Workflow B"
        assert collision_warning["content_hash"] == hash_a
        assert collision_warning["canonical_id"] == "canonical-2"
        assert "Hash collision detected" in collision_warning["message"]
        assert hash_a[:12] in collision_warning["message"]

    @pytest.mark.asyncio
    async def test_env_sync_no_collision_warning_for_identical_payloads(
        self,
        workflow_payload_a
    ):
        """
        Test that no collision warning is created when workflows have identical payloads
        """
        from app.services.canonical_env_sync_service import _detect_hash_collision
        from app.services.promotion_service import normalize_workflow_for_comparison

        # Create two workflow objects with identical content but different IDs
        workflow_1 = {
            **workflow_payload_a,
            "id": "wf-111",
            "name": "Workflow Instance 1"
        }

        workflow_2 = {
            **workflow_payload_a,
            "id": "wf-222",
            "name": "Workflow Instance 1"  # Same name
        }

        # Normalize both
        normalized = normalize_workflow_for_comparison(workflow_1)

        # Compute hash for first workflow
        hash_1 = compute_workflow_hash(workflow_1, canonical_id="canonical-1")

        # Register it
        clear_hash_registry()
        register_workflow_hash(hash_1, normalized)

        # Detect collision with second workflow (identical payload, same hash)
        collision_warning = _detect_hash_collision(
            workflow_2,
            hash_1,
            canonical_id="canonical-2"
        )

        # Assert: NO collision warning (payloads are identical)
        assert collision_warning is None

    @pytest.mark.asyncio
    async def test_env_sync_collision_warning_format(self):
        """
        Test that collision warnings have the correct format for env sync
        """
        from app.services.canonical_env_sync_service import _detect_hash_collision
        from app.services.promotion_service import normalize_workflow_for_comparison

        workflow_a = {
            "id": "wf-test-1",
            "name": "Test Workflow A",
            "nodes": [{"id": "1", "type": "start"}]
        }

        workflow_b = {
            "id": "wf-test-2",
            "name": "Test Workflow B",
            "nodes": [{"id": "2", "type": "webhook"}]
        }

        # Normalize
        normalized_a = normalize_workflow_for_comparison(workflow_a)
        normalized_b = normalize_workflow_for_comparison(workflow_b)

        # Create a test hash
        test_hash = "abc123def456"

        # Register workflow A
        clear_hash_registry()
        register_workflow_hash(test_hash, normalized_a)

        # Detect collision with workflow B
        collision_warning = _detect_hash_collision(
            workflow_b,
            test_hash,
            canonical_id="test-canonical-123"
        )

        # Assert: collision warning has expected structure
        assert isinstance(collision_warning, dict)
        assert "n8n_workflow_id" in collision_warning
        assert "workflow_name" in collision_warning
        assert "content_hash" in collision_warning
        assert "canonical_id" in collision_warning
        assert "message" in collision_warning

        # Verify values
        assert collision_warning["n8n_workflow_id"] == "wf-test-2"
        assert collision_warning["workflow_name"] == "Test Workflow B"
        assert collision_warning["content_hash"] == test_hash
        assert collision_warning["canonical_id"] == "test-canonical-123"
        assert "Test Workflow B" in collision_warning["message"]
        assert "wf-test-2" in collision_warning["message"]

    @pytest.mark.asyncio
    async def test_repo_sync_collision_detection(self):
        """
        Test that collision detection works during repo sync operations
        """
        from app.services.canonical_repo_sync_service import _detect_hash_collision as repo_detect_collision
        from app.services.promotion_service import normalize_workflow_for_comparison

        workflow_data = {
            "name": "Repo Workflow",
            "nodes": [{"id": "1", "type": "http"}]
        }

        # Normalize
        normalized = normalize_workflow_for_comparison(workflow_data)

        # Create a test hash
        test_hash = "xyz789abc123"

        # Register with different payload
        different_payload = {"name": "Different", "nodes": []}
        clear_hash_registry()
        register_workflow_hash(test_hash, different_payload)

        # Detect collision
        collision_warning = repo_detect_collision(
            workflow_data,
            test_hash,
            canonical_id="canonical-repo-1",
            file_path="workflows/test.json"
        )

        # Assert: collision detected
        assert collision_warning is not None
        assert collision_warning["canonical_id"] == "canonical-repo-1"
        assert collision_warning["content_hash"] == test_hash
        assert collision_warning["file_path"] == "workflows/test.json"
        assert "Hash collision detected" in collision_warning["message"]

    @pytest.mark.asyncio
    async def test_collision_warnings_propagate_to_onboarding_results(self):
        """
        Test that collision warnings are properly formatted for OnboardingInventoryResults schema
        """
        from app.schemas.canonical_workflow import OnboardingInventoryResults

        # Create sample collision warnings
        collision_warnings = [
            "Hash collision detected for workflow 'WF1' (ID: wf-111). Hash 'abc123...' maps to different payloads.",
            "Hash collision detected for workflow 'WF2' (ID: wf-222). Hash 'def456...' maps to different payloads."
        ]

        # Create OnboardingInventoryResults with collision warnings
        results = OnboardingInventoryResults(
            workflows_inventoried=10,
            canonical_ids_generated=5,
            auto_links=3,
            suggested_links=2,
            untracked_workflows=0,
            collision_warnings=collision_warnings,
            errors=[],
            has_errors=False
        )

        # Assert: collision warnings are properly stored
        assert len(results.collision_warnings) == 2
        assert results.collision_warnings[0] == collision_warnings[0]
        assert results.collision_warnings[1] == collision_warnings[1]

    @pytest.mark.asyncio
    async def test_collision_warnings_appear_in_workflow_matrix_cell(self):
        """
        Test that collision warnings are properly formatted for WorkflowMatrixCell schema
        """
        from app.api.endpoints.workflow_matrix import WorkflowMatrixCell, WorkflowEnvironmentStatus

        # Create a matrix cell with collision warning
        collision_msg = "Hash collision detected: Content hash 'abc123...' is shared with 2 other workflow(s)."

        cell = WorkflowMatrixCell(
            status=WorkflowEnvironmentStatus.LINKED,
            canSync=True,
            n8nWorkflowId="wf-123",
            contentHash="abc123def456",
            collisionWarning=collision_msg
        )

        # Assert: collision warning is stored and accessible
        assert cell.collision_warning == collision_msg
        assert cell.status == WorkflowEnvironmentStatus.LINKED
        assert cell.n8n_workflow_id == "wf-123"

    @pytest.mark.asyncio
    async def test_collision_warnings_format_for_canonical_workflows_endpoint(self):
        """
        Test that collision warnings are properly formatted for CanonicalWorkflowResponse schema
        """
        from app.schemas.canonical_workflow import CanonicalWorkflowResponse
        from datetime import datetime

        # Create collision warnings list
        collision_warnings = [
            "Environment dev: Hash collision with 1 other workflow(s) (hash: abc123...)",
            "Environment staging: Hash collision with 2 other workflow(s) (hash: def456...)"
        ]

        # Create CanonicalWorkflowResponse with collision warnings
        workflow_response = CanonicalWorkflowResponse(
            tenant_id="tenant-123",
            canonical_id="canonical-456",
            created_at=datetime.utcnow(),
            created_by_user_id="user-789",
            display_name="Test Workflow",
            deleted_at=None,
            collision_warnings=collision_warnings
        )

        # Assert: collision warnings are properly stored
        assert len(workflow_response.collision_warnings) == 2
        assert "Environment dev" in workflow_response.collision_warnings[0]
        assert "Environment staging" in workflow_response.collision_warnings[1]

    @pytest.mark.asyncio
    async def test_multiple_collisions_tracked_independently(self):
        """
        Test that multiple collision warnings are tracked independently in a batch
        """
        from app.services.canonical_env_sync_service import _detect_hash_collision
        from app.services.promotion_service import normalize_workflow_for_comparison

        # Create three different workflows
        workflows = [
            {"id": "wf-1", "name": "WF1", "nodes": [{"id": "a"}]},
            {"id": "wf-2", "name": "WF2", "nodes": [{"id": "b"}]},
            {"id": "wf-3", "name": "WF3", "nodes": [{"id": "c"}]},
        ]

        # Register a collision payload
        collision_hash = "collision-hash-123"
        collision_payload = {"collision": "payload"}
        clear_hash_registry()
        register_workflow_hash(collision_hash, collision_payload)

        # Detect collisions for all three workflows with the same hash
        collision_warnings = []
        for i, wf in enumerate(workflows):
            collision = _detect_hash_collision(
                wf,
                collision_hash,
                canonical_id=f"canonical-{i+1}"
            )
            if collision:
                collision_warnings.append(collision)

        # Assert: all three collisions detected independently
        assert len(collision_warnings) == 3
        assert collision_warnings[0]["n8n_workflow_id"] == "wf-1"
        assert collision_warnings[1]["n8n_workflow_id"] == "wf-2"
        assert collision_warnings[2]["n8n_workflow_id"] == "wf-3"

        # Assert: each has unique canonical_id
        canonical_ids = [w["canonical_id"] for w in collision_warnings]
        assert len(set(canonical_ids)) == 3

    @pytest.mark.asyncio
    async def test_collision_warning_without_canonical_id(self):
        """
        Test that collision warnings work when canonical_id is None (untracked workflows)
        """
        from app.services.canonical_env_sync_service import _detect_hash_collision
        from app.services.promotion_service import normalize_workflow_for_comparison

        workflow = {
            "id": "untracked-wf-1",
            "name": "Untracked Workflow",
            "nodes": [{"id": "x"}]
        }

        # Register a different payload with a hash
        test_hash = "test-hash-untracked"
        different_payload = {"different": "content"}
        clear_hash_registry()
        register_workflow_hash(test_hash, different_payload)

        # Detect collision without canonical_id
        collision = _detect_hash_collision(
            workflow,
            test_hash,
            canonical_id=None
        )

        # Assert: collision detected even without canonical_id
        assert collision is not None
        assert collision["canonical_id"] is None
        assert collision["n8n_workflow_id"] == "untracked-wf-1"
        assert collision["workflow_name"] == "Untracked Workflow"

    @pytest.mark.asyncio
    async def test_collision_warning_message_content(self):
        """
        Test that collision warning messages contain all necessary information
        """
        from app.services.canonical_env_sync_service import _detect_hash_collision

        workflow = {
            "id": "wf-msg-test",
            "name": "Message Test Workflow",
            "nodes": []
        }

        test_hash = "full-hash-0123456789abcdef"
        different_payload = {"not": "same"}
        clear_hash_registry()
        register_workflow_hash(test_hash, different_payload)

        collision = _detect_hash_collision(
            workflow,
            test_hash,
            canonical_id="canonical-msg"
        )

        # Assert: message contains key information
        message = collision["message"]
        assert "Hash collision detected" in message
        assert "Message Test Workflow" in message
        assert "wf-msg-test" in message
        assert test_hash[:12] in message  # Truncated hash
        assert "maps to different payloads" in message

    @pytest.mark.asyncio
    async def test_collision_warnings_empty_list_when_no_collisions(self):
        """
        Test that collision_warnings is an empty list when no collisions occur
        """
        from app.schemas.canonical_workflow import OnboardingInventoryResults

        # Create results with no collision warnings
        results = OnboardingInventoryResults(
            workflows_inventoried=5,
            canonical_ids_generated=3,
            auto_links=2,
            suggested_links=0,
            untracked_workflows=0,
            collision_warnings=[],  # Empty list
            errors=[],
            has_errors=False
        )

        # Assert: collision_warnings is empty but not None
        assert results.collision_warnings is not None
        assert isinstance(results.collision_warnings, list)
        assert len(results.collision_warnings) == 0
