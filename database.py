#!/usr/bin/env python3
"""
Database module for CAAA scraper
Handles all PostgreSQL interactions
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from search_params import SearchParams


class Database:
    """PostgreSQL database manager for CAAA scraper"""
    
    def __init__(self, db_config: dict):
        """
        Initialize database connection
        
        Args:
            db_config: Dict with keys: host, port, dbname, user, password
        """
        self.config = db_config
        self._test_connection()
    
    def _test_connection(self):
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            print("✓ Database connection successful")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = psycopg2.connect(**self.config)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    # ============================================================
    # SEARCHES
    # ============================================================
    
    def create_search(self, search_params: SearchParams) -> str:
        """
        Create a new search record
        
        Returns:
            search_id (UUID as string)
        """
        form_data = search_params.to_form_data()
        print(f"🔍 DEBUG create_search - form_data: {form_data}", flush=True)
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO searches (
                        search_params,
                        keyword,
                        listserv,
                        date_from,
                        date_to,
                        status
                    ) VALUES (%s, %s, %s, %s, %s, 'pending')
                    RETURNING id::text
                """, (
                    Json(form_data),
                    search_params.keyword,
                    search_params.listserv if search_params.listserv != "all" else None,
                    search_params.date_from,
                    search_params.date_to
                ))
                
                search_id = cur.fetchone()[0]
                print(f"✓ Created search: {search_id}")
                return search_id
    
    def update_search_status(self, search_id: str, status: str,
                            total_found: Optional[int] = None,
                            total_relevant: Optional[int] = None):
        """Update search status and counts"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                updates = ["status = %s"]
                params = [status]
                
                if status == 'running':
                    updates.append("started_at = NOW()")
                elif status in ['completed', 'failed']:
                    updates.append("completed_at = NOW()")
                
                if total_found is not None:
                    updates.append("total_messages_found = %s")
                    params.append(total_found)
                
                if total_relevant is not None:
                    updates.append("total_relevant_found = %s")
                    params.append(total_relevant)
                
                params.append(search_id)
                
                query = f"""
                    UPDATE searches 
                    SET {', '.join(updates)}
                    WHERE id = %s
                """
                
                cur.execute(query, params)
    
    # ============================================================
    # MESSAGES
    # ============================================================
    
    def get_or_create_message(self, caaa_message_id: str, message_data: dict) -> str:
        """
        Get existing message or create new one
        
        Args:
            caaa_message_id: CAAA message ID (e.g., '21783907')
            message_data: Dict with keys: post_date, from_name, from_email, 
                         listserv, subject, body, has_attachment
        
        Returns:
            message_id (UUID as string)
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Check if exists
                cur.execute("""
                    SELECT id::text FROM messages 
                    WHERE caaa_message_id = %s
                """, (caaa_message_id,))
                
                result = cur.fetchone()
                if result:
                    return result[0]
                
                # Create new
                cur.execute("""
                    INSERT INTO messages (
                        caaa_message_id,
                        post_date,
                        from_name,
                        from_email,
                        listserv,
                        subject,
                        body,
                        body_length,
                        has_attachment
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id::text
                """, (
                    caaa_message_id,
                    message_data.get('post_date'),
                    message_data.get('from_name'),
                    message_data.get('from_email'),
                    message_data.get('listserv'),
                    message_data.get('subject'),
                    message_data.get('body'),
                    len(message_data.get('body', '')) if message_data.get('body') else 0,
                    message_data.get('has_attachment', False)
                ))
                
                message_id = cur.fetchone()[0]
                return message_id
    
    def message_exists(self, caaa_message_id: str) -> bool:
        """Check if message already exists in database"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM messages 
                        WHERE caaa_message_id = %s
                    )
                """, (caaa_message_id,))
                
                return cur.fetchone()[0]
    
    # ============================================================
    # SEARCH RESULTS
    # ============================================================
    
    def add_search_result(self, search_id: str, message_id: str,
                         position: int, page: int):
        """Link a message to a search as a result"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO search_results (
                        search_id, message_id, result_position, result_page
                    ) VALUES (%s, %s, %s, %s)
                    ON CONFLICT (search_id, message_id) DO NOTHING
                """, (search_id, message_id, position, page))
    
    # ============================================================
    # ANALYSES
    # ============================================================
    
    def save_analysis(self, search_id: str, message_id: str, analysis: dict):
        """
        Save AI analysis result
        
        Args:
            analysis: Dict with keys: is_relevant, confidence, ai_reasoning,
                     ai_model, ai_tokens_used, ai_cost_usd
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO analyses (
                        search_id,
                        message_id,
                        is_relevant,
                        confidence,
                        ai_reasoning,
                        ai_model,
                        ai_tokens_used,
                        ai_cost_usd
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (search_id, message_id) 
                    DO UPDATE SET
                        is_relevant = EXCLUDED.is_relevant,
                        confidence = EXCLUDED.confidence,
                        ai_reasoning = EXCLUDED.ai_reasoning,
                        analyzed_at = NOW()
                """, (
                    search_id,
                    message_id,
                    analysis['is_relevant'],
                    analysis.get('confidence'),
                    analysis.get('ai_reasoning'),
                    analysis.get('ai_model'),
                    analysis.get('ai_tokens_used'),
                    analysis.get('ai_cost_usd')
                ))
    
    def analysis_exists(self, search_id: str, message_id: str) -> bool:
        """Check if analysis already exists for this search + message"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM analyses 
                        WHERE search_id = %s AND message_id = %s
                    )
                """, (search_id, message_id))
                
                return cur.fetchone()[0]
    
    # ============================================================
    # QUERIES
    # ============================================================
    
    def get_relevant_results(self, search_id: str) -> List[Dict[str, Any]]:
        """Get all relevant messages for a search"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        sr.search_id,
                        sr.message_id,
                        m.caaa_message_id,
                        m.subject,
                        m.author,
                        m.posted_date,
                        m.body,
                        a.is_relevant,
                        a.confidence as confidence_score,
                        a.ai_reasoning,
                        sr.result_position as position,
                        sr.result_page as page_number
                    FROM search_results sr
                    JOIN messages m ON sr.message_id = m.id
                    LEFT JOIN analyses a ON sr.search_id = a.search_id AND sr.message_id = a.message_id
                    WHERE sr.search_id = %s
                    ORDER BY sr.result_position
                """, (search_id,))
                
                return cur.fetchall()
    
    def get_search_stats(self, search_id: str) -> dict:
        """Get statistics for a search"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        s.keyword,
                        s.total_messages_found,
                        s.total_relevant_found,
                        s.status,
                        s.created_at,
                        s.completed_at,
                        COUNT(DISTINCT a.id) as analyzed_count,
                        AVG(a.confidence) FILTER (WHERE a.is_relevant = TRUE) as avg_confidence
                    FROM searches s
                    LEFT JOIN analyses a ON s.id = a.search_id
                    WHERE s.id = %s
                    GROUP BY s.id, s.keyword, s.total_messages_found, s.total_relevant_found, 
                             s.status, s.created_at, s.completed_at
                """, (search_id,))
                
                return cur.fetchone()
    
    def get_search_info(self, search_id: str) -> dict:
        """Get basic search information"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        id::text,
                        keyword,
                        status,
                        total_messages_found,
                        total_relevant_found,
                        created_at,
                        started_at,
                        completed_at
                    FROM searches
                    WHERE id = %s
                """, (search_id,))
                
                return cur.fetchone()
    
    def get_recent_searches(self, limit: int = 10) -> List[Dict]:
        """Get recent searches"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        id::text,
                        keyword,
                        status,
                        total_messages_found,
                        total_relevant_found,
                        created_at,
                        completed_at
                    FROM searches
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                
                return cur.fetchall()
    
    def get_platform_stats(self) -> dict:
        """Get overall platform statistics"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT s.id) as total_searches,
                        COUNT(DISTINCT m.id) as total_messages,
                        COUNT(DISTINCT a.id) FILTER (WHERE a.is_relevant = TRUE) as total_relevant,
                        COUNT(DISTINCT s.id) FILTER (WHERE s.status = 'completed') as completed_searches,
                        COUNT(DISTINCT s.id) FILTER (WHERE s.status = 'running') as running_searches
                    FROM searches s
                    LEFT JOIN search_results sr ON s.id = sr.search_id
                    LEFT JOIN messages m ON sr.message_id = m.id
                    LEFT JOIN analyses a ON a.message_id = m.id
                """)
                
                return cur.fetchone()


# ============================================================
# Example Usage
# ============================================================

if __name__ == "__main__":
    # Example configuration
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'dbname': 'caaa_scraper',
        'user': 'caaa_user',
        'password': 'your_password_here'
    }
    
    try:
        db = Database(db_config)
        print("✓ Database module loaded successfully")
    except Exception as e:
        print(f"❌ Error: {e}")

