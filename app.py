#!/usr/bin/env python3
"""
CAAA Legal Intelligence Platform - FastAPI Application
Enterprise-grade web dashboard for AI-powered legal research
"""

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Any
import os
import json
from datetime import datetime, date
import asyncio
from contextlib import asynccontextmanager

# Custom JSON encoder for FastAPI
class CustomJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        from decimal import Decimal
        
        def default(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
        
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=default,
        ).encode("utf-8")

from orchestrator import CAAAOrchestrator
from database import Database
from decimal import Decimal

# Helper function to convert non-JSON-serializable types
def convert_decimals(obj, for_json_api=False):
    """Recursively convert Decimal objects for serialization
    
    Args:
        obj: Object to convert
        for_json_api: If True, also convert date/datetime to ISO strings for JSON API responses
    """
    from datetime import date, datetime
    
    if isinstance(obj, Decimal):
        return float(obj)
    elif for_json_api and isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_decimals(v, for_json_api) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item, for_json_api) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_decimals(item, for_json_api) for item in obj)
    return obj

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'dbname': os.getenv('DB_NAME', 'caaa_scraper'),
    'user': os.getenv('DB_USER', 'caaa_user'),
    'password': os.getenv('DB_PASSWORD', 'caaa_scraper_2025')
}

# Global orchestrator instance
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup"""
    global orchestrator
    orchestrator = CAAAOrchestrator(
        db_config=db_config,
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    print("✓ CAAA Legal Intelligence Platform initialized")
    yield
    print("✓ Shutting down gracefully")

# Initialize FastAPI app with custom JSON encoder
app = FastAPI(
    title="CAAA Legal Intelligence",
    description="AI-Powered Legal Research Platform",
    version="1.0.0",
    lifespan=lifespan,
    default_response_class=CustomJSONResponse
)

# Enable CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://caaa-scraper.vercel.app", "http://localhost:8000", "http://134.199.196.31:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ============================================================
# Request Models
# ============================================================

class SearchRequest(BaseModel):
    search_fields: Optional[dict] = None
    ai_intent: Optional[str] = None
    use_ai_enhancement: bool = False
    max_messages: int = 10
    max_pages: int = 2

class AIAnalyzeRequest(BaseModel):
    intent: str
    current_fields: dict

class AIFollowUpRequest(BaseModel):
    answer: str
    conversation: List[dict]
    current_fields: dict

# ============================================================
# Routes
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    
    # Get recent searches
    recent_searches = orchestrator.db.get_recent_searches(limit=10)
    
    # Get stats
    stats = orchestrator.db.get_platform_stats()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "recent_searches": convert_decimals([dict(s) for s in recent_searches]) if recent_searches else [],
        "stats": convert_decimals(dict(stats)) if stats else {}
    })

@app.post("/api/search")
async def create_search(search_req: SearchRequest, background_tasks: BackgroundTasks):
    """Create a new search and start processing in background"""
    
    try:
        # DEBUG: Log what we received
        print(f"📥 Received search request:")
        print(f"   search_fields: {search_req.search_fields}")
        print(f"   ai_intent: {search_req.ai_intent}")
        print(f"   use_ai_enhancement: {search_req.use_ai_enhancement}")
        
        # Validate that we have either search fields or AI intent
        if not search_req.search_fields and not search_req.ai_intent:
            raise HTTPException(status_code=400, detail="Must provide search fields or AI intent")
        
        # Start search in background
        search_id = await run_search_async(
            search_req.search_fields,
            search_req.ai_intent,
            search_req.use_ai_enhancement,
            search_req.max_messages,
            search_req.max_pages
        )
        
        return {
            "success": True,
            "search_id": search_id,
            "message": "Search started successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search/{search_id}/status")
async def get_search_status(search_id: str):
    """Get the status of a search"""
    
    try:
        search_info = orchestrator.db.get_search_info(search_id)
        
        if not search_info:
            raise HTTPException(status_code=404, detail="Search not found")
        
        return convert_decimals({
            "success": True,
            "search_id": search_id,
            "status": search_info['status'],
            "progress": {
                "total_found": search_info.get('total_messages_found', 0),
                "analyzed": search_info.get('analyzed_count', 0),
                "relevant": search_info.get('total_relevant_found', 0)
            },
            "started_at": search_info.get('started_at'),
            "completed_at": search_info.get('completed_at')
        }, for_json_api=True)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search/{search_id}/results")
async def get_search_results(search_id: str):
    """Get results for a completed search"""
    
    try:
        # Get search info
        search_info = orchestrator.db.get_search_info(search_id)
        
        if not search_info:
            raise HTTPException(status_code=404, detail="Search not found")
        
        # Get relevant results
        results = orchestrator.db.get_relevant_results(search_id)
        
        # Get stats
        stats = orchestrator.db.get_search_stats(search_id)
        
        # Convert all database results to JSON-safe format
        return convert_decimals({
            "success": True,
            "search_id": search_id,
            "query": search_info.get('keyword'),
            "status": search_info['status'],
            "stats": dict(stats) if stats else {},
            "results": [dict(r) for r in results]
        }, for_json_api=True)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/{search_id}", response_class=HTMLResponse)
async def view_search(request: Request, search_id: str):
    """View a specific search and its results"""
    
    try:
        search_info = orchestrator.db.get_search_info(search_id)
        
        if not search_info:
            raise HTTPException(status_code=404, detail="Search not found")
        
        results = orchestrator.db.get_relevant_results(search_id)
        stats = orchestrator.db.get_search_stats(search_id)
        
        return templates.TemplateResponse("search_results.html", {
            "request": request,
            "search_id": search_id,
            "search_info": convert_decimals(dict(search_info)) if search_info else {},
            "results": convert_decimals([dict(r) for r in results]) if results else [],
            "stats": convert_decimals(dict(stats)) if stats else {}
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search/{search_id}")
async def get_search_results_json(search_id: str):
    """Get search results as JSON (for Vercel frontend)"""
    
    try:
        search_info = orchestrator.db.get_search_info(search_id)
        
        if not search_info:
            raise HTTPException(status_code=404, detail="Search not found")
        
        results = orchestrator.db.get_relevant_results(search_id)
        stats = orchestrator.db.get_search_stats(search_id)
        
        return {
            "success": True,
            "search_id": search_id,
            "search_info": convert_decimals(dict(search_info)) if search_info else {},
            "results": convert_decimals([dict(r) for r in results]) if results else [],
            "stats": convert_decimals(dict(stats)) if stats else {}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/analyze")
async def ai_analyze(request: AIAnalyzeRequest):
    """AI analyzes user intent - asks follow-up if vague, uses QueryEnhancer if specific"""
    
    try:
        if not orchestrator.client:
            raise HTTPException(status_code=503, detail="AI service not available")
        
        # STEP 1: Check if query is too vague and needs clarification
        vagueness_check = f"""Analyze this query and determine if it has enough information to search effectively.

Query: "{request.intent}"

A query is VAGUE if:
1. Multiple interpretations exist that would lead to VERY DIFFERENT searches
2. Key information is missing that would significantly change what we search for
3. The query is so broad that any search would return too many irrelevant results

A query is SPECIFIC if:
1. We can confidently determine what to search for
2. The search intent is unambiguous (or ambiguity doesn't matter much)
3. We have enough information to create targeted search parameters

CRITICAL DISTINCTIONS TO CHECK:
- Person name WITHOUT context → VAGUE (could mean BY them or ABOUT them)
  - "Chris Johnson" → VAGUE
  - "articles BY Chris Johnson" → SPECIFIC
  - "articles MENTIONING Chris Johnson" → SPECIFIC
  
- Topic without WHAT aspect → Often VAGUE
  - Just a case name → VAGUE (which aspect?)
  - "Case X's impact on Y" → SPECIFIC (clear aspect)
  
- Overly broad → May be VAGUE
  - "recent changes" → VAGUE (changes to what?)
  - "recent changes to settlement procedures" → SPECIFIC

When VAGUE, craft a clarifying question that:
1. Identifies the ambiguity/missing info
2. Offers 2-3 specific alternatives
3. Helps narrow the search effectively

Return JSON:
{{
  "is_vague": true/false,
  "follow_up_question": "clarifying question" OR null
}}"""

        vagueness_response = orchestrator.client.chat.completions.create(
            model="qwen2.5:32b",
            messages=[{"role": "user", "content": vagueness_check}],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        vagueness_result = json.loads(vagueness_response.choices[0].message.content)
        print(f"🔍 Vagueness check: {vagueness_result}")
        
        # If vague, return follow-up question immediately
        if vagueness_result.get("is_vague", False):
            follow_up = vagueness_result.get("follow_up_question")
            print(f"❓ Query is vague, asking follow-up: {follow_up}")
            return {
                "success": True,
                "analysis": "Query needs clarification",
                "suggestions": None,
                "follow_up_question": follow_up
            }
        
        # STEP 2: Query is specific - use QueryEnhancer to generate search params
        print(f"✅ Query is specific, using QueryEnhancer")
        from query_enhancer import QueryEnhancer
        
        enhancer = QueryEnhancer()
        search_params = enhancer.enhance_query(request.intent)
        
        # Convert SearchParams to suggestions dictionary for frontend
        suggestions = {}
        
        if search_params.keyword:
            suggestions["keyword"] = search_params.keyword
        if search_params.keywords_all:
            suggestions["keywords_all"] = search_params.keywords_all
        if search_params.keywords_phrase:
            suggestions["keywords_phrase"] = search_params.keywords_phrase
        if search_params.keywords_any:
            suggestions["keywords_any"] = search_params.keywords_any
        if search_params.keywords_exclude:
            suggestions["keywords_exclude"] = search_params.keywords_exclude
        if search_params.listserv and search_params.listserv != "all":
            suggestions["listserv"] = search_params.listserv
        if search_params.search_in and search_params.search_in != "subject_and_body":
            suggestions["search_in"] = search_params.search_in
        if search_params.attachment_filter and search_params.attachment_filter != "all":
            suggestions["attachments"] = search_params.attachment_filter
        if search_params.posted_by:
            suggestions["posted_by"] = search_params.posted_by
        if search_params.author_first_name:
            suggestions["first_name"] = search_params.author_first_name
        if search_params.author_last_name:
            suggestions["last_name"] = search_params.author_last_name
        if search_params.date_from:
            suggestions["date_from"] = str(search_params.date_from)
        if search_params.date_to:
            suggestions["date_to"] = str(search_params.date_to)
        
        # Remove empty values
        suggestions = {k: v for k, v in suggestions.items() if v}
        
        print(f"✅ QueryEnhancer generated suggestions: {list(suggestions.keys())}")
        
        return {
            "success": True,
            "analysis": "Generated specific search parameters",
            "suggestions": suggestions if suggestions else None,
            "follow_up_question": None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/follow-up")
async def ai_follow_up(request: AIFollowUpRequest):
    """Continue AI conversation using QueryEnhancer with refined query"""
    
    try:
        if not orchestrator.client:
            raise HTTPException(status_code=503, detail="AI service not available")
        
        # Combine the conversation context into a refined query for QueryEnhancer
        # Get the original question from conversation
        original_query = ""
        for msg in request.conversation:
            if msg['role'] == 'user':
                original_query = msg['content']
                break
        
        # Create refined query: original question + user's clarifying answer
        refined_query = f"{original_query}. Specifically: {request.answer}"
        
        print(f"📝 Refined query for QueryEnhancer: {refined_query}")
        
        # Use QueryEnhancer with the refined query
        from query_enhancer import QueryEnhancer
        
        enhancer = QueryEnhancer()
        search_params = enhancer.enhance_query(refined_query)
        
        # Convert SearchParams to suggestions dictionary
        suggestions = {}
        
        if search_params.keyword:
            suggestions["keyword"] = search_params.keyword
        if search_params.keywords_all:
            suggestions["keywords_all"] = search_params.keywords_all
        if search_params.keywords_phrase:
            suggestions["keywords_phrase"] = search_params.keywords_phrase
        if search_params.keywords_any:
            suggestions["keywords_any"] = search_params.keywords_any
        if search_params.keywords_exclude:
            suggestions["keywords_exclude"] = search_params.keywords_exclude
        if search_params.listserv and search_params.listserv != "all":
            suggestions["listserv"] = search_params.listserv
        if search_params.search_in and search_params.search_in != "subject_and_body":
            suggestions["search_in"] = search_params.search_in
        if search_params.attachment_filter and search_params.attachment_filter != "all":
            suggestions["attachments"] = search_params.attachment_filter
        if search_params.posted_by:
            suggestions["posted_by"] = search_params.posted_by
        if search_params.author_first_name:
            suggestions["first_name"] = search_params.author_first_name
        if search_params.author_last_name:
            suggestions["last_name"] = search_params.author_last_name
        if search_params.date_from:
            suggestions["date_from"] = str(search_params.date_from)
        if search_params.date_to:
            suggestions["date_to"] = str(search_params.date_to)
        
        # Remove empty values
        suggestions = {k: v for k, v in suggestions.items() if v}
        
        print(f"✅ Follow-up QueryEnhancer generated: {list(suggestions.keys())}")
        
        return {
            "success": True,
            "analysis": "Generated search parameters based on your clarification",
            "suggestions": suggestions if suggestions else None,
            "follow_up_question": None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_platform_stats():
    """Get platform statistics for dashboard"""
    try:
        stats = orchestrator.db.get_platform_stats()
        return convert_decimals(dict(stats)) if stats else {
            "total_searches": 0,
            "total_messages": 0,
            "total_relevant": 0,
            "running_searches": 0
        }
    except Exception as e:
        return {
            "total_searches": 0,
            "total_messages": 0,
            "total_relevant": 0,
            "running_searches": 0
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# ============================================================
# Helper Functions
# ============================================================

async def run_search_async(search_fields: Optional[dict], ai_intent: Optional[str], 
                           use_ai: bool, max_messages: int, max_pages: int) -> str:
    """Run search asynchronously"""
    
    print(f"🔵 run_search_async called", flush=True)
    
    # Import here to avoid circular dependency
    from search_params import SearchParams
    from query_enhancer import QueryEnhancer
    
    print(f"🔵 Imports successful", flush=True)
    
    # Build search params from manual fields
    if search_fields:
        # User provided manual search fields
        # Parse dates if provided as strings (empty strings become None)
        from datetime import datetime
        
        date_from = search_fields.get('date_from')
        date_to = search_fields.get('date_to')
        
        # Convert empty strings to None
        if date_from == '' or not date_from:
            date_from = None
        elif isinstance(date_from, str):
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            
        if date_to == '' or not date_to:
            date_to = None
        elif isinstance(date_to, str):
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        
        # Helper to convert empty strings to None
        def clean_field(value):
            return None if value == '' or not value else value
        
        search_params = SearchParams(
            keyword=clean_field(search_fields.get('keyword')),
            keywords_all=clean_field(search_fields.get('keywords_all')),
            keywords_phrase=clean_field(search_fields.get('keywords_phrase')),
            keywords_any=clean_field(search_fields.get('keywords_any')),
            keywords_exclude=clean_field(search_fields.get('keywords_exclude')),
            listserv=search_fields.get('listserv', 'all') or 'all',
            date_from=date_from,
            date_to=date_to,
            posted_by=clean_field(search_fields.get('posted_by')),
            author_first_name=clean_field(search_fields.get('first_name')),  # Map 'first_name' to 'author_first_name'
            author_last_name=clean_field(search_fields.get('last_name')),  # Map 'last_name' to 'author_last_name'
            search_in=search_fields.get('search_in', 'subject_and_body') or 'subject_and_body',
            attachment_filter=search_fields.get('attachments', 'all') or 'all'  # Map 'attachments' to 'attachment_filter'
        )
    elif use_ai and ai_intent and orchestrator.query_enhancer:
        # Use AI to generate search params
        search_params = orchestrator.query_enhancer.enhance_query(ai_intent)
    else:
        # Fallback to simple keyword from AI intent
        search_params = SearchParams(keyword=ai_intent or "")
    
    # Apply limits
    search_params.max_messages = max_messages
    search_params.max_pages = max_pages
    
    # If no AI intent provided, construct one from search parameters for relevance analysis
    if not ai_intent or ai_intent.strip() == "":
        intent_parts = []
        has_content_criteria = False
        
        # Check for content-based criteria
        if search_params.keywords_all:
            intent_parts.append(f"messages containing all: {search_params.keywords_all}")
            has_content_criteria = True
        if search_params.keywords_phrase:
            intent_parts.append(f"exact phrase: {search_params.keywords_phrase}")
            has_content_criteria = True
        if search_params.keywords_any:
            intent_parts.append(f"containing: {search_params.keywords_any}")
            has_content_criteria = True
        
        # Author criteria
        author_criteria = []
        if search_params.author_last_name:
            author_criteria.append(f"author: {search_params.author_last_name}")
        if search_params.posted_by:
            author_criteria.append(f"posted by: {search_params.posted_by}")
        
        # If ONLY author criteria (no content keywords), make it clear we want ALL messages from that person
        if author_criteria and not has_content_criteria:
            ai_intent = f"Find ALL messages from {', '.join(author_criteria)}. Any message from this person is relevant regardless of content."
        elif intent_parts or author_criteria:
            # Has content criteria - combine everything normally
            ai_intent = "Looking for " + ", ".join(intent_parts + author_criteria)
        else:
            ai_intent = "all messages matching search criteria"
        
        print(f"📝 Generated AI intent from search fields: {ai_intent}", flush=True)
    
    # Create search record
    print(f"🔵 Creating search in database", flush=True)
    search_id = orchestrator.db.create_search(search_params)
    orchestrator.db.update_search_status(search_id, 'running')
    print(f"🔵 Search {search_id} created, spawning worker", flush=True)
    
    # Run as subprocess to avoid Playwright threading issues
    import subprocess
    import os
    
    # Set environment variables for worker
    worker_env = os.environ.copy()
    worker_env.update({
        'DISPLAY': ':99',
        'DB_NAME': 'caaa_scraper',
        'DB_USER': 'caaa_user', 
        'DB_PASSWORD': 'caaa_scraper_2025',
        'DB_HOST': 'localhost'
    })
    
    worker_log = f'/tmp/worker_{search_id}.log'
    print(f"🚀 Launching worker for search {search_id}, logs: {worker_log}", flush=True)
    
    with open(worker_log, 'w') as log_file:
        subprocess.Popen([
            '/srv/caaa_scraper/venv/bin/python',
            '/srv/caaa_scraper/run_search_worker.py',
            search_id,
            ai_intent
        ], stdout=log_file, stderr=log_file, env=worker_env)
    
    return search_id

def run_search_sync(search_id: str, search_params, query: str):
    """Synchronous search execution (runs in background)"""
    
    try:
        print(f"🔍 Starting scrape for search {search_id}...", flush=True)
        
        # Scrape
        messages = orchestrator.scraper.scrape(search_params)
        print(f"✓ Scrape complete: {len(messages)} messages found", flush=True)
        
        # Store messages
        for msg in messages:
            message_id = orchestrator.db.get_or_create_message(msg['caaa_message_id'], msg)
            orchestrator.db.add_search_result(search_id, message_id, msg['position'], msg['page'])
        
        orchestrator.db.update_search_status(search_id, 'running', total_found=len(messages))
        print(f"✓ Stored {len(messages)} messages in database", flush=True)
        
        # Analyze relevance with AI
        if orchestrator.ai_analyzer:
            print(f"🤖 Starting AI analysis...", flush=True)
            relevant_count = orchestrator._analyze_relevance(search_id, messages, query)
            print(f"✓ AI analysis complete: {relevant_count} relevant", flush=True)
        else:
            relevant_count = len(messages)
        
        # Mark complete
        orchestrator.db.update_search_status(search_id, 'completed', total_relevant=relevant_count)
        print(f"✅ Search {search_id} completed successfully!", flush=True)
        
    except Exception as e:
        orchestrator.db.update_search_status(search_id, 'failed')
        print(f"❌ Search {search_id} failed: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

