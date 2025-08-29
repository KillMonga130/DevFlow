"""
Data export service for comprehensive user data exports.
"""

import json
import csv
import logging
from io import StringIO
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from ..models import UserDataExport, Conversation, UserPreferences, PrivacySettings
from ..services.storage_layer import StorageLayer
from ..config import get_memory_config

logger = logging.getLogger(__name__)


class DataExportService:
    """Service for exporting user data in various formats."""
    
    def __init__(self, storage_layer: Optional[StorageLayer] = None):
        """Initialize the data export service."""
        self._storage = storage_layer or StorageLayer()
        self._config = get_memory_config()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the data export service."""
        if not self._initialized:
            await self._storage.initialize()
            self._initialized = True
    
    async def export_user_data(
        self, 
        user_id: str, 
        format_type: str = "json",
        include_metadata: bool = True
    ) -> UserDataExport:
        """Export complete user data with enhanced formatting."""
        await self._ensure_initialized()
        
        await self._audit_export_request(user_id, format_type)
        
        try:
            # Gather all user data
            conversations = await self._get_formatted_conversations(user_id)
            preferences = await self._get_formatted_preferences(user_id)
            privacy_settings = await self._get_formatted_privacy_settings(user_id)
            search_history = await self._get_formatted_search_history(user_id)
            
            # Create comprehensive metadata
            metadata = await self._generate_export_metadata(
                user_id, conversations, preferences, privacy_settings, search_history
            ) if include_metadata else {}
            
            # Create export object
            export = UserDataExport(
                user_id=user_id,
                conversations=conversations,
                preferences=preferences,
                privacy_settings=privacy_settings,
                search_history=search_history,
                metadata=metadata
            )
            
            await self._audit_export_completion(user_id, export)
            
            return export
            
        except Exception as e:
            await self._audit_export_failure(user_id, str(e))
            raise
    
    async def export_to_json(self, user_id: str, pretty_print: bool = True) -> str:
        """Export user data as JSON string."""
        export = await self.export_user_data(user_id, "json")
        
        if pretty_print:
            return json.dumps(export.model_dump(), indent=2, default=self._json_serializer)
        else:
            return json.dumps(export.model_dump(), default=self._json_serializer)
    
    async def export_conversations_to_csv(self, user_id: str) -> str:
        """Export conversations as CSV format."""
        await self._ensure_initialized()
        
        conversations = await self._storage.get_user_conversations(user_id)
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'conversation_id', 'timestamp', 'message_id', 'role', 
            'content', 'message_timestamp', 'tags', 'summary'
        ])
        
        # Write conversation data
        for conv in conversations:
            for msg in conv.messages:
                writer.writerow([
                    conv.id,
                    conv.timestamp.isoformat(),
                    msg.id,
                    msg.role,
                    msg.content,
                    msg.timestamp.isoformat(),
                    ','.join(conv.tags) if conv.tags else '',
                    conv.summary or ''
                ])
        
        await self._audit_export_completion(user_id, {"format": "csv", "type": "conversations"})
        
        return output.getvalue()
    
    async def export_preferences_to_json(self, user_id: str) -> str:
        """Export user preferences as JSON."""
        await self._ensure_initialized()
        
        preferences = await self._storage.get_user_preferences(user_id)
        if not preferences:
            return json.dumps({"user_id": user_id, "preferences": None})
        
        return json.dumps(preferences.model_dump(), indent=2, default=self._json_serializer)
    
    async def create_data_package(self, user_id: str) -> Dict[str, str]:
        """Create a complete data package with multiple formats."""
        await self._ensure_initialized()
        
        package = {}
        
        # JSON export (complete data)
        package["complete_data.json"] = await self.export_to_json(user_id)
        
        # CSV export (conversations only)
        package["conversations.csv"] = await self.export_conversations_to_csv(user_id)
        
        # JSON export (preferences only)
        package["preferences.json"] = await self.export_preferences_to_json(user_id)
        
        # Privacy settings
        privacy_settings = await self._storage.get_privacy_settings(user_id)
        if privacy_settings:
            package["privacy_settings.json"] = json.dumps(
                privacy_settings.model_dump(), 
                indent=2, 
                default=self._json_serializer
            )
        
        # Export summary (create after all other files are added)
        export_summary = {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "files_included": list(package.keys()) + ["export_summary.json"],  # Include self in the list
            "export_version": "1.0"
        }
        package["export_summary.json"] = json.dumps(export_summary, indent=2)
        
        await self._audit_export_completion(user_id, {"format": "package", "files": len(package)})
        
        return package
    
    async def _get_formatted_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get conversations formatted for export."""
        conversations = await self._storage.get_user_conversations(user_id)
        
        formatted_conversations = []
        for conv in conversations:
            conv_dict = conv.model_dump()
            
            # Add computed fields
            conv_dict["message_count"] = len(conv.messages)
            conv_dict["duration_minutes"] = self._calculate_conversation_duration(conv)
            conv_dict["participant_roles"] = list(set(msg.role for msg in conv.messages))
            
            formatted_conversations.append(conv_dict)
        
        return formatted_conversations
    
    async def _get_formatted_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user preferences formatted for export."""
        preferences = await self._storage.get_user_preferences(user_id)
        if not preferences:
            return None
        
        prefs_dict = preferences.model_dump()
        
        # Add computed fields
        prefs_dict["total_topics"] = len(preferences.topic_interests)
        prefs_dict["has_communication_preferences"] = preferences.communication_preferences is not None
        
        return prefs_dict
    
    async def _get_formatted_privacy_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get privacy settings formatted for export."""
        settings = await self._storage.get_privacy_settings(user_id)
        if not settings:
            return None
        
        settings_dict = settings.model_dump()
        
        # Add computed fields
        settings_dict["memory_enabled"] = settings.is_memory_enabled()
        settings_dict["long_term_storage_allowed"] = settings.allows_long_term_storage()
        
        return settings_dict
    
    async def _get_formatted_search_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get search history formatted for export."""
        # This would integrate with search service to get actual search history
        # For now, return empty list as placeholder
        return []
    
    async def _generate_export_metadata(
        self, 
        user_id: str, 
        conversations: List[Dict[str, Any]],
        preferences: Optional[Dict[str, Any]],
        privacy_settings: Optional[Dict[str, Any]],
        search_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate comprehensive metadata for the export."""
        
        # Calculate conversation statistics
        total_messages = sum(conv.get("message_count", 0) for conv in conversations)
        total_duration = sum(conv.get("duration_minutes", 0) for conv in conversations)
        
        # Get date range
        conversation_dates = []
        for conv in conversations:
            if conv.get("timestamp"):
                timestamp = conv["timestamp"]
                if isinstance(timestamp, str):
                    # Handle ISO format strings
                    timestamp = timestamp.replace("Z", "+00:00")
                    conversation_dates.append(datetime.fromisoformat(timestamp))
                elif isinstance(timestamp, datetime):
                    conversation_dates.append(timestamp)
        
        earliest_date = min(conversation_dates) if conversation_dates else None
        latest_date = max(conversation_dates) if conversation_dates else None
        
        # Collect all tags
        all_tags = set()
        for conv in conversations:
            if conv.get("tags"):
                all_tags.update(conv["tags"])
        
        metadata = {
            "export_info": {
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "export_version": "1.0",
                "user_id": user_id
            },
            "data_summary": {
                "total_conversations": len(conversations),
                "total_messages": total_messages,
                "total_conversation_duration_minutes": total_duration,
                "has_preferences": preferences is not None,
                "has_privacy_settings": privacy_settings is not None,
                "search_history_entries": len(search_history)
            },
            "date_range": {
                "earliest_conversation": earliest_date.isoformat() if earliest_date else None,
                "latest_conversation": latest_date.isoformat() if latest_date else None,
                "span_days": (latest_date - earliest_date).days if earliest_date and latest_date else 0
            },
            "content_analysis": {
                "unique_tags": sorted(list(all_tags)),  # Sort for consistent ordering
                "tag_count": len(all_tags),
                "average_messages_per_conversation": total_messages / len(conversations) if conversations else 0,
                "average_conversation_duration_minutes": total_duration / len(conversations) if conversations else 0
            },
            "privacy_info": {
                "data_anonymized": False,  # Would be True if anonymization was applied
                "export_includes_sensitive_data": True,
                "retention_policy": privacy_settings.get("data_retention_policy") if privacy_settings else None
            }
        }
        
        return metadata
    
    def _calculate_conversation_duration(self, conversation: Conversation) -> float:
        """Calculate conversation duration in minutes."""
        if len(conversation.messages) < 2:
            return 0.0
        
        first_message = min(conversation.messages, key=lambda m: m.timestamp)
        last_message = max(conversation.messages, key=lambda m: m.timestamp)
        
        duration = last_message.timestamp - first_message.timestamp
        return duration.total_seconds() / 60.0
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    async def _audit_export_request(self, user_id: str, format_type: str) -> None:
        """Audit log for export request."""
        if not self._config.audit_logging_enabled:
            return
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "operation": "DATA_EXPORT_REQUEST",
            "details": f"Format: {format_type}",
            "source": "data_export_service"
        }
        
        logger.info(f"AUDIT: {json.dumps(audit_entry)}")
    
    async def _audit_export_completion(self, user_id: str, export_info: Union[UserDataExport, Dict[str, Any]]) -> None:
        """Audit log for successful export completion."""
        if not self._config.audit_logging_enabled:
            return
        
        if isinstance(export_info, UserDataExport):
            details = f"Exported {len(export_info.conversations)} conversations"
        else:
            details = f"Export completed: {export_info}"
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "operation": "DATA_EXPORT_COMPLETED",
            "details": details,
            "source": "data_export_service"
        }
        
        logger.info(f"AUDIT: {json.dumps(audit_entry)}")
    
    async def _audit_export_failure(self, user_id: str, error: str) -> None:
        """Audit log for export failure."""
        if not self._config.audit_logging_enabled:
            return
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "operation": "DATA_EXPORT_FAILED",
            "details": f"Error: {error}",
            "source": "data_export_service"
        }
        
        logger.error(f"AUDIT: {json.dumps(audit_entry)}")
    
    async def _ensure_initialized(self) -> None:
        """Ensure the service is initialized."""
        if not self._initialized:
            await self.initialize()