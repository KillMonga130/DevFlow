"""
FastAPI router for memory service endpoints.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from .models import (
    StoreConversationRequest, StoreConversationResponse,
    RetrieveContextRequest, RetrieveContextResponse,
    SearchHistoryRequest, SearchHistoryResponse,
    DeleteUserDataRequest, DeleteUserDataResponse,
    ExportUserDataRequest, ExportUserDataResponse,
    UpdatePrivacySettingsRequest, UpdatePrivacySettingsResponse,
    HealthCheckResponse, ErrorResponse
)
from ..models import PrivacySettings
from ..services.memory_service_factory import get_memory_service
from ..interfaces import MemoryServiceInterface

logger = logging.getLogger(__name__)

# Create the router
memory_router = APIRouter(
    prefix="/memory",
    tags=["memory"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        404: {"model": ErrorResponse, "description": "Not found"}
    }
)


async def get_memory_service_dependency() -> MemoryServiceInterface:
    """Dependency to get the memory service instance."""
    try:
        service = get_memory_service()
        await service.initialize()
        return service
    except Exception as e:
        logger.error(f"Failed to initialize memory service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memory service unavailable"
        )


def create_error_response(error: Exception, error_code: Optional[str] = None) -> JSONResponse:
    """Create a standardized error response."""
    error_response = ErrorResponse(
        error=str(error),
        error_code=error_code,
        details={"type": type(error).__name__}
    )
    
    # Determine status code based on error type
    if isinstance(error, ValueError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(error, FileNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, PermissionError):
        status_code = status.HTTP_403_FORBIDDEN
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump()
    )


@memory_router.post(
    "/conversations",
    response_model=StoreConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store a conversation",
    description="Store a complete conversation in the memory system with full processing including context updates and preference learning."
)
async def store_conversation(
    request: StoreConversationRequest,
    memory_service: MemoryServiceInterface = Depends(get_memory_service_dependency)
) -> StoreConversationResponse:
    """Store a conversation in the memory system."""
    try:
        await memory_service.store_conversation(
            request.conversation.user_id,
            request.conversation
        )
        
        return StoreConversationResponse(
            success=True,
            message="Conversation stored successfully",
            conversation_id=request.conversation.id
        )
        
    except Exception as e:
        logger.error(f"Failed to store conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store conversation: {str(e)}"
        )


@memory_router.get(
    "/context/{user_id}",
    response_model=RetrieveContextResponse,
    summary="Retrieve conversation context",
    description="Retrieve conversation context for a user including recent messages, relevant history, and user preferences."
)
async def retrieve_context(
    user_id: str,
    limit: Optional[int] = None,
    memory_service: MemoryServiceInterface = Depends(get_memory_service_dependency)
) -> RetrieveContextResponse:
    """Retrieve conversation context for a user."""
    try:
        context = await memory_service.retrieve_context(user_id, limit)
        
        return RetrieveContextResponse(
            success=True,
            context=context,
            message="Context retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to retrieve context for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve context: {str(e)}"
        )


@memory_router.post(
    "/search",
    response_model=SearchHistoryResponse,
    summary="Search conversation history",
    description="Search through conversation history using keywords, date ranges, topics, and semantic search capabilities."
)
async def search_history(
    request: SearchHistoryRequest,
    memory_service: MemoryServiceInterface = Depends(get_memory_service_dependency)
) -> SearchHistoryResponse:
    """Search through conversation history."""
    try:
        search_query = request.to_search_query()
        results = await memory_service.search_history(request.user_id, search_query)
        
        # Calculate pagination info
        total_count = len(results)
        has_more = total_count > (request.offset + request.limit)
        
        return SearchHistoryResponse(
            success=True,
            results=results,
            total_count=total_count,
            has_more=has_more,
            message="Search completed successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to search history for user {request.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search history: {str(e)}"
        )


@memory_router.delete(
    "/users/{user_id}/data",
    response_model=DeleteUserDataResponse,
    summary="Delete user data",
    description="Delete user data according to specified options including conversations, preferences, and search history."
)
async def delete_user_data(
    user_id: str,
    request: Optional[DeleteUserDataRequest] = None,
    memory_service: MemoryServiceInterface = Depends(get_memory_service_dependency)
) -> DeleteUserDataResponse:
    """Delete user data."""
    try:
        delete_options = request.delete_options if request else None
        await memory_service.delete_user_data(user_id, delete_options)
        
        return DeleteUserDataResponse(
            success=True,
            message="User data deleted successfully",
            deleted_items={"user_data": 1}  # This would be populated with actual counts
        )
        
    except Exception as e:
        logger.error(f"Failed to delete user data for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user data: {str(e)}"
        )


@memory_router.get(
    "/users/{user_id}/export",
    response_model=ExportUserDataResponse,
    summary="Export user data",
    description="Export all user data including conversations, preferences, privacy settings, and search history."
)
async def export_user_data(
    user_id: str,
    memory_service: MemoryServiceInterface = Depends(get_memory_service_dependency)
) -> ExportUserDataResponse:
    """Export all user data."""
    try:
        export_data = await memory_service.export_user_data(user_id)
        
        return ExportUserDataResponse(
            success=True,
            export_data=export_data,
            message="User data exported successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to export user data for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export user data: {str(e)}"
        )


@memory_router.put(
    "/users/{user_id}/privacy",
    response_model=UpdatePrivacySettingsResponse,
    summary="Update privacy settings",
    description="Update user privacy settings including data retention policy, privacy mode, and feature permissions."
)
async def update_privacy_settings(
    user_id: str,
    request: UpdatePrivacySettingsRequest,
    memory_service: MemoryServiceInterface = Depends(get_memory_service_dependency)
) -> UpdatePrivacySettingsResponse:
    """Update user privacy settings."""
    try:
        # Ensure the user_id in the request matches the path parameter
        if request.user_id != user_id:
            raise ValueError("User ID in request body must match path parameter")
        
        await memory_service.update_privacy_settings(user_id, request.privacy_settings)
        
        return UpdatePrivacySettingsResponse(
            success=True,
            message="Privacy settings updated successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update privacy settings for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update privacy settings: {str(e)}"
        )


@memory_router.get(
    "/users/{user_id}/privacy",
    response_model=PrivacySettings,
    summary="Get privacy settings",
    description="Retrieve current privacy settings for a user."
)
async def get_privacy_settings(
    user_id: str,
    memory_service: MemoryServiceInterface = Depends(get_memory_service_dependency)
) -> PrivacySettings:
    """Get user privacy settings."""
    try:
        settings = await memory_service.get_privacy_settings(user_id)
        return settings
        
    except Exception as e:
        logger.error(f"Failed to get privacy settings for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get privacy settings: {str(e)}"
        )


@memory_router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check",
    description="Check the health status of the memory service and all its components."
)
async def health_check(
    memory_service: MemoryServiceInterface = Depends(get_memory_service_dependency)
) -> HealthCheckResponse:
    """Perform a health check on the memory service."""
    try:
        health_status = await memory_service.health_check()
        
        return HealthCheckResponse(
            status=health_status.get("memory_service", "unknown"),
            components=health_status.get("components", {}),
            initialized=health_status.get("initialized", False)
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            components={"error": str(e)},
            initialized=False
        )


# Note: Exception handlers should be added to the main FastAPI app, not the router
# These can be added to main.py if needed:
#
# @app.exception_handler(ValueError)
# async def value_error_handler(request, exc: ValueError):
#     return create_error_response(exc, "VALIDATION_ERROR")
#
# @app.exception_handler(FileNotFoundError) 
# async def not_found_error_handler(request, exc: FileNotFoundError):
#     return create_error_response(exc, "NOT_FOUND")
#
# @app.exception_handler(PermissionError)
# async def permission_error_handler(request, exc: PermissionError):
#     return create_error_response(exc, "PERMISSION_DENIED")