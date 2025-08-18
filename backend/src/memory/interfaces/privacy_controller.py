"""
Privacy controller interface.
"""

from abc import ABC, abstractmethod
from typing import List
from ..models import (
    PrivacySettings, DeleteOptions, UserDataExport
)


class PrivacyControllerInterface(ABC):
    """Interface for privacy and data control functionality."""
    
    @abstractmethod
    async def delete_user_data(self, user_id: str, options: DeleteOptions) -> None:
        """Delete user data according to the specified options."""
        pass
    
    @abstractmethod
    async def export_user_data(self, user_id: str) -> UserDataExport:
        """Export all user data for download."""
        pass
    
    @abstractmethod
    async def apply_retention_policy(self, user_id: str, settings: PrivacySettings) -> None:
        """Apply data retention policy for a user."""
        pass
    
    @abstractmethod
    async def anonymize_data(self, user_id: str, conversation_ids: List[str]) -> None:
        """Anonymize specified conversations."""
        pass
    
    @abstractmethod
    async def audit_data_access(self, user_id: str, operation: str, details: str) -> None:
        """Log data access for audit purposes."""
        pass
    
    @abstractmethod
    async def check_privacy_compliance(self, user_id: str) -> bool:
        """Check if user data handling is compliant with privacy settings."""
        pass