#!/usr/bin/env python3
"""
End-to-end test: Plain English query → AI Enhancement → Scraping → AI Filtering → Results
"""

import os
from orchestrator import CAAAOrchestrator

# Database configuration
db_config = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'caaa_scraper',
    'user': 'caaa_user',
    'password': 'caaa_scraper_2025'
}

print("\n" + "="*60)
print("END-TO-END TEST: CAAA Scraper with AI")
print("="*60)

# Initialize orchestrator
try:
    orchestrator = CAAAOrchestrator(db_config)
    print("✓ Orchestrator initialized")
except Exception as e:
    print(f"❌ Failed to initialize: {e}")
    exit(1)

# Test query
user_query = "permanent disability ratings"

print(f"\nUser query: \"{user_query}\"")
print("\n⚠️  TEST MODE: Limiting to 5 messages for speed")
print("\nStarting search...")

# Modify search params to limit messages for testing
from search_params import SearchParams
from query_enhancer import QueryEnhancer

# Get AI-enhanced params
enhancer = QueryEnhancer()
search_params = enhancer.enhance_query(user_query)

# Limit to 5 messages for testing
search_params.max_messages = 5
search_params.max_pages = 1

# Create search manually
search_id = orchestrator.db.create_search(search_params)
orchestrator.db.update_search_status(search_id, 'running')

print(f"✓ Search ID: {search_id}")

# Scrape
print("\n→ STEP 2: Scraping CAAA listserv...")
try:
    messages = orchestrator.scraper.scrape(search_params, progress_callback=orchestrator._progress_callback)
    print(f"\n✓ Scraped {len(messages)} messages")
except Exception as e:
    print(f"\n❌ Scraping failed: {e}")
    result = {'success': False, 'error': str(e), 'search_id': search_id}
    
# Store and analyze
if 'messages' in locals():
    # Store messages
    print("\n→ STEP 3: Storing messages in database...")
    for msg in messages:
        message_id = orchestrator.db.get_or_create_message(msg['caaa_message_id'], msg)
        orchestrator.db.add_search_result(search_id, message_id, msg['position'], msg['page'])
    
    orchestrator.db.update_search_status(search_id, 'running', total_found=len(messages))
    
    # Analyze relevance
    print("\n→ STEP 4: Analyzing relevance with AI...")
    relevant_count = orchestrator._analyze_relevance(search_id, messages, user_query)
    
    orchestrator.db.update_search_status(search_id, 'completed', total_relevant=relevant_count)
    
    # Get results
    results = orchestrator.db.get_relevant_results(search_id)
    
    result = {
        'success': True,
        'search_id': search_id,
        'total_found': len(messages),
        'relevant_found': len(results),
        'results': results,
        'stats': orchestrator.db.get_search_stats(search_id)
    }
else:
    result = {'success': False}

if result['success']:
    print("\n" + "="*60)
    print("SEARCH COMPLETE!")
    print("="*60)
    print(f"Total messages found: {result['total_found']}")
    print(f"Relevant messages: {result['relevant_found']}")
    
    print("\n" + "="*60)
    print("TOP 5 RELEVANT RESULTS")
    print("="*60)
    
    for i, msg in enumerate(result['results'][:5]):
        print(f"\n{i+1}. {msg['subject']}")
        print(f"   From: {msg['from_name']}")
        print(f"   Date: {msg['post_date']}")
        if 'confidence' in msg and msg['confidence']:
            print(f"   Confidence: {msg['confidence']:.0%}")
        if 'ai_reasoning' in msg and msg['ai_reasoning']:
            print(f"   AI: {msg['ai_reasoning']}")
        print(f"   Preview: {msg['body'][:100]}...")
else:
    print(f"\n❌ Search failed: {result.get('error')}")

