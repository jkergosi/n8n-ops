"""
Unit tests for the diff service - workflow drift detection.
"""
import pytest
from app.services.diff_service import (
    normalize_value,
    compare_nodes,
    compare_node,
    compare_connections,
    compare_settings,
    compare_workflows,
    DriftDifference,
    DriftSummary,
    DriftResult,
    IGNORED_FIELDS,
    IGNORED_NODE_FIELDS,
)


class TestNormalizeValue:
    """Tests for normalize_value function."""

    @pytest.mark.unit
    def test_normalize_none_value(self):
        """None values should return None."""
        assert normalize_value(None) is None

    @pytest.mark.unit
    def test_normalize_primitive_values(self):
        """Primitive values should pass through unchanged."""
        assert normalize_value("string") == "string"
        assert normalize_value(123) == 123
        assert normalize_value(True) is True
        assert normalize_value(3.14) == 3.14

    @pytest.mark.unit
    def test_normalize_dict_removes_none_values(self):
        """Dicts should have None values removed."""
        input_dict = {"a": 1, "b": None, "c": "value"}
        result = normalize_value(input_dict)
        assert result == {"a": 1, "c": "value"}
        assert "b" not in result

    @pytest.mark.unit
    def test_normalize_nested_dict(self):
        """Nested dicts should be normalized recursively."""
        input_dict = {
            "level1": {
                "level2": {"value": 1, "empty": None},
                "empty": None,
            }
        }
        result = normalize_value(input_dict)
        assert result == {"level1": {"level2": {"value": 1}}}

    @pytest.mark.unit
    def test_normalize_list(self):
        """Lists should have elements normalized."""
        input_list = [1, None, {"a": 1, "b": None}, "string"]
        result = normalize_value(input_list)
        assert result == [1, None, {"a": 1}, "string"]

    @pytest.mark.unit
    def test_normalize_empty_structures(self):
        """Empty structures should return empty."""
        assert normalize_value({}) == {}
        assert normalize_value([]) == []


class TestCompareNode:
    """Tests for comparing individual nodes."""

    @pytest.mark.unit
    def test_identical_nodes_have_no_differences(self):
        """Identical nodes should produce no differences."""
        node = {
            "name": "Test Node",
            "type": "n8n-nodes-base.httpRequest",
            "parameters": {"url": "https://api.example.com"},
            "position": [100, 200],
        }
        differences = compare_node("Test Node", node, node)
        assert differences == []

    @pytest.mark.unit
    def test_type_change_detected(self):
        """Node type changes should be detected."""
        git_node = {"name": "Test", "type": "n8n-nodes-base.httpRequest"}
        runtime_node = {"name": "Test", "type": "n8n-nodes-base.set"}

        differences = compare_node("Test", git_node, runtime_node)

        assert len(differences) == 1
        assert differences[0].path == "nodes[Test].type"
        assert differences[0].git_value == "n8n-nodes-base.httpRequest"
        assert differences[0].runtime_value == "n8n-nodes-base.set"
        assert differences[0].diff_type == "modified"

    @pytest.mark.unit
    def test_parameter_change_detected(self):
        """Parameter changes should be detected."""
        git_node = {
            "name": "HTTP",
            "type": "n8n-nodes-base.httpRequest",
            "parameters": {"url": "https://old.api.com", "method": "GET"},
        }
        runtime_node = {
            "name": "HTTP",
            "type": "n8n-nodes-base.httpRequest",
            "parameters": {"url": "https://new.api.com", "method": "GET"},
        }

        differences = compare_node("HTTP", git_node, runtime_node)

        # Should detect the URL parameter change
        url_diff = next((d for d in differences if "url" in d.path), None)
        assert url_diff is not None
        assert url_diff.git_value == "https://old.api.com"
        assert url_diff.runtime_value == "https://new.api.com"

    @pytest.mark.unit
    def test_position_change_detected(self):
        """Position changes should be detected."""
        git_node = {
            "name": "Test",
            "type": "n8n-nodes-base.start",
            "position": [0, 0],
        }
        runtime_node = {
            "name": "Test",
            "type": "n8n-nodes-base.start",
            "position": [100, 200],
        }

        differences = compare_node("Test", git_node, runtime_node)

        position_diff = next((d for d in differences if "position" in d.path), None)
        assert position_diff is not None
        assert position_diff.git_value == [0, 0]
        assert position_diff.runtime_value == [100, 200]

    @pytest.mark.unit
    def test_added_parameter_detected(self):
        """New parameters in runtime should be detected as added."""
        git_node = {
            "name": "Test",
            "type": "n8n-nodes-base.httpRequest",
            "parameters": {"url": "https://api.com"},
        }
        runtime_node = {
            "name": "Test",
            "type": "n8n-nodes-base.httpRequest",
            "parameters": {"url": "https://api.com", "timeout": 5000},
        }

        differences = compare_node("Test", git_node, runtime_node)

        timeout_diff = next((d for d in differences if "timeout" in d.path), None)
        assert timeout_diff is not None
        assert timeout_diff.diff_type == "added"


class TestCompareNodes:
    """Tests for comparing lists of nodes."""

    @pytest.mark.unit
    def test_no_drift_for_identical_lists(self):
        """Identical node lists should have no drift."""
        nodes = [
            {"name": "Start", "type": "n8n-nodes-base.start"},
            {"name": "HTTP", "type": "n8n-nodes-base.httpRequest"},
        ]

        differences, summary = compare_nodes(nodes, nodes)

        assert differences == []
        assert summary.nodes_added == 0
        assert summary.nodes_removed == 0
        assert summary.nodes_modified == 0

    @pytest.mark.unit
    def test_removed_node_detected(self):
        """Nodes in git but not runtime should be marked as removed."""
        git_nodes = [
            {"name": "Start", "type": "n8n-nodes-base.start"},
            {"name": "HTTP", "type": "n8n-nodes-base.httpRequest"},
        ]
        runtime_nodes = [
            {"name": "Start", "type": "n8n-nodes-base.start"},
        ]

        differences, summary = compare_nodes(git_nodes, runtime_nodes)

        assert summary.nodes_removed == 1
        removed_diff = next((d for d in differences if d.diff_type == "removed"), None)
        assert removed_diff is not None
        assert "HTTP" in removed_diff.path

    @pytest.mark.unit
    def test_added_node_detected(self):
        """Nodes in runtime but not git should be marked as added."""
        git_nodes = [
            {"name": "Start", "type": "n8n-nodes-base.start"},
        ]
        runtime_nodes = [
            {"name": "Start", "type": "n8n-nodes-base.start"},
            {"name": "New Node", "type": "n8n-nodes-base.set"},
        ]

        differences, summary = compare_nodes(git_nodes, runtime_nodes)

        assert summary.nodes_added == 1
        added_diff = next((d for d in differences if d.diff_type == "added"), None)
        assert added_diff is not None
        assert "New Node" in added_diff.path

    @pytest.mark.unit
    def test_modified_node_detected(self):
        """Modified nodes should be counted and have differences listed."""
        git_nodes = [
            {"name": "HTTP", "type": "n8n-nodes-base.httpRequest", "parameters": {"url": "old.com"}},
        ]
        runtime_nodes = [
            {"name": "HTTP", "type": "n8n-nodes-base.httpRequest", "parameters": {"url": "new.com"}},
        ]

        differences, summary = compare_nodes(git_nodes, runtime_nodes)

        assert summary.nodes_modified == 1


class TestCompareConnections:
    """Tests for comparing workflow connections."""

    @pytest.mark.unit
    def test_identical_connections_no_drift(self):
        """Identical connections should have no drift."""
        connections = {
            "Start": {"main": [[{"node": "HTTP", "type": "main", "index": 0}]]},
        }

        differences, changed = compare_connections(connections, connections)

        assert differences == []
        assert changed is False

    @pytest.mark.unit
    def test_different_connections_detected(self):
        """Different connections should be detected."""
        git_connections = {
            "Start": {"main": [[{"node": "HTTP", "type": "main", "index": 0}]]},
        }
        runtime_connections = {
            "Start": {"main": [[{"node": "Set", "type": "main", "index": 0}]]},
        }

        differences, changed = compare_connections(git_connections, runtime_connections)

        assert changed is True
        assert len(differences) == 1
        assert differences[0].path == "connections"

    @pytest.mark.unit
    def test_empty_connections_no_drift(self):
        """Empty connections on both sides should have no drift."""
        differences, changed = compare_connections({}, {})
        assert changed is False

    @pytest.mark.unit
    def test_none_connections_no_drift(self):
        """None connections on both sides should have no drift."""
        differences, changed = compare_connections(None, None)
        assert changed is False


class TestCompareSettings:
    """Tests for comparing workflow settings."""

    @pytest.mark.unit
    def test_identical_settings_no_drift(self):
        """Identical settings should have no drift."""
        settings = {"saveExecutionProgress": True, "saveManualExecutions": False}

        differences, changed = compare_settings(settings, settings)

        assert differences == []
        assert changed is False

    @pytest.mark.unit
    def test_different_settings_detected(self):
        """Changed settings should be detected."""
        git_settings = {"saveExecutionProgress": True}
        runtime_settings = {"saveExecutionProgress": False}

        differences, changed = compare_settings(git_settings, runtime_settings)

        assert changed is True
        assert len(differences) == 1
        assert "saveExecutionProgress" in differences[0].path

    @pytest.mark.unit
    def test_added_setting_detected(self):
        """New settings in runtime should be detected."""
        git_settings = {"existingSetting": True}
        runtime_settings = {"existingSetting": True, "newSetting": "value"}

        differences, changed = compare_settings(git_settings, runtime_settings)

        assert changed is True
        new_diff = next((d for d in differences if "newSetting" in d.path), None)
        assert new_diff is not None


class TestCompareWorkflows:
    """Tests for the main compare_workflows function."""

    @pytest.mark.unit
    def test_no_git_version_returns_no_drift(self):
        """If no git version exists, should return no drift."""
        runtime = {"name": "Test", "active": True, "nodes": [], "connections": {}}

        result = compare_workflows(None, runtime)

        assert result.has_drift is False
        assert result.git_version is None
        assert result.runtime_version == runtime
        assert result.differences == []

    @pytest.mark.unit
    def test_identical_workflows_no_drift(self):
        """Identical workflows should have no drift."""
        workflow = {
            "name": "Test Workflow",
            "active": True,
            "nodes": [{"name": "Start", "type": "n8n-nodes-base.start"}],
            "connections": {},
            "settings": {},
        }

        result = compare_workflows(workflow, workflow)

        assert result.has_drift is False
        assert result.differences == []
        assert result.summary.nodes_added == 0
        assert result.summary.nodes_removed == 0
        assert result.summary.nodes_modified == 0
        assert result.summary.connections_changed is False
        assert result.summary.settings_changed is False

    @pytest.mark.unit
    def test_name_change_detected(self):
        """Workflow name changes should be detected."""
        git = {"name": "Old Name", "active": True, "nodes": [], "connections": {}}
        runtime = {"name": "New Name", "active": True, "nodes": [], "connections": {}}

        result = compare_workflows(git, runtime)

        assert result.has_drift is True
        name_diff = next((d for d in result.differences if d.path == "name"), None)
        assert name_diff is not None
        assert name_diff.git_value == "Old Name"
        assert name_diff.runtime_value == "New Name"

    @pytest.mark.unit
    def test_active_state_change_detected(self):
        """Active state changes should be detected."""
        git = {"name": "Test", "active": False, "nodes": [], "connections": {}}
        runtime = {"name": "Test", "active": True, "nodes": [], "connections": {}}

        result = compare_workflows(git, runtime)

        assert result.has_drift is True
        active_diff = next((d for d in result.differences if d.path == "active"), None)
        assert active_diff is not None
        assert active_diff.git_value is False
        assert active_diff.runtime_value is True

    @pytest.mark.unit
    def test_commit_info_preserved(self):
        """Commit SHA and date should be preserved in result."""
        git = {"name": "Test", "active": True, "nodes": [], "connections": {}}
        runtime = {"name": "Test", "active": True, "nodes": [], "connections": {}}

        result = compare_workflows(
            git, runtime,
            last_commit_sha="abc123",
            last_commit_date="2024-01-15T10:00:00Z"
        )

        assert result.last_commit_sha == "abc123"
        assert result.last_commit_date == "2024-01-15T10:00:00Z"

    @pytest.mark.unit
    def test_to_dict_serialization(self):
        """DriftResult.to_dict should serialize correctly."""
        git = {"name": "Test", "active": True, "nodes": [], "connections": {}}
        runtime = {"name": "New", "active": True, "nodes": [], "connections": {}}

        result = compare_workflows(git, runtime, "sha123", "2024-01-15")
        dict_result = result.to_dict()

        assert dict_result["hasDrift"] is True
        assert dict_result["lastCommitSha"] == "sha123"
        assert dict_result["lastCommitDate"] == "2024-01-15"
        assert isinstance(dict_result["differences"], list)
        assert isinstance(dict_result["summary"], dict)


class TestIgnoredFields:
    """Tests for field ignoring behavior."""

    @pytest.mark.unit
    def test_ignored_fields_are_defined(self):
        """Verify expected fields are in IGNORED_FIELDS."""
        expected_ignored = ["id", "createdAt", "updatedAt", "versionId", "meta", "staticData"]
        for field in expected_ignored:
            assert field in IGNORED_FIELDS

    @pytest.mark.unit
    def test_ignored_node_fields_are_defined(self):
        """Verify expected node fields are in IGNORED_NODE_FIELDS."""
        expected_ignored = ["id", "webhookId", "notesInFlow"]
        for field in expected_ignored:
            assert field in IGNORED_NODE_FIELDS
