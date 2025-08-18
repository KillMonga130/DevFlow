"""
Search-related data models.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DateRange(BaseModel):
    """Date range for search queries."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    def contains(self, date: datetime) -> bool:
        """Check if a date falls within this range."""
        if self.start_date and date < self.start_date:
            return False
        if self.end_date and date > self.end_date:
            return False
        return True


class SearchQuery(BaseModel):
    """Search query parameters."""
    keywords: Optional[List[str]] = None
    date_range: Optional[DateRange] = None
    topics: Optional[List[str]] = None
    user_id: str
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    include_context: bool = True
    semantic_search: bool = False
    
    def has_filters(self) -> bool:
        """Check if query has any filters applied."""
        return bool(
            self.keywords or 
            self.date_range or 
            self.topics
        )


class SearchResultHighlight(BaseModel):
    """Highlighted text in search results."""
    field: str  # "content", "summary", etc.
    highlighted_text: str
    context_before: str = ""
    context_after: str = ""


class SearchResult(BaseModel):
    """Individual search result."""
    conversation_id: str
    message_id: Optional[str] = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    timestamp: datetime
    content_snippet: str
    highlights: List[SearchResultHighlight] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_highlight(self, field: str, text: str, before: str = "", after: str = "") -> None:
        """Add a highlight to the search result."""
        self.highlights.append(SearchResultHighlight(
            field=field,
            highlighted_text=text,
            context_before=before,
            context_after=after
        ))