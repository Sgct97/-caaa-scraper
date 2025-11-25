#!/usr/bin/env python3
"""
Search Parameters Data Structure for CAAA Listserv Search

This module defines all available search parameters and provides
a clean interface for building search queries.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
from datetime import date

@dataclass
class SearchParams:
    """
    Complete search parameters for CAAA listserv search
    
    All fields are optional. If not specified, defaults to "search all".
    """
    
    # ============================================================
    # BASIC TEXT SEARCH FIELDS
    # ============================================================
    
    # Simple keyword search (searches both subject and body by default)
    keyword: Optional[str] = None
    """Simple keyword search - most common field used"""
    
    # ============================================================
    # ADVANCED KEYWORD SEARCH FIELDS
    # ============================================================
    
    keywords_all: Optional[str] = None
    """Must contain ALL of these keywords (space-separated)"""
    
    keywords_phrase: Optional[str] = None
    """Exact phrase match (e.g., 'permanent disability')"""
    
    keywords_any: Optional[str] = None
    """Must contain at least ONE of these keywords (space-separated)"""
    
    keywords_exclude: Optional[str] = None
    """Must NOT contain any of these keywords (space-separated)"""
    
    # ============================================================
    # AUTHOR/SENDER FILTERS
    # ============================================================
    
    author_first_name: Optional[str] = None
    """Filter by author's first name"""
    
    author_last_name: Optional[str] = None
    """Filter by author's last name"""
    
    posted_by: Optional[str] = None
    """Filter by poster (email or name)"""
    
    # ============================================================
    # DATE RANGE FILTERS
    # ============================================================
    
    date_from: Optional[date] = None
    """Start date for message search (format: YYYY-MM-DD)"""
    
    date_to: Optional[date] = None
    """End date for message search (format: YYYY-MM-DD)"""
    
    # ============================================================
    # LIST/CATEGORY FILTERS
    # ============================================================
    
    listserv: Literal["all", "lamaaa", "lavaaa", "lawnet", "scaaa"] = "all"
    """Which listserv to search (default: all)"""
    
    search_in: Literal["subject_and_body", "subject_only"] = "subject_and_body"
    """Where to search for keywords (default: subject and body)"""
    
    attachment_filter: Literal["all", "with_attachments", "without_attachments"] = "all"
    """Filter by attachment presence (default: all)"""
    
    # ============================================================
    # SCRAPER CONTROL PARAMS (not sent to CAAA form)
    # ============================================================
    
    max_pages: int = 10
    """Maximum number of result pages to scrape (default: 10 = 100 messages)"""
    
    max_messages: int = 100
    """Maximum number of messages to fetch (default: 100)"""
    
    def to_form_data(self) -> dict:
        """
        Convert SearchParams to form data dictionary for Playwright
        
        Returns:
            dict: Form field names and values ready for page.fill()
        """
        form_data = {}
        
        # Basic keyword (goes in s_fname field - first name field repurposed)
        if self.keyword:
            form_data['s_fname'] = self.keyword
        
        # Author filters
        if self.author_first_name:
            form_data['s_fname'] = self.author_first_name
        if self.author_last_name:
            form_data['s_lname'] = self.author_last_name
        if self.posted_by:
            form_data['s_postedby'] = self.posted_by
        
        # Date filters (format as MM/DD/YYYY)
        if self.date_from:
            form_data['s_postdatefrom'] = self.date_from.strftime('%m/%d/%Y')
        if self.date_to:
            form_data['s_postdateto'] = self.date_to.strftime('%m/%d/%Y')
        
        # Advanced keyword filters
        if self.keywords_all:
            form_data['s_key_all'] = self.keywords_all
        if self.keywords_phrase:
            form_data['s_key_phrase'] = self.keywords_phrase
        if self.keywords_any:
            form_data['s_key_one'] = self.keywords_any
        if self.keywords_exclude:
            form_data['s_key_x'] = self.keywords_exclude
        
        # List selection
        if self.listserv != "all":
            form_data['s_list'] = self.listserv
        
        # Search category (subject only vs subject+body)
        if self.search_in == "subject_only":
            form_data['s_cat'] = '1'
        
        # Attachment filter
        if self.attachment_filter == "with_attachments":
            form_data['s_attachment'] = '1'
        elif self.attachment_filter == "without_attachments":
            form_data['s_attachment'] = '0'
        
        # Add scraper control params (not sent to CAAA form but needed by worker)
        form_data['max_messages'] = self.max_messages
        form_data['max_pages'] = self.max_pages
        
        return form_data
    
    def __str__(self) -> str:
        """Human-readable description of search parameters"""
        parts = []
        
        if self.keyword:
            parts.append(f"keyword='{self.keyword}'")
        if self.keywords_all:
            parts.append(f"all_keywords='{self.keywords_all}'")
        if self.keywords_phrase:
            parts.append(f"exact_phrase='{self.keywords_phrase}'")
        if self.keywords_any:
            parts.append(f"any_keywords='{self.keywords_any}'")
        if self.keywords_exclude:
            parts.append(f"exclude='{self.keywords_exclude}'")
        
        if self.author_first_name or self.author_last_name:
            parts.append(f"author='{self.author_first_name or ''} {self.author_last_name or ''}'.strip()")
        
        if self.date_from or self.date_to:
            date_range = f"{self.date_from or 'start'} to {self.date_to or 'now'}"
            parts.append(f"dates={date_range}")
        
        if self.listserv != "all":
            parts.append(f"list={self.listserv}")
        
        if not parts:
            return "SearchParams(empty search - will return all messages)"
        
        return f"SearchParams({', '.join(parts)})"


# ============================================================
# EXAMPLE USAGE
# ============================================================

if __name__ == "__main__":
    # Example 1: Simple keyword search
    search1 = SearchParams(keyword="workers compensation")
    print("Example 1 - Simple search:")
    print(search1)
    print(f"Form data: {search1.to_form_data()}\n")
    
    # Example 2: Advanced search with multiple criteria
    from datetime import date, timedelta
    
    search2 = SearchParams(
        keywords_all="workers compensation",
        keywords_exclude="defense attorney",
        listserv="lawnet",
        date_from=date.today() - timedelta(days=30),
        date_to=date.today(),
        max_pages=5
    )
    print("Example 2 - Advanced search:")
    print(search2)
    print(f"Form data: {search2.to_form_data()}\n")
    
    # Example 3: Search by author
    search3 = SearchParams(
        author_last_name="Smith",
        listserv="lawnet",
        search_in="subject_only"
    )
    print("Example 3 - Author search:")
    print(search3)
    print(f"Form data: {search3.to_form_data()}\n")

