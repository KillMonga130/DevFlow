"""
Unit tests for API request and response models.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from src.memory.api.models import (
    StoreConversationRequest, RetrieveContextRequest, SearchHistoryRequest,
    DeleteUserDataRequest, ExportUserDataRequest, UpdatePrivacySettingsRequest,
    StoreConversationResponse, RetrieveContextResponse, SearchHistoryResponse,
    DeleteUserDataResponse, ExportUserDataResponse, UpdatePrivacySettingsResponse,
    HealthCheckResponse, ErrorResponse
)
from src.memory.models import (
    Conversation, Message, MessageRole, ConversationContext,
    SearchResult, DeleteOptions, UserDataExport, PrivacySettings
)


class TestStoreConversationRequest:
    """Test cases for StoreConversationRequest model."""
    
    @pytest.fixture
    def sample_conversation(self):
        """Create a sample conversation for testing."""
        message = Message(
            id="msg1",
            role=MessageRole.USER,
            content="Test message",
            timestamp=datetime.now(timezone.utc)
        )
        
        return Conversation(
            id="conv123",
            user_id="user123",
            messages=[message],
            timestamp=datetime.now(timezone.utc)
        )
    
    def test_valid_request(self, sample_conversation):
        """Test creating a valid store conversation request."""
        request = StoreConversationRequest(conversation=sample_conversation)
        
        assert request.conversation == sample_conversation
        assert request.conversation.id == "conv123"
        assert request.conversation.user_id == "user123"
    
    def test_missing_conversation(self):
        """Test that missing conversation raises validation error."""
        with pytest.raises(ValidationError):
            StoreConversationRequest()
    
    def test_invalid_conversation_type(self):
        """Test that invalid conversation type raises validation error."""
        with pytest.raises(ValidationError):
            StoreConversationRequest(conversation="invalid")


class TestRetrieveContextRequest:
    """Test cases for RetrieveContextRequest model."""
    
    def test_valid_request_with_limit(self):
        """Test creating a valid retrieve context request with limit."""
        request = RetrieveContextRequest(user_id="user123", limit=50)
        
        assert request.user_id == "user123"
        assert request.limit == 50
    
    def test_valid_request_without_limit(self):
        """Test creating a valid retrieve context request without limit."""
        request = RetrieveContextRequest(user_id="user123")
        
        assert request.user_id == "user123"
        assert request.limit is None
    
    def test_missing_user_id(self):
        """Test that missing user_id raises validation error."""
        with pytest.raises(ValidationError):
            RetrieveContextRequest()
    
    def test_invalid_limit_too_low(self):
        """Test that limit below minimum raises validation error."""
        with pytest.raises(ValidationError):
            RetrieveContextRequest(user_id="user123", limit=0)
    
    def test_invalid_limit_too_high(self):
        """Test that limit above maximum raises validation error."""
        with pytest.raises(ValidationError):
            RetrieveContextRequest(user_id="user123", limit=101)
    
    def test_empty_user_id(self):
        """Test that empty user_id raises validation error."""
        with pytest.raises(ValidationError):
            RetrieveContextRequest(user_id="")


class TestSearchHistoryRequest:
    """Test cases for SearchHistoryRequest model."""
    
    def test_valid_minimal_request(self):
        """Test creating a valid minimal search request."""
        request = SearchHistoryRequest(user_id="user123")
        
        assert request.user_id == "user123"
        assert request.keywords is None
        assert request.date_range_start is None
        assert request.date_range_end is None
        assert request.topics is None
        assert request.limit == 20  # default
        assert request.offset == 0  # default
        assert request.include_context is True  # default
        assert request.semantic_search is False  # default
    
    def test_valid_full_request(self):
        """Test creating a valid full search request."""
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
        
        request = SearchHistoryRequest(
            user_id="user123",
            keywords=["test", "search"],
            date_range_start=start_date,
            date_range_end=end_date,
            topics=["topic1", "topic2"],
            limit=50,
            offset=10,
            include_context=False,
            semantic_search=True
        )
        
        assert request.user_id == "user123"
        assert request.keywords == ["test", "search"]
        assert request.date_range_start == start_date
        assert request.date_range_end == end_date
        assert request.topics == ["topic1", "topic2"]
        assert request.limit == 50
        assert request.offset == 10
        assert request.include_context is False
        assert request.semantic_search is True
    
    def test_to_search_query_conversion(self):
        """Test conversion to SearchQuery model."""
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
        
        request = SearchHistoryRequest(
            user_id="user123",
            keywords=["test"],
            date_range_start=start_date,
            date_range_end=end_date,
            topics=["topic1"],
            limit=30,
            offset=5
        )
        
        search_query = request.to_search_query()
        
        assert search_query.user_id == "user123"
        assert search_query.keywords == ["test"]
        assert search_query.date_range.start_date == start_date
        assert search_query.date_range.end_date == end_date
        assert search_query.topics == ["topic1"]
        assert search_query.limit == 30
        assert search_query.offset == 5
    
    def test_to_search_query_no_date_range(self):
        """Test conversion to SearchQuery without date range."""
        request = SearchHistoryRequest(
            user_id="user123",
            keywords=["test"]
        )
        
        search_query = request.to_search_query()
        
        assert search_query.user_id == "user123"
        assert search_query.keywords == ["test"]
        assert search_query.date_range is None
    
    def test_invalid_limit_values(self):
        """Test invalid limit values."""
        with pytest.raises(ValidationError):
            SearchHistoryRequest(user_id="user123", limit=0)
        
        with pytest.raises(ValidationError):
            SearchHistoryRequest(user_id="user123", limit=101)
    
    def test_invalid_offset_value(self):
        """Test invalid offset value."""
        with pytest.raises(ValidationError):
            SearchHistoryRequest(user_id="user123", offset=-1)
    
    def test_empty_keywords_list(self):
        """Test empty keywords list is valid."""
        request = SearchHistoryRequest(user_id="user123", keywords=[])
        assert request.keywords == []
    
    def test_empty_topics_list(self):
        """Test empty topics list is valid."""
        request = SearchHistoryRequest(user_id="user123", topics=[])
        assert request.topics == []


class TestDeleteUserDataRequest:
    """Test cases for DeleteUserDataRequest model."""
    
    def test_valid_request_minimal(self):
        """Test creating a valid minimal delete request."""
        request = DeleteUserDataRequest(user_id="user123")
        
        assert request.user_id == "user123"
        assert request.delete_conversations is True  # default
        assert request.delete_preferences is True  # default
        assert request.delete_search_history is True  # default
        assert request.conversation_ids is None
        assert request.before_date is None
    
    def test_valid_request_full(self):
        """Test creating a valid full delete request."""
        before_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        request = DeleteUserDataRequest(
            user_id="user123",
            delete_conversations=False,
            delete_preferences=False,
            delete_search_history=False,
            conversation_ids=["conv1", "conv2"],
            before_date=before_date
        )
        
        assert request.user_id == "user123"
        assert request.delete_conversations is False
        assert request.delete_preferences is False
        assert request.delete_search_history is False
        assert request.conversation_ids == ["conv1", "conv2"]
        assert request.before_date == before_date
    
    def test_to_delete_options_conversion(self):
        """Test conversion to DeleteOptions model."""
        before_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        request = DeleteUserDataRequest(
            user_id="user123",
            delete_conversations=True,
            delete_preferences=False,
            conversation_ids=["conv1"],
            before_date=before_date
        )
        
        delete_options = request.to_delete_options()
        
        assert delete_options.scope is not None
        assert delete_options.conversation_ids == ["conv1"]
        assert delete_options.date_range_start == before_date
    
    def test_missing_user_id(self):
        """Test that missing user_id raises validation error."""
        with pytest.raises(ValidationError):
            DeleteUserDataRequest()


class TestExportUserDataRequest:
    """Test cases for ExportUserDataRequest model."""
    
    def test_valid_request_minimal(self):
        """Test creating a valid minimal export request."""
        request = ExportUserDataRequest(user_id="user123")
        
        assert request.user_id == "user123"
        assert request.format == "json"  # default
        assert request.include_conversations is True  # default
        assert request.include_preferences is True  # default
        assert request.include_search_history is False  # default
        assert request.date_range_start is None
        assert request.date_range_end is None
    
    def test_valid_request_full(self):
        """Test creating a valid full export request."""
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
        
        request = ExportUserDataRequest(
            user_id="user123",
            format="csv",
            include_conversations=False,
            include_preferences=False,
            include_search_history=True,
            date_range_start=start_date,
            date_range_end=end_date
        )
        
        assert request.user_id == "user123"
        assert request.format == "csv"
        assert request.include_conversations is False
        assert request.include_preferences is False
        assert request.include_search_history is True
        assert request.date_range_start == start_date
        assert request.date_range_end == end_date
    
    def test_invalid_format(self):
        """Test invalid export format."""
        with pytest.raises(ValidationError):
            ExportUserDataRequest(user_id="user123", format="xml")
    
    def test_valid_formats(self):
        """Test all valid export formats."""
        valid_formats = ["json", "csv", "yaml"]
        
        for format_type in valid_formats:
            request = ExportUserDataRequest(user_id="user123", format=format_type)
            assert request.format == format_type


class TestUpdatePrivacySettingsRequest:
    """Test cases for UpdatePrivacySettingsRequest model."""
    
    def test_valid_request(self):
        """Test creating a valid privacy settings request."""
        privacy_settings = PrivacySettings(
            user_id="user123",
            data_retention_days=30,
            allow_analytics=False,
            allow_personalization=True
        )
        
        request = UpdatePrivacySettingsRequest(
            user_id="user123",
            privacy_settings=privacy_settings
        )
        
        assert request.user_id == "user123"
        assert request.privacy_settings == privacy_settings
    
    def test_missing_fields(self):
        """Test that missing required fields raise validation errors."""
        with pytest.raises(ValidationError):
            UpdatePrivacySettingsRequest()
        
        with pytest.raises(ValidationError):
            UpdatePrivacySettingsRequest(user_id="user123")


class TestResponseModels:
    """Test cases for response models."""
    
    def test_store_conversation_response(self):
        """Test StoreConversationResponse model."""
        response = StoreConversationResponse(
            success=True,
            message="Conversation stored successfully",
            conversation_id="conv123"
        )
        
        assert response.success is True
        assert response.message == "Conversation stored successfully"
        assert response.conversation_id == "conv123"
    
    def test_retrieve_context_response(self):
        """Test RetrieveContextResponse model."""
        context = ConversationContext(
            user_id="user123",
            recent_messages=[],
            relevant_history=[],
            context_summary="Test context"
        )
        
        response = RetrieveContextResponse(
            success=True,
            context=context
        )
        
        assert response.success is True
        assert response.context == context
    
    def test_search_history_response(self):
        """Test SearchHistoryResponse model."""
        search_results = [
            SearchResult(
                conversation_id="conv1",
                relevance_score=0.9,
                content_snippet="Test snippet",
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        response = SearchHistoryResponse(
            success=True,
            results=search_results,
            total_count=1,
            has_more=False
        )
        
        assert response.success is True
        assert response.results == search_results
        assert response.total_count == 1
        assert response.has_more is False
    
    def test_delete_user_data_response(self):
        """Test DeleteUserDataResponse model."""
        response = DeleteUserDataResponse(
            success=True,
            message="Data deleted successfully",
            deleted_conversations=5,
            deleted_preferences=True,
            deleted_search_history=True
        )
        
        assert response.success is True
        assert response.message == "Data deleted successfully"
        assert response.deleted_conversations == 5
        assert response.deleted_preferences is True
        assert response.deleted_search_history is True
    
    def test_export_user_data_response(self):
        """Test ExportUserDataResponse model."""
        export_data = UserDataExport(
            user_id="user123",
            export_timestamp=datetime.now(timezone.utc),
            conversations=[],
            preferences=None,
            format="json"
        )
        
        response = ExportUserDataResponse(
            success=True,
            export_data=export_data,
            download_url="https://example.com/download/123"
        )
        
        assert response.success is True
        assert response.export_data == export_data
        assert response.download_url == "https://example.com/download/123"
    
    def test_update_privacy_settings_response(self):
        """Test UpdatePrivacySettingsResponse model."""
        response = UpdatePrivacySettingsResponse(
            success=True,
            message="Privacy settings updated successfully"
        )
        
        assert response.success is True
        assert response.message == "Privacy settings updated successfully"
    
    def test_health_check_response(self):
        """Test HealthCheckResponse model."""
        response = HealthCheckResponse(
            status="healthy",
            timestamp=datetime.now(timezone.utc),
            version="1.0.0",
            components={
                "database": "healthy",
                "cache": "healthy"
            }
        )
        
        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert response.components["database"] == "healthy"
        assert response.components["cache"] == "healthy"
    
    def test_error_response(self):
        """Test ErrorResponse model."""
        response = ErrorResponse(
            success=False,
            error_code="VALIDATION_ERROR",
            error_message="Invalid input data",
            details={"field": "user_id", "issue": "required"}
        )
        
        assert response.success is False
        assert response.error_code == "VALIDATION_ERROR"
        assert response.error_message == "Invalid input data"
        assert response.details == {"field": "user_id", "issue": "required"}


class TestModelValidation:
    """Test cases for model validation edge cases."""
    
    def test_request_model_serialization(self):
        """Test that request models can be serialized to JSON."""
        request = RetrieveContextRequest(user_id="user123", limit=10)
        
        json_data = request.model_dump()
        assert json_data["user_id"] == "user123"
        assert json_data["limit"] == 10
    
    def test_response_model_serialization(self):
        """Test that response models can be serialized to JSON."""
        response = StoreConversationResponse(
            success=True,
            message="Success",
            conversation_id="conv123"
        )
        
        json_data = response.model_dump()
        assert json_data["success"] is True
        assert json_data["message"] == "Success"
        assert json_data["conversation_id"] == "conv123"
    
    def test_model_deserialization(self):
        """Test that models can be created from JSON data."""
        json_data = {
            "user_id": "user123",
            "limit": 25
        }
        
        request = RetrieveContextRequest(**json_data)
        assert request.user_id == "user123"
        assert request.limit == 25
    
    def test_model_validation_with_extra_fields(self):
        """Test model behavior with extra fields."""
        json_data = {
            "user_id": "user123",
            "limit": 25,
            "extra_field": "should_be_ignored"
        }
        
        # Should create successfully, ignoring extra fields
        request = RetrieveContextRequest(**json_data)
        assert request.user_id == "user123"
        assert request.limit == 25
        assert not hasattr(request, "extra_field")


if __name__ == "__main__":
    pytest.main([__file__])