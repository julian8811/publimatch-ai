"""Task status endpoint for checking Celery async job results."""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas import TaskStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Check the status of a Celery task by its task ID.

    Returns the task's current state, and the result or error if
    the task has completed.
    """
    try:
        from app.core.celery_app import celery_app

        if celery_app is None:
            raise RuntimeError("Celery is not configured")

        async_result = celery_app.AsyncResult(task_id)

        if async_result.failed():
            try:
                result = async_result.result  # This re-raises the exception
            except Exception as exc:
                return TaskStatusResponse(
                    task_id=task_id,
                    status="FAILURE",
                    error=str(exc),
                )

        if async_result.successful():
            return TaskStatusResponse(
                task_id=task_id,
                status="SUCCESS",
                result=async_result.result,
            )

        return TaskStatusResponse(
            task_id=task_id,
            status=async_result.status,
        )

    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Celery unavailable: {e}")
    except Exception as e:
        logger.error("Failed to check task %s status: %s", task_id, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check task status: {e}",
        )
