#!/usr/bin/env python3
"""
Test script to verify pagination fix
"""

from scraper import CAAAScraper
from search_params import SearchParams

def test_pagination():
    """Test that scraper can fetch messages across multiple pages"""
    
    print("\n" + "="*60)
    print("TESTING PAGINATION FIX")
    print("="*60 + "\n")
    
    # Create search with keyword "medical" (known to have 10,000+ results)
    search = SearchParams(
        keyword="medical",
        max_pages=5,
        max_messages=50
    )
    
    print(f"Search Parameters:")
    print(f"  Keyword: {search.keyword}")
    print(f"  Max Pages: {search.max_pages}")
    print(f"  Max Messages: {search.max_messages}")
    print()
    
    # Create scraper and run
    scraper = CAAAScraper()
    
    def progress(status, current, total):
        print(f"  [{current}/{total}] {status}")
    
    try:
        results = scraper.scrape(search, progress_callback=progress)
        
        print("\n" + "="*60)
        print("RESULTS")
        print("="*60 + "\n")
        
        print(f"✓ Total messages fetched: {len(results)}")
        
        # Check if we got messages from multiple pages
        pages_seen = set()
        for msg in results:
            pages_seen.add(msg.get('page', 1))
        
        print(f"✓ Pages retrieved: {sorted(pages_seen)}")
        print(f"✓ Number of pages: {len(pages_seen)}")
        
        # Show sample messages
        print(f"\nSample messages:")
        for i, msg in enumerate(results[:3], 1):
            print(f"\n{i}. [{msg.get('page', '?')}] {msg['subject']}")
            print(f"   From: {msg['from_name']}")
            print(f"   Date: {msg['post_date']}")
            print(f"   Body preview: {msg['body'][:100]}...")
        
        # Verify we got more than 10 messages (one page)
        if len(results) > 10:
            print(f"\n✓ SUCCESS! Fetched {len(results)} messages across {len(pages_seen)} pages")
            print(f"  (Previously only fetched 10 messages from 1 page)")
            return True
        else:
            print(f"\n✗ FAILED! Only fetched {len(results)} messages from {len(pages_seen)} page(s)")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pagination()
    exit(0 if success else 1)

