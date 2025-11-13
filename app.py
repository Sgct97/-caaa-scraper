#!/usr/bin/env python3
"""
CAAA Legal Intelligence Platform - FastAPI Application
Enterprise-grade web dashboard for AI-powered legal research
"""

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
import os
import json
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager

from orchestrator import CAAAOrchestrator
from database import Database

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

# Initialize FastAPI app
app = FastAPI(
    title="CAAA Legal Intelligence",
    description="AI-Powered Legal Research Platform",
    version="1.0.0",
    lifespan=lifespan
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
    max_messages: int = 100
    max_pages: int = 10

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
        "recent_searches": recent_searches,
        "stats": stats
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
        
        return {
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
        }
        
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
        
        return {
            "success": True,
            "search_id": search_id,
            "query": search_info.get('keyword'),
            "status": search_info['status'],
            "stats": stats,
            "results": [dict(r) for r in results]
        }
        
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
            "search_info": search_info,
            "results": results,
            "stats": stats
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/analyze")
async def ai_analyze(request: AIAnalyzeRequest):
    """AI analyzes user intent and current search fields, suggests improvements"""
    
    try:
        if not orchestrator.client:
            raise HTTPException(status_code=503, detail="AI service not available")
        
        # Build prompt for AI
        from datetime import datetime, timedelta
        today = datetime.now()
        three_months_ago = (today - timedelta(days=90)).strftime('%Y-%m-%d')
        six_months_ago = (today - timedelta(days=180)).strftime('%Y-%m-%d')
        one_year_ago = (today - timedelta(days=365)).strftime('%Y-%m-%d')
        today_str = today.strftime('%Y-%m-%d')
        
        prompt = f"""You are an expert legal research assistant for California workers' compensation law.
You help users search the CAAA listserv (a legal discussion forum) for relevant case discussions.

TODAY'S DATE: {today_str}

USER'S INTENT: "{request.intent}"

CURRENT SEARCH FIELDS THEY'VE FILLED:
{json.dumps(request.current_fields, indent=2)}

Your task:
1. Analyze what the user is truly trying to find
2. Review their current search field values  
3. Suggest SPECIFIC CAAA search field values to improve their search, OR ask a clarifying question

AVAILABLE CAAA SEARCH FIELDS (use these exact keys in suggestions):
- keyword: Simple keyword search
- keywords_all: Must contain ALL these keywords (comma-separated: "term1, term2, term3") - USE THIS AS YOUR PRIMARY TOOL
- keywords_phrase: DO NOT USE THIS FIELD - it returns 0 results. Leave it null.
- keywords_any: At least ONE of these (comma-separated: "term1, term2, term3")
- keywords_exclude: Must NOT contain these (comma-separated)
- listserv: "all", "lawnet" (applicant), "lavaaa" (defense), "lamaaa", or "scaaa"
- date_from: DO NOT USE unless user explicitly asks for a date range
- date_to: DO NOT USE unless user explicitly asks for a date range
- posted_by: Filter by poster's email/name
- last_name: Author's last name
- search_in: "subject_and_body" or "subject_only"
- attachments: "all", "with_attachments", or "without_attachments"

CRITICAL RULES:
1. DO NOT use keywords_phrase - it always returns 0 results. Leave it null or omit it.
2. DO NOT use date_from or date_to unless the user EXPLICITLY asks for "recent" or a specific time period
3. The user did NOT ask for dates, so DO NOT include date_from or date_to in your suggestions
4. ALWAYS use comma-separated values for keywords_all, keywords_any, keywords_exclude
5. Use keywords_all as your primary tool - put all important terms there
6. Return suggestions as a dictionary with field names as keys and values as strings
7. If their fields are good, set suggestions to null

Respond in JSON format:
{{
  "analysis": "Your analysis and advice (2-3 sentences)",
  "suggestions": {{
    "keywords_all": "term1, term2, term3",
    "keywords_phrase": "exact phrase here",
    "listserv": "lawnet"
  }} OR null if current fields are good,
  "follow_up_question": "A specific question to ask, or null"
}}

CRITICAL: suggestions must be a dictionary of field names and values, NOT a list or string of instructions!
"""
        
        response = orchestrator.client.chat.completions.create(
            model="qwen3:14b",
            messages=[
                {"role": "system", "content": "You are a California workers' compensation legal research expert."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return {
            "success": True,
            "analysis": result.get("analysis", ""),
            "suggestions": result.get("suggestions"),
            "follow_up_question": result.get("follow_up_question")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/follow-up")
async def ai_follow_up(request: AIFollowUpRequest):
    """Continue AI conversation with user's answer to follow-up question"""
    
    try:
        if not orchestrator.client:
            raise HTTPException(status_code=503, detail="AI service not available")
        
        # Build conversation history
        messages = [
            {"role": "system", "content": "You are a California workers' compensation legal research expert."}
        ]
        
        # Add conversation history
        for msg in request.conversation[-4:]:  # Last 4 messages for context
            if msg['role'] == 'user':
                messages.append({"role": "user", "content": msg['content']})
            elif msg['role'] == 'ai':
                messages.append({"role": "assistant", "content": msg['content']})
        
        # Add latest answer
        messages.append({
            "role": "user",
            "content": f"User's answer: {request.answer}\n\nCurrent fields: {json.dumps(request.current_fields)}\n\nBased on this, provide final search recommendations in JSON format with: analysis, suggestions, follow_up_question (or null if done)."
        })
        
        response = orchestrator.client.chat.completions.create(
            model="qwen3:14b",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return {
            "success": True,
            "analysis": result.get("analysis", ""),
            "suggestions": result.get("suggestions"),
            "follow_up_question": result.get("follow_up_question")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    
    # Import here to avoid circular dependency
    from search_params import SearchParams
    from query_enhancer import QueryEnhancer
    
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
        if search_params.keywords_all:
            intent_parts.append(f"messages containing all: {search_params.keywords_all}")
        if search_params.keywords_phrase:
            intent_parts.append(f"exact phrase: {search_params.keywords_phrase}")
        if search_params.keywords_any:
            intent_parts.append(f"containing: {search_params.keywords_any}")
        if search_params.author_last_name:
            intent_parts.append(f"by author: {search_params.author_last_name}")
        if search_params.posted_by:
            intent_parts.append(f"posted by: {search_params.posted_by}")
        
        ai_intent = "Looking for " + ", ".join(intent_parts) if intent_parts else "all messages matching search criteria"
        print(f"📝 Generated AI intent from search fields: {ai_intent}", flush=True)
    
    # Create search record
    search_id = orchestrator.db.create_search(search_params)
    orchestrator.db.update_search_status(search_id, 'running')
    
    # Run as subprocess to avoid Playwright threading issues
    import subprocess
    import os
    
    # Set environment variables for worker
    worker_env = os.environ.copy()
    worker_env.update({
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

