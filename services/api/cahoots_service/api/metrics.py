"""Metrics endpoints."""
from cahoots_service.api.auth import verify_api_key
from fastapi import APIRouter, Response, Depends
from prometheus_client import (
    generate_latest,
    CONTENT_TYPE_LATEST,
)
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/")
async def get_metrics(organization_id: str = Depends(verify_api_key)) -> Response:
    """Generate Prometheus metrics response.
    
    Args:
        organization_id: Organization ID from verified API key
        
    Returns:
        Response: Prometheus metrics in text format
    """
    metrics = generate_latest()
    return Response(
        content=metrics,
        media_type=CONTENT_TYPE_LATEST
    ) 