"""Provider enum and types for provider abstraction.

This module defines the supported workflow automation providers and provides
utilities for working with provider types throughout the application.
"""
from enum import Enum
from typing import Optional


class Provider(str, Enum):
    """Supported workflow automation providers.

    Each provider represents a different workflow automation platform
    that can be integrated with the system.
    """
    N8N = "n8n"
    MAKE = "make"  # Future provider - Make.com (formerly Integromat)

    @classmethod
    def from_string(cls, value: Optional[str]) -> "Provider":
        """Convert string to Provider enum.

        Args:
            value: Provider string value (case-insensitive)

        Returns:
            Provider enum value, defaults to N8N if value is invalid or None
        """
        if not value:
            return cls.N8N
        try:
            return cls(value.lower())
        except ValueError:
            return cls.N8N

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a string is a valid provider value.

        Args:
            value: String to check

        Returns:
            True if value is a valid provider, False otherwise
        """
        try:
            cls(value.lower())
            return True
        except ValueError:
            return False

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of all supported provider values.

        Returns:
            List of provider string values
        """
        return [p.value for p in cls]


# Default provider for new entities
DEFAULT_PROVIDER = Provider.N8N
