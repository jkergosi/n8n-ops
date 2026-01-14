"""Provider adapter protocol defining the interface for workflow providers.

This module defines the ProviderAdapter Protocol that all provider implementations
must implement. The protocol ensures consistent behavior across different
workflow automation platforms.
"""
from typing import Protocol, List, Dict, Any, runtime_checkable


@runtime_checkable
class ProviderAdapter(Protocol):
    """Protocol defining the interface for workflow provider adapters.

    All provider implementations must implement these methods to ensure
    consistent behavior across different workflow automation platforms.

    Adapters are instantiated with environment-specific configuration:
        adapter = N8NProviderAdapter(base_url="...", api_key="...")

    All methods are async to support non-blocking I/O operations.
    """

    # =========================================================================
    # Workflow Operations
    # =========================================================================

    async def get_workflows(self) -> List[Dict[str, Any]]:
        """Fetch all workflows from the provider.

        Returns:
            List of workflow dictionaries containing workflow metadata and definition
        """
        ...

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get a specific workflow by ID.

        Args:
            workflow_id: The provider's workflow identifier

        Returns:
            Workflow dictionary containing full workflow definition
        """
        ...

    async def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow in the provider.

        Args:
            workflow_data: Workflow definition including name, nodes, connections, etc.

        Returns:
            Created workflow with provider-assigned ID
        """
        ...

    async def update_workflow(
        self, workflow_id: str, workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing workflow.

        Args:
            workflow_id: The provider's workflow identifier
            workflow_data: Updated workflow definition

        Returns:
            Updated workflow definition
        """
        ...

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow from the provider.

        Args:
            workflow_id: The provider's workflow identifier

        Returns:
            True if deletion was successful
        """
        ...

    async def activate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Activate a workflow (enable it to run on triggers).

        Args:
            workflow_id: The provider's workflow identifier

        Returns:
            Updated workflow definition with active status
        """
        ...

    async def deactivate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Deactivate a workflow (disable triggers).

        Args:
            workflow_id: The provider's workflow identifier

        Returns:
            Updated workflow definition with inactive status
        """
        ...

    # =========================================================================
    # Execution Operations
    # =========================================================================

    async def get_executions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch recent workflow executions from the provider.

        Args:
            limit: Maximum number of executions to return

        Returns:
            List of execution records with status, timing, and metadata
        """
        ...

    # =========================================================================
    # Credential Operations
    # =========================================================================

    async def get_credentials(self) -> List[Dict[str, Any]]:
        """Fetch all credentials from the provider.

        Returns:
            List of credential metadata (not including secret data)
        """
        ...

    async def get_credential(self, credential_id: str) -> Dict[str, Any]:
        """Get a specific credential by ID.

        Args:
            credential_id: The provider's credential identifier

        Returns:
            Credential metadata (not including secret data)
        """
        ...

    async def create_credential(self, credential_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new credential in the provider.

        Args:
            credential_data: Credential definition including name, type, and data

        Returns:
            Created credential metadata with provider-assigned ID
        """
        ...

    async def update_credential(
        self, credential_id: str, credential_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing credential.

        Args:
            credential_id: The provider's credential identifier
            credential_data: Updated credential data

        Returns:
            Updated credential metadata
        """
        ...

    async def delete_credential(self, credential_id: str) -> bool:
        """Delete a credential from the provider.

        Args:
            credential_id: The provider's credential identifier

        Returns:
            True if deletion was successful
        """
        ...

    async def get_credential_types(self) -> List[Dict[str, Any]]:
        """Get available credential types/schemas from the provider.

        Returns:
            List of credential type definitions with field schemas
        """
        ...

    async def test_credential(self, credential_id: str) -> Dict[str, Any]:
        """Test a credential by making a lightweight API call.

        This method verifies that the credential is valid and can successfully
        authenticate/authorize with the provider. The test should be a lightweight
        operation (e.g., GET /me, GET /profile) rather than a heavy operation.

        Args:
            credential_id: The provider's credential identifier

        Returns:
            Dictionary with test result:
            {
                "success": bool,
                "error": Optional[str],
                "expiration_info": Optional[Dict[str, Any]]  # e.g., {"expires_at": "...", "days_until_expiry": 30}
            }

        If the provider does not support credential testing, return:
            {
                "success": False,
                "error": "Provider does not support credential testing",
                "status": "unsupported"
            }
        """
        ...

    # =========================================================================
    # User Operations
    # =========================================================================

    async def get_users(self) -> List[Dict[str, Any]]:
        """Fetch all users from the provider instance.

        Returns:
            List of user records from the provider
        """
        ...

    # =========================================================================
    # Tag Operations
    # =========================================================================

    async def get_tags(self) -> List[Dict[str, Any]]:
        """Fetch all tags from the provider.

        Returns:
            List of tag records
        """
        ...

    async def update_workflow_tags(
        self, workflow_id: str, tag_ids: List[str]
    ) -> Dict[str, Any]:
        """Update tags assigned to a workflow.

        Args:
            workflow_id: The provider's workflow identifier
            tag_ids: List of tag IDs to assign to the workflow

        Returns:
            Updated workflow with new tag assignments
        """
        ...

    # =========================================================================
    # Connection and Health
    # =========================================================================

    async def test_connection(self) -> bool:
        """Test if the provider instance is reachable and credentials are valid.

        Returns:
            True if connection is successful, False otherwise
        """
        ...

    # =========================================================================
    # Credential Extraction (Provider-specific workflow parsing)
    # =========================================================================

    @staticmethod
    def extract_logical_credentials(workflow: Dict[str, Any]) -> List[str]:
        """Extract logical credential keys from a workflow definition.

        Parses the workflow structure to identify all credentials referenced
        by nodes, returning them in a provider-agnostic format.

        Args:
            workflow: The workflow definition dictionary from the provider

        Returns:
            List of logical credential keys in format "type:name"
        """
        ...

    @staticmethod
    def rewrite_credentials_with_mappings(
        workflow: Dict[str, Any],
        mapping_lookup: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Rewrite workflow credential references using mapping lookup.

        Transforms credential references in a workflow to point to target
        environment credentials based on the provided mapping.

        Args:
            workflow: The workflow definition to transform
            mapping_lookup: Dict keyed by logical_key (type:name) with mapping info

        Returns:
            Transformed workflow with updated credential references
        """
        ...
