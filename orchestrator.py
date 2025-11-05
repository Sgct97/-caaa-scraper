#!/usr/bin/env python3
"""
Main Orchestrator - Ties everything together
User Query → AI Enhancement → Scraping → Database → AI Filtering → Results
"""

import os
from typing import List, Dict, Optional
from datetime import datetime

from query_enhancer import QueryEnhancer
from scraper import CAAAScraper
from database import Database
from ai_analyzer import AIAnalyzer
from search_params import SearchParams


class CAAAOrchestrator:
    """Main orchestrator for the CAAA scraper system"""
    
    def __init__(self, 
                 db_config: dict,
                 openai_api_key: Optional[str] = None,
                 storage_state_path: str = "auth.json"):
        """
        Initialize orchestrator
        
        Args:
            db_config: Database configuration dict
            openai_api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            storage_state_path: Path to auth cookies
        """
        self.db = Database(db_config)
        self.scraper = CAAAScraper(storage_state_path)
        
        # AI components - using local Llama via Ollama (no API key needed)
        from openai import OpenAI
        
        # Use local Llama via Ollama for HIPAA compliance
        self.client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"  # Ollama doesn't need a real key
        )
        self.query_enhancer = QueryEnhancer()
        self.ai_analyzer = AIAnalyzer()
        print("✓ AI components initialized (Local Llama 3.1 8B)")
    
    def search(self, user_query: str, use_ai_enhancement: bool = True) -> Dict:
        """
        Main search method - full end-to-end flow
        
        Args:
            user_query: Plain English query or simple keyword
            use_ai_enhancement: Whether to use AI to optimize search params
        
        Returns:
            Dict with search results and metadata
        """
        
        print("\n" + "="*60)
        print("CAAA SEARCH ORCHESTRATOR")
        print("="*60)
        print(f"User query: \"{user_query}\"")
        print(f"Timestamp: {datetime.now()}")
        print("="*60)
        
        # Step 1: Create search record in database
        print("\n→ STEP 1: Creating search record...")
        
        # Enhance query with AI (if enabled and available)
        if use_ai_enhancement and self.query_enhancer:
            search_params = self.query_enhancer.enhance_query(user_query)
        else:
            # Fallback: simple keyword search
            print("\n→ Using simple keyword search (AI enhancement disabled)")
            search_params = SearchParams(keyword=user_query)
        
        search_id = self.db.create_search(search_params)
        self.db.update_search_status(search_id, 'running')
        
        print(f"✓ Search ID: {search_id}")
        
        # Step 2: Scrape messages
        print("\n→ STEP 2: Scraping CAAA listserv...")
        
        try:
            messages = self.scraper.scrape(
                search_params,
                progress_callback=self._progress_callback
            )
            
            print(f"\n✓ Scraped {len(messages)} messages")
            
        except Exception as e:
            print(f"\n❌ Scraping failed: {e}")
            self.db.update_search_status(search_id, 'failed')
            return {
                'success': False,
                'error': str(e),
                'search_id': search_id
            }
        
        # Step 3: Store messages in database
        print("\n→ STEP 3: Storing messages in database...")
        
        stored_count = 0
        new_count = 0
        
        for i, msg in enumerate(messages):
            # Check if message already exists
            if self.db.message_exists(msg['caaa_message_id']):
                print(f"  [{i+1}/{len(messages)}] Message {msg['caaa_message_id']} already in DB (skipping)")
                
                # Get existing message_id
                with self.db.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT id::text FROM messages 
                            WHERE caaa_message_id = %s
                        """, (msg['caaa_message_id'],))
                        message_id = cur.fetchone()[0]
            else:
                # Create new message
                message_id = self.db.get_or_create_message(
                    msg['caaa_message_id'],
                    msg
                )
                new_count += 1
                print(f"  [{i+1}/{len(messages)}] Stored new message {msg['caaa_message_id']}")
            
            # Link to search
            self.db.add_search_result(
                search_id,
                message_id,
                msg['position'],
                msg['page']
            )
            stored_count += 1
        
        print(f"\n✓ Stored {stored_count} messages ({new_count} new, {stored_count - new_count} existing)")
        
        # Update search metadata
        self.db.update_search_status(
            search_id,
            'running',
            total_found=len(messages)
        )
        
        # Step 4: AI relevance analysis
        print("\n→ STEP 4: Analyzing relevance with AI...")
        
        if self.ai_analyzer:
            relevant_count = self._analyze_relevance(search_id, messages, user_query)
        else:
            print("  ⚠️  Skipping AI analysis (no API key)")
            relevant_count = len(messages)  # Assume all relevant without AI
        
        # Step 5: Mark search complete
        self.db.update_search_status(
            search_id,
            'completed',
            total_relevant=relevant_count
        )
        
        print(f"\n✓ Search complete!")
        
        # Step 6: Get results
        print("\n→ STEP 5: Retrieving relevant results...")
        
        if self.ai_analyzer:
            results = self.db.get_relevant_results(search_id)
        else:
            # Without AI, just return all messages
            with self.db.get_connection() as conn:
                from psycopg2.extras import RealDictCursor
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            m.caaa_message_id,
                            m.post_date,
                            m.from_name,
                            m.subject,
                            m.body,
                            sr.result_position
                        FROM search_results sr
                        JOIN messages m ON sr.message_id = m.id
                        WHERE sr.search_id = %s
                        ORDER BY sr.result_position
                    """, (search_id,))
                    results = cur.fetchall()
        
        print(f"✓ Found {len(results)} relevant results")
        
        # Get search stats
        stats = self.db.get_search_stats(search_id)
        
        # Print summary
        print("\n" + "="*60)
        print("SEARCH SUMMARY")
        print("="*60)
        print(f"Total messages found: {stats['total_messages_found']}")
        print(f"Relevant messages: {stats['total_relevant_found']}")
        if self.ai_analyzer and stats['avg_confidence']:
            print(f"Average confidence: {stats['avg_confidence']:.1%}")
        print(f"Search completed at: {stats['completed_at']}")
        
        if self.ai_analyzer:
            ai_stats = self.ai_analyzer.get_usage_stats()
            print(f"\nAI Usage:")
            print(f"  Tokens: {ai_stats['total_tokens']}")
            print(f"  Cost: ${ai_stats['total_cost_usd']:.4f}")
        
        return {
            'success': True,
            'search_id': search_id,
            'total_found': len(messages),
            'relevant_found': len(results),
            'results': results,
            'stats': stats
        }
    
    def _progress_callback(self, status: str, current: int, total: int):
        """Progress callback for scraper"""
        print(f"  [{current}/{total}] {status}")
    
    def _analyze_relevance(self, search_id: str, messages: List[Dict], user_query: str) -> int:
        """Analyze message relevance with AI"""
        
        relevant_count = 0
        
        for i, msg in enumerate(messages):
            print(f"  [{i+1}/{len(messages)}] Analyzing: {msg['subject'][:50]}...")
            
            # Get message_id from database
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id::text FROM messages 
                        WHERE caaa_message_id = %s
                    """, (msg['caaa_message_id'],))
                    message_id = cur.fetchone()[0]
            
            # Check if already analyzed
            if self.db.analysis_exists(search_id, message_id):
                print(f"    ✓ Already analyzed (skipping)")
                continue
            
            # Analyze with AI
            try:
                analysis = self.ai_analyzer.analyze_relevance(
                    message=msg,
                    search_keyword=user_query
                )
                
                # Save analysis
                self.db.save_analysis(search_id, message_id, analysis)
                
                if analysis['is_relevant']:
                    relevant_count += 1
                    print(f"    ✓ RELEVANT (confidence: {analysis['confidence']:.0%})")
                else:
                    print(f"    ✗ Not relevant")
                
            except Exception as e:
                print(f"    ⚠️  Analysis error: {e}")
        
        return relevant_count


# ============================================================
# Example Usage / CLI
# ============================================================

if __name__ == "__main__":
    import sys
    
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'dbname': 'caaa_scraper',
        'user': 'caaa_user',
        'password': 'caaa_scraper_2025'
    }
    
    # Initialize orchestrator
    try:
        orchestrator = CAAAOrchestrator(db_config)
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        sys.exit(1)
    
    # Get user query from command line or use default
    if len(sys.argv) > 1:
        user_query = ' '.join(sys.argv[1:])
    else:
        user_query = "workers compensation permanent disability"
    
    # Run search
    result = orchestrator.search(user_query, use_ai_enhancement=False)
    
    if result['success']:
        print("\n" + "="*60)
        print("TOP RESULTS")
        print("="*60)
        
        for i, msg in enumerate(result['results'][:5]):
            print(f"\n{i+1}. {msg['subject']}")
            print(f"   From: {msg['from_name']}")
            print(f"   Date: {msg['post_date']}")
            if 'ai_reasoning' in msg and msg['ai_reasoning']:
                print(f"   AI: {msg['ai_reasoning']}")
            print(f"   Body preview: {msg['body'][:150]}...")
    else:
        print(f"\n❌ Search failed: {result.get('error')}")

