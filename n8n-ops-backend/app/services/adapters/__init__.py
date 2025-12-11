"""Provider adapters package.

This package contains adapter implementations for different workflow providers.
Each adapter wraps a provider-specific client to conform to the ProviderAdapter protocol.
"""
from app.services.adapters.n8n_adapter import N8NProviderAdapter

__all__ = ["N8NProviderAdapter"]
