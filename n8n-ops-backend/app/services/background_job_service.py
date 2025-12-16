"""
Background job service for managing async task execution.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import uuid4
from app.services.database import db_service

logger = logging.getLogger(__name__)


class BackgroundJobStatus:
    """Job status constants"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackgroundJobType:
    """Job type constants"""
    PROMOTION_EXECUTE = "promotion_execute"
    ENVIRONMENT_SYNC = "environment_sync"
    GITHUB_SYNC_FROM = "github_sync_from"
    GITHUB_SYNC_TO = "github_sync_to"
    RESTORE_EXECUTE = "restore_execute"
    SNAPSHOT_RESTORE = "snapshot_restore"


class BackgroundJobService:
    """Service for managing background jobs"""

    @staticmethod
    async def create_job(
        tenant_id: str,
        job_type: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        created_by: Optional[str] = None,
        initial_progress: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new background job record.
        
        Args:
            tenant_id: Tenant ID
            job_type: Type of job (use BackgroundJobType constants)
            resource_id: ID of the resource being processed (promotion_id, environment_id, etc.)
            resource_type: Type of resource ('promotion', 'environment', etc.)
            created_by: User ID who created the job
            initial_progress: Initial progress data
            
        Returns:
            Job record dictionary
        """
        job_id = str(uuid4())
        job_data = {
            "id": job_id,
            "tenant_id": tenant_id,
            "job_type": job_type,
            "status": BackgroundJobStatus.PENDING,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "created_by": created_by,
            "progress": initial_progress or {},
            "result": {},
            "error_details": {}
        }
        
        try:
            response = db_service.client.table("background_jobs").insert(job_data).execute()
            logger.info(f"Created background job {job_id} of type {job_type} for resource {resource_id}")
            return response.data[0]
        except Exception as e:
            logger.error(f"Failed to create background job: {str(e)}")
            raise

    @staticmethod
    async def update_job_status(
        job_id: str,
        status: str,
        progress: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update job status and progress.
        
        Args:
            job_id: Job ID
            status: New status (use BackgroundJobStatus constants)
            progress: Progress data (will be merged with existing)
            result: Result data (will be merged with existing)
            error_message: Error message if failed
            error_details: Detailed error information
            
        Returns:
            Updated job record
        """
        update_data: Dict[str, Any] = {"status": status}
        
        if status == BackgroundJobStatus.RUNNING:
            # Set started_at when job starts running (if not already set)
            try:
                current_job = await BackgroundJobService.get_job(job_id)
                if current_job and not current_job.get("started_at"):
                    update_data["started_at"] = datetime.utcnow().isoformat()
            except Exception:
                update_data["started_at"] = datetime.utcnow().isoformat()
        elif status in [BackgroundJobStatus.COMPLETED, BackgroundJobStatus.FAILED, BackgroundJobStatus.CANCELLED]:
            # Set completed_at when job finishes
            update_data["completed_at"] = datetime.utcnow().isoformat()
        
        if progress is not None:
            # Merge progress with existing
            try:
                current_job = await BackgroundJobService.get_job(job_id)
                current_progress = current_job.get("progress", {}) if current_job else {}
                merged_progress = {**current_progress, **progress}
                update_data["progress"] = merged_progress
            except Exception:
                update_data["progress"] = progress
        
        if result is not None:
            # Merge result with existing
            try:
                current_job = await BackgroundJobService.get_job(job_id)
                current_result = current_job.get("result", {}) if current_job else {}
                merged_result = {**current_result, **result}
                update_data["result"] = merged_result
            except Exception:
                update_data["result"] = result
        
        if error_message:
            update_data["error_message"] = error_message
        
        if error_details is not None:
            update_data["error_details"] = error_details
        
        try:
            response = db_service.client.table("background_jobs").update(update_data).eq("id", job_id).execute()
            if response.data:
                logger.debug(f"Updated job {job_id} status to {status}")
                return response.data[0]
            else:
                raise ValueError(f"Job {job_id} not found")
        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {str(e)}")
            raise

    @staticmethod
    async def get_job(job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by ID"""
        try:
            response = db_service.client.table("background_jobs").select("*").eq("id", job_id).single().execute()
            return response.data
        except Exception as e:
            logger.debug(f"Job {job_id} not found: {str(e)}")
            return None

    @staticmethod
    async def get_jobs_by_resource(
        resource_type: str,
        resource_id: str,
        tenant_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get jobs for a specific resource.
        
        Args:
            resource_type: Type of resource ('promotion', 'environment', etc.)
            resource_id: ID of the resource
            tenant_id: Optional tenant ID filter
            limit: Maximum number of jobs to return
            
        Returns:
            List of job records, ordered by created_at DESC
        """
        query = db_service.client.table("background_jobs").select("*").eq("resource_type", resource_type).eq("resource_id", resource_id)
        
        if tenant_id:
            query = query.eq("tenant_id", tenant_id)
        
        response = query.order("created_at", desc=True).limit(limit).execute()
        return response.data

    @staticmethod
    async def get_latest_job_by_resource(
        resource_type: str,
        resource_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the latest job for a specific resource"""
        jobs = await BackgroundJobService.get_jobs_by_resource(resource_type, resource_id, tenant_id, limit=1)
        return jobs[0] if jobs else None

    @staticmethod
    async def cancel_job(job_id: str) -> Dict[str, Any]:
        """Cancel a running job"""
        job = await BackgroundJobService.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.get("status") not in [BackgroundJobStatus.PENDING, BackgroundJobStatus.RUNNING]:
            raise ValueError(f"Cannot cancel job in status: {job.get('status')}")
        
        return await BackgroundJobService.update_job_status(
            job_id=job_id,
            status=BackgroundJobStatus.CANCELLED,
            error_message="Job cancelled by user"
        )

    @staticmethod
    async def update_progress(
        job_id: str,
        current: Optional[int] = None,
        total: Optional[int] = None,
        percentage: Optional[float] = None,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update job progress.
        
        Args:
            job_id: Job ID
            current: Current item number
            total: Total items
            percentage: Progress percentage (0-100)
            message: Progress message
            
        Returns:
            Updated job record
        """
        progress: Dict[str, Any] = {}
        
        if current is not None:
            progress["current"] = current
        if total is not None:
            progress["total"] = total
        if percentage is not None:
            progress["percentage"] = percentage
        if message is not None:
            progress["message"] = message
        
        # Calculate percentage if not provided but current and total are
        if "percentage" not in progress and "current" in progress and "total" in progress:
            if progress["total"] > 0:
                progress["percentage"] = round((progress["current"] / progress["total"]) * 100, 2)
        
        return await BackgroundJobService.update_job_status(job_id, BackgroundJobStatus.RUNNING, progress=progress)


# Singleton instance
background_job_service = BackgroundJobService()

