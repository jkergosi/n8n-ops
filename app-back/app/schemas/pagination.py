"""
Standardized pagination schema models for all paginated API endpoints.

This module provides reusable Pydantic models for consistent pagination
across the n8n-ops backend API. All paginated endpoints should return
responses that conform to these schemas.

Standard Pagination Envelope:
----------------------------
All paginated endpoints return a response with:
- items: List of the actual data items (workflows, executions, etc.)
- total: Total count of items across all pages
- page: Current page number (1-indexed)
- pageSize: Number of items per page
- totalPages: Total number of pages
- hasMore: Boolean indicating if more pages exist

Default Limits:
--------------
- Default page size: 50
- Maximum page size: 100
- Minimum page size: 1

Usage Example:
-------------
from app.schemas.pagination import PaginatedResponse, PageMetadata
from app.schemas.workflow import WorkflowResponse

# In your endpoint:
@router.get("/workflows", response_model=PaginatedResponse[WorkflowResponse])
async def get_workflows(page: int = 1, page_size: int = 50):
    # ... fetch data ...
    return PaginatedResponse(
        items=workflows,
        total=total_count,
        page=page,
        pageSize=page_size,
        totalPages=total_pages,
        hasMore=has_more
    )
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, TypeVar, Generic
from math import ceil


# Default pagination constants
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1


class PageMetadata(BaseModel):
    """
    Pagination metadata for paginated responses.

    This model represents the pagination information without the actual data items.
    Use this when you need to return only metadata or when composing custom response models.

    Attributes:
        page: Current page number (1-indexed)
        pageSize: Number of items per page (capped at MAX_PAGE_SIZE)
        total: Total number of items across all pages
        totalPages: Total number of pages
        hasMore: Boolean indicating if more pages exist beyond current page
    """
    page: int = Field(default=1, ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=MIN_PAGE_SIZE,
        le=MAX_PAGE_SIZE,
        alias="pageSize",
        serialization_alias="pageSize",
        description=f"Number of items per page (default: {DEFAULT_PAGE_SIZE}, max: {MAX_PAGE_SIZE})"
    )
    total: int = Field(ge=0, description="Total number of items across all pages")
    total_pages: int = Field(
        ge=0,
        alias="totalPages",
        serialization_alias="totalPages",
        description="Total number of pages"
    )
    has_more: bool = Field(
        alias="hasMore",
        serialization_alias="hasMore",
        description="Boolean indicating if more pages exist beyond current page"
    )

    model_config = {"populate_by_name": True}

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        """Ensure page_size is within allowed bounds."""
        return max(MIN_PAGE_SIZE, min(v, MAX_PAGE_SIZE))

    @staticmethod
    def create(page: int, page_size: int, total: int) -> "PageMetadata":
        """
        Factory method to create PageMetadata with computed fields.

        Args:
            page: Current page number (1-indexed)
            page_size: Items per page (will be capped at MAX_PAGE_SIZE)
            total: Total number of items

        Returns:
            PageMetadata instance with computed totalPages and hasMore
        """
        # Ensure page_size is within bounds
        page_size = max(MIN_PAGE_SIZE, min(page_size, MAX_PAGE_SIZE))

        # Compute total pages (minimum 1 if total > 0, otherwise 0)
        total_pages = ceil(total / page_size) if total > 0 and page_size > 0 else 0

        # Determine if more pages exist
        has_more = page < total_pages

        return PageMetadata(
            page=page,
            pageSize=page_size,
            total=total,
            totalPages=total_pages,
            hasMore=has_more
        )


# Generic type for paginated items
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response envelope.

    This is the standard response structure for all paginated endpoints.
    It wraps a list of items with pagination metadata.

    Type Parameters:
        T: The type of items in the response (e.g., WorkflowResponse, ExecutionResponse)

    Attributes:
        items: List of data items for the current page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        pageSize: Number of items per page
        totalPages: Total number of pages
        hasMore: Boolean indicating if more pages exist

    Example:
        >>> from app.schemas.workflow import WorkflowResponse
        >>> response = PaginatedResponse[WorkflowResponse](
        ...     items=[workflow1, workflow2],
        ...     total=100,
        ...     page=1,
        ...     pageSize=50,
        ...     totalPages=2,
        ...     hasMore=True
        ... )
    """
    items: List[T] = Field(description="List of items for the current page")
    total: int = Field(ge=0, description="Total number of items across all pages")
    page: int = Field(default=1, ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=MIN_PAGE_SIZE,
        le=MAX_PAGE_SIZE,
        alias="pageSize",
        serialization_alias="pageSize",
        description=f"Number of items per page (default: {DEFAULT_PAGE_SIZE}, max: {MAX_PAGE_SIZE})"
    )
    total_pages: int = Field(
        ge=0,
        alias="totalPages",
        serialization_alias="totalPages",
        description="Total number of pages"
    )
    has_more: bool = Field(
        alias="hasMore",
        serialization_alias="hasMore",
        description="Boolean indicating if more pages exist"
    )

    model_config = {"populate_by_name": True}

    @staticmethod
    def create(items: List[T], page: int, page_size: int, total: int) -> "PaginatedResponse[T]":
        """
        Factory method to create a PaginatedResponse with computed fields.

        Args:
            items: List of items for the current page
            page: Current page number (1-indexed)
            page_size: Items per page (will be capped at MAX_PAGE_SIZE)
            total: Total number of items across all pages

        Returns:
            PaginatedResponse instance with computed totalPages and hasMore
        """
        # Ensure page_size is within bounds
        page_size = max(MIN_PAGE_SIZE, min(page_size, MAX_PAGE_SIZE))

        # Compute total pages (minimum 1 if total > 0, otherwise 0)
        total_pages = ceil(total / page_size) if total > 0 and page_size > 0 else 0

        # Determine if more pages exist
        has_more = page < total_pages

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            pageSize=page_size,
            totalPages=total_pages,
            hasMore=has_more
        )


class LegacyPaginatedResponse(BaseModel):
    """
    Legacy paginated response format for backward compatibility.

    Some existing endpoints return pagination data with different field names
    (e.g., 'workflows' or 'executions' instead of 'items'). This model provides
    a base class for maintaining backward compatibility while transitioning to
    the standardized format.

    DO NOT use this for new endpoints. Use PaginatedResponse[T] instead.

    Attributes:
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total_pages: Total number of pages
    """
    total: int = Field(ge=0, description="Total number of items across all pages")
    page: int = Field(default=1, ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=MIN_PAGE_SIZE,
        le=MAX_PAGE_SIZE,
        alias="pageSize",
        serialization_alias="pageSize",
        description=f"Number of items per page"
    )
    total_pages: int = Field(
        ge=0,
        alias="totalPages",
        serialization_alias="totalPages",
        description="Total number of pages"
    )

    model_config = {"populate_by_name": True}


# Pagination query parameter models for consistent endpoint definitions

class PaginationParams(BaseModel):
    """
    Standard pagination query parameters.

    Use this model with FastAPI's Depends() to inject pagination parameters
    into your endpoint functions.

    Example:
        from fastapi import Depends
        from app.schemas.pagination import PaginationParams

        @router.get("/workflows")
        async def get_workflows(
            pagination: PaginationParams = Depends()
        ):
            # Use pagination.page and pagination.page_size
            ...
    """
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=MIN_PAGE_SIZE,
        le=MAX_PAGE_SIZE,
        description=f"Items per page (default: {DEFAULT_PAGE_SIZE}, max: {MAX_PAGE_SIZE})"
    )

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        """Ensure page_size is within allowed bounds."""
        return max(MIN_PAGE_SIZE, min(v, MAX_PAGE_SIZE))
