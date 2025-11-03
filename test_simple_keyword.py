#!/usr/bin/env python3
"""
Test with the simplest possible search - just keyword="workers"
"""

from scraper import CAAAScraper
from search_params import SearchParams

print("\n" + "="*60)
print("SIMPLE KEYWORD TEST: 'workers'")
print("="*60)

# Simplest possible search
search_params = SearchParams(
    keyword="workers",
    max_messages=5,
    max_pages=1
)

print(f"\nSearch params: {search_params}")
print(f"Form data: {search_params.to_form_data()}")

# Scrape
scraper = CAAAScraper()

def progress(status, current, total):
    print(f"  [{current}/{total}] {status}")

try:
    messages = scraper.scrape(search_params, progress_callback=progress)
    
    print(f"\n✓ SUCCESS! Scraped {len(messages)} messages")
    
    if len(messages) > 0:
        print("\nFirst message:")
        print(f"  Subject: {messages[0]['subject']}")
        print(f"  From: {messages[0]['from_name']}")
        print(f"  Date: {messages[0]['post_date']}")
        print(f"  Body preview: {messages[0]['body'][:100]}...")
    else:
        print("\n⚠️  No messages found (but search completed)")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

