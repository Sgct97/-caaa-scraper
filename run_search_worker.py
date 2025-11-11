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
        
        print(f"📋 Raw search_params from DB: {search_params_dict}", flush=True)
        
        # Reconstruct SearchParams from the stored dict
        # Map form field names back to SearchParams attributes
        from datetime import datetime
        
        # Parse date strings if present (format: MM/DD/YYYY)
        date_from = search_params_dict.get('s_postdatefrom')
        date_to = search_params_dict.get('s_postdateto')
        
        if date_from and isinstance(date_from, str):
            try:
                date_from = datetime.strptime(date_from, '%m/%d/%Y').date()
            except:
                date_from = None
        
        if date_to and isinstance(date_to, str):
            try:
                date_to = datetime.strptime(date_to, '%m/%d/%Y').date()
            except:
                date_to = None
        
        search_params = SearchParams(
            keyword=search_params_dict.get('s_fname'),  # Basic keyword uses fname field
            keywords_all=search_params_dict.get('s_key_all'),
            keywords_phrase=search_params_dict.get('s_key_phrase'),
            keywords_any=search_params_dict.get('s_key_one'),  # 'any' maps to 's_key_one'
            keywords_exclude=search_params_dict.get('s_key_x'),  # 'exclude' maps to 's_key_x'
            listserv=search_params_dict.get('s_list', 'all'),
            date_from=date_from,
            date_to=date_to,
            posted_by=search_params_dict.get('s_postedby'),
            author_last_name=search_params_dict.get('s_lname'),  # Last name is 's_lname'
            search_in='subject_only' if search_params_dict.get('s_cat') == '1' else 'subject_and_body',
            attachment_filter='with_attachments' if search_params_dict.get('s_attachment') == '1' else ('without_attachments' if search_params_dict.get('s_attachment') == '0' else 'all'),
            max_messages=search_params_dict.get('max_messages', 100),
            max_pages=search_params_dict.get('max_pages', 10)
        )
        
        print(f"✓ Search params loaded", flush=True)
        print(f"   keywords_any={search_params.keywords_any}", flush=True)
        print(f"   keywords_phrase={search_params.keywords_phrase}", flush=True)
        print(f"   author_last_name={search_params.author_last_name}", flush=True)
        
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

