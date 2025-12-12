"""N8N provider adapter wrapping the existing N8NClient.

This adapter implements the ProviderAdapter protocol for the n8n workflow
automation platform by delegating to the existing N8NClient implementation.
"""
from typing import List, Dict, Any
from app.services.n8n_client import N8NClient


class N8NProviderAdapter:
    """Provider adapter for n8n workflow automation platform.

    Wraps the existing N8NClient to conform to the ProviderAdapter protocol.
    This allows the service layer to work with n8n through a provider-agnostic
    interface.

    Example:
        adapter = N8NProviderAdapter(
            base_url="https://n8n.example.com",
            api_key="your-api-key"
        )
        workflows = await adapter.get_workflows()
    """

    def __init__(self, base_url: str, api_key: str):
        """Initialize adapter with n8n instance configuration.

        Args:
            base_url: The n8n instance base URL (e.g., "https://n8n.example.com")
            api_key: The n8n API key for authentication
        """
        self._client = N8NClient(base_url=base_url, api_key=api_key)

    # =========================================================================
    # Workflow Operations
    # =========================================================================

    async def get_workflows(self) -> List[Dict[str, Any]]:
        """Fetch all workflows from n8n."""
        return await self._client.get_workflows()

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get a specific workflow by ID."""
        return await self._client.get_workflow(workflow_id)

    async def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow in n8n."""
        return await self._client.create_workflow(workflow_data)

    async def update_workflow(
        self, workflow_id: str, workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing workflow."""
        return await self._client.update_workflow(workflow_id, workflow_data)

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow from n8n."""
        return await self._client.delete_workflow(workflow_id)

    async def activate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Activate a workflow."""
        return await self._client.activate_workflow(workflow_id)

    async def deactivate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Deactivate a workflow."""
        return await self._client.deactivate_workflow(workflow_id)

    # =========================================================================
    # Execution Operations
    # =========================================================================

    async def get_executions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch recent workflow executions from n8n."""
        return await self._client.get_executions(limit=limit)

    # =========================================================================
    # Credential Operations
    # =========================================================================

    async def get_credentials(self) -> List[Dict[str, Any]]:
        """Fetch all credentials from n8n."""
        return await self._client.get_credentials()

    async def get_credential(self, credential_id: str) -> Dict[str, Any]:
        """Get a specific credential by ID."""
        return await self._client.get_credential(credential_id)

    async def create_credential(self, credential_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new credential in n8n."""
        return await self._client.create_credential(credential_data)

    async def update_credential(
        self, credential_id: str, credential_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing credential."""
        return await self._client.update_credential(credential_id, credential_data)

    async def delete_credential(self, credential_id: str) -> bool:
        """Delete a credential from n8n."""
        return await self._client.delete_credential(credential_id)

    async def get_credential_types(self) -> List[Dict[str, Any]]:
        """Get available credential types from n8n."""
        return await self._client.get_credential_types()

    # =========================================================================
    # User Operations
    # =========================================================================

    async def get_users(self) -> List[Dict[str, Any]]:
        """Fetch all users from the n8n instance."""
        return await self._client.get_users()

    # =========================================================================
    # Tag Operations
    # =========================================================================

    async def get_tags(self) -> List[Dict[str, Any]]:
        """Fetch all tags from n8n."""
        return await self._client.get_tags()

    async def update_workflow_tags(
        self, workflow_id: str, tag_ids: List[str]
    ) -> Dict[str, Any]:
        """Update tags assigned to a workflow."""
        return await self._client.update_workflow_tags(workflow_id, tag_ids)

    # =========================================================================
    # Credential reference utilities (provider-specific)
    # =========================================================================

    @staticmethod
    def extract_logical_credentials(workflow: Dict[str, Any]) -> List[str]:
        """
        Extract logical credential keys from workflow (format: type:name).
        """
        logical_keys = set()
        nodes = workflow.get("nodes", [])
        for node in nodes:
            node_credentials = node.get("credentials", {})
            for cred_type, cred_info in node_credentials.items():
                if isinstance(cred_info, dict):
                    cred_name = cred_info.get("name", "Unknown")
                else:
                    cred_name = str(cred_info) if cred_info else "Unknown"
                logical_keys.add(f"{cred_type}:{cred_name}")
        return sorted(logical_keys)

    @staticmethod
    def rewrite_credentials_with_mappings(
        workflow: Dict[str, Any],
        mapping_lookup: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Rewrite workflow credential references using mapping_lookup keyed by logical_key (type:name).
        If mapping provides physical_credential_id, set it to 'id'; if physical_name provided, set 'name'.
        """
        nodes = workflow.get("nodes", [])
        for node in nodes:
            node_credentials = node.get("credentials", {})
            for cred_type, cred_info in list(node_credentials.items()):
                if isinstance(cred_info, dict):
                    cred_name = cred_info.get("name", "Unknown")
                else:
                    cred_name = str(cred_info) if cred_info else "Unknown"
                    cred_info = {}
                logical_key = f"{cred_type}:{cred_name}"
                mapping = mapping_lookup.get(logical_key)
                if not mapping:
                    continue

                # Apply mapped values
                physical_name = mapping.get("physical_name") or cred_name
                physical_type = mapping.get("physical_type") or cred_type
                physical_id = mapping.get("physical_credential_id")

                cred_info["name"] = physical_name
                if physical_id:
                    cred_info["id"] = physical_id

                # If type changes, rename key
                if physical_type != cred_type:
                    node_credentials.pop(cred_type, None)
                    node_credentials[physical_type] = cred_info
                else:
                    node_credentials[cred_type] = cred_info

            node["credentials"] = node_credentials

        workflow["nodes"] = nodes
        return workflow

    # =========================================================================
    # Connection and Health
    # =========================================================================

    async def test_connection(self) -> bool:
        """Test if the n8n instance is reachable."""
        return await self._client.test_connection()
