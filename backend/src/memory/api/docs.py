"""
OpenAPI documentation configuration for memory service endpoints.
"""

from typing import Dict, Any

# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "memory",
        "description": "Conversational memory service operations including context management, search, and privacy controls.",
    },
    {
        "name": "chat",
        "description": "Chat operations with optional memory integration.",
    }
]

# OpenAPI documentation
openapi_description = """
## Conversational Memory API

This API provides comprehensive conversational memory capabilities including:

### Core Features
- **Conversation Storage**: Store and manage conversation history
- **Context Retrieval**: Get relevant context for ongoing conversations
- **Search**: Full-text and semantic search through conversation history
- **Privacy Controls**: User data management and privacy settings
- **Data Export**: Complete user data export functionality

### Memory Service Endpoints

#### Conversation Management
- `POST /memory/conversations` - Store a complete conversation
- `GET /memory/context/{user_id}` - Retrieve conversation context

#### Search and Discovery
- `POST /memory/search` - Search conversation history with filters

#### Privacy and Data Control
- `DELETE /memory/users/{user_id}/data` - Delete user data
- `GET /memory/users/{user_id}/export` - Export user data
- `PUT /memory/users/{user_id}/privacy` - Update privacy settings
- `GET /memory/users/{user_id}/privacy` - Get privacy settings

#### System Health
- `GET /memory/health` - Check service health status

### Authentication
Currently, the API uses user_id as a simple identifier. In production, this should be replaced with proper authentication and authorization mechanisms.

### Error Handling
All endpoints return standardized error responses with appropriate HTTP status codes:
- `400` - Bad Request (validation errors)
- `403` - Forbidden (permission errors)
- `404` - Not Found (resource not found)
- `500` - Internal Server Error (system errors)
- `503` - Service Unavailable (service initialization issues)

### Data Models
The API uses Pydantic models for request/response validation with comprehensive data validation and serialization.
"""

# Example responses for documentation
example_responses: Dict[str, Dict[str, Any]] = {
    "store_conversation": {
        "201": {
            "description": "Conversation stored successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Conversation stored successfully",
                        "conversation_id": "123e4567-e89b-12d3-a456-426614174000"
                    }
                }
            }
        }
    },
    "retrieve_context": {
        "200": {
            "description": "Context retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "context": {
                            "user_id": "user123",
                            "recent_messages": [],
                            "relevant_history": [],
                            "context_summary": "Previous conversation about API development",
                            "total_context_tokens": 150
                        },
                        "message": "Context retrieved successfully"
                    }
                }
            }
        }
    },
    "search_history": {
        "200": {
            "description": "Search completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "results": [
                            {
                                "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                                "relevance_score": 0.95,
                                "timestamp": "2024-01-15T10:30:00Z",
                                "content_snippet": "Discussion about API development...",
                                "highlights": [],
                                "topics": ["API", "development"]
                            }
                        ],
                        "total_count": 1,
                        "has_more": False,
                        "message": "Search completed successfully"
                    }
                }
            }
        }
    },
    "health_check": {
        "200": {
            "description": "Health check completed",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "components": {
                            "storage": "healthy",
                            "context_manager": "healthy",
                            "preference_engine": "healthy",
                            "search_service": "healthy",
                            "privacy_controller": "healthy"
                        },
                        "initialized": True,
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        }
    }
}