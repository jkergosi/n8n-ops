from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class WorkflowBase(BaseModel):
    name: str
    active: bool = False
    nodes: List[Dict[str, Any]] = []
    connections: Dict[str, Any] = {}
    settings: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    connections: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class WorkflowResponse(BaseModel):
    id: str
    name: str
    active: bool
    nodes: List[Dict[str, Any]]
    connections: Dict[str, Any]
    settings: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkflowUpload(BaseModel):
    """Schema for uploading workflow files"""
    workflow_data: Dict[str, Any]


class WorkflowTagsUpdate(BaseModel):
    """Schema for updating workflow tags"""
    tag_names: List[str]
