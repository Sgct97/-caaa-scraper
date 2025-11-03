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
print("\nStarting search...")

# Run search with AI enhancement
result = orchestrator.search(
    user_query, 
    use_ai_enhancement=True  # Enable AI query enhancement
)

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

