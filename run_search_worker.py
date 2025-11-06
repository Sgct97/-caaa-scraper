#!/usr/bin/env python3
"""
Worker script to run scraper in a separate process
This avoids Playwright threading issues
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import CAAAOrchestrator
from database import Database

def main():
    if len(sys.argv) < 3:
        print("Usage: run_search_worker.py <search_id> <query>")
        sys.exit(1)
    
    search_id = sys.argv[1]
    query = sys.argv[2]
    
    print(f"🔍 Worker started for search {search_id}", flush=True)
    
    # Database config from environment
    db_config = {
        'dbname': os.getenv('DB_NAME', 'caaa_scraper'),
        'user': os.getenv('DB_USER', 'caaa_user'),
        'password': os.getenv('DB_PASSWORD', 'secure_password_here'),
        'host': os.getenv('DB_HOST', 'localhost')
    }
    
    try:
        # Initialize orchestrator
        orchestrator = CAAAOrchestrator(
            db_config=db_config,
            storage_state_path=Path('/srv/caaa_scraper/auth.json')
        )
        
        # Get search params from database
        search_info = orchestrator.db.get_search_info(search_id)
        if not search_info:
            print(f"❌ Search {search_id} not found", flush=True)
            sys.exit(1)
        
        # Parse search params from JSONB
        from search_params import SearchParams
        search_params_dict = search_info.get('search_params', {})
        
        # Reconstruct SearchParams from the stored dict
        search_params = SearchParams(
            keyword=search_params_dict.get('s_key'),
            keywords_all=search_params_dict.get('s_key_all'),
            keywords_phrase=search_params_dict.get('s_key_phrase'),
            keywords_any=search_params_dict.get('s_key_any'),
            keywords_exclude=search_params_dict.get('s_key_exclude'),
            listserv=search_params_dict.get('s_listserv', 'all'),
            date_from=search_params_dict.get('s_postdatefrom'),
            date_to=search_params_dict.get('s_postdateto'),
            posted_by=search_params_dict.get('s_postedby'),
            author_last_name=search_params_dict.get('s_lastname'),
            search_in=search_params_dict.get('s_searchin', 'subject_and_body'),
            attachment_filter=search_params_dict.get('s_attachments', 'all'),
            max_messages=search_params_dict.get('max_messages', 100),
            max_pages=search_params_dict.get('max_pages', 10)
        )
        
        print(f"✓ Search params loaded", flush=True)
        
        # Scrape
        print(f"🌐 Starting scrape...", flush=True)
        messages = orchestrator.scraper.scrape(search_params)
        print(f"✓ Scrape complete: {len(messages)} messages found", flush=True)
        
        # Store messages
        for msg in messages:
            message_id = orchestrator.db.get_or_create_message(msg['caaa_message_id'], msg)
            orchestrator.db.add_search_result(search_id, message_id, msg['position'], msg['page'])
        
        orchestrator.db.update_search_status(search_id, 'running', total_found=len(messages))
        print(f"✓ Stored {len(messages)} messages in database", flush=True)
        
        # Analyze relevance with AI
        if orchestrator.ai_analyzer and len(messages) > 0:
            print(f"🤖 Starting AI analysis...", flush=True)
            relevant_count = orchestrator._analyze_relevance(search_id, messages, query)
            print(f"✓ AI analysis complete: {relevant_count} relevant", flush=True)
        else:
            relevant_count = len(messages)
        
        # Mark complete
        orchestrator.db.update_search_status(search_id, 'completed', total_relevant=relevant_count)
        print(f"✅ Search {search_id} completed successfully!", flush=True)
        
    except Exception as e:
        print(f"❌ Search {search_id} failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        
        # Mark as failed in database
        db = Database(db_config)
        db.update_search_status(search_id, 'failed')
        sys.exit(1)

if __name__ == "__main__":
    main()

