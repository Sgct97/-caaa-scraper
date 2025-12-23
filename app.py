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
    query_type: str = "general"  # "general", "doctor_evaluation", "judge_evaluation", "adjuster_evaluation", or "defense_attorney_evaluation"
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
        print(f"   query_type: {search_req.query_type}")
        print(f"   search_fields: {search_req.search_fields}")
        print(f"   ai_intent: {search_req.ai_intent}")
        print(f"   use_ai_enhancement: {search_req.use_ai_enhancement}")
        
        # Validate based on query type
        if search_req.query_type == "doctor_evaluation":
            if not search_req.ai_intent:
                raise HTTPException(status_code=400, detail="Doctor evaluation requires ai_intent with doctor name")
        elif search_req.query_type == "judge_evaluation":
            if not search_req.ai_intent:
                raise HTTPException(status_code=400, detail="Judge evaluation requires ai_intent with judge name")
        elif search_req.query_type == "adjuster_evaluation":
            if not search_req.ai_intent:
                raise HTTPException(status_code=400, detail="Adjuster evaluation requires ai_intent with adjuster name")
        elif search_req.query_type == "defense_attorney_evaluation":
            if not search_req.ai_intent:
                raise HTTPException(status_code=400, detail="Defense attorney evaluation requires ai_intent with attorney name")
        else:
            if not search_req.search_fields and not search_req.ai_intent:
                raise HTTPException(status_code=400, detail="Must provide search fields or AI intent")
        
        # Start search in background
        search_id = await run_search_async(
            search_req.query_type,
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
        
        # Get synthesis result if this is a doctor evaluation
        synthesis_result = orchestrator.db.get_synthesis_result(search_id)
        
        # Convert all database results to JSON-safe format
        response = {
            "success": True,
            "search_id": search_id,
            "query": search_info.get('keyword'),
            "status": search_info['status'],
            "stats": dict(stats) if stats else {},
            "results": [dict(r) for r in results]
        }
        
        # Add synthesis result if available
        if synthesis_result:
            response["synthesis"] = synthesis_result
        
        return convert_decimals(response, for_json_api=True)
        
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
        
        # Get synthesis result if this is a doctor evaluation
        synthesis_result = orchestrator.db.get_synthesis_result(search_id)
        
        response = {
            "success": True,
            "search_id": search_id,
            "search_info": convert_decimals(dict(search_info)) if search_info else {},
            "results": convert_decimals([dict(r) for r in results]) if results else [],
            "stats": convert_decimals(dict(stats)) if stats else {}
        }
        
        # Add synthesis result if available
        if synthesis_result:
            response["synthesis"] = synthesis_result
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# Feedback Endpoints
# ============================================================

class SynthesisFeedbackRequest(BaseModel):
    search_id: str
    is_positive: bool
    comment: Optional[str] = None

class MessageFeedbackRequest(BaseModel):
    search_id: str
    message_id: str
    is_positive: bool
    comment: Optional[str] = None

@app.post("/api/feedback/synthesis")
async def save_synthesis_feedback(request: SynthesisFeedbackRequest):
    """Save feedback on a synthesis (evaluation) result"""
    try:
        feedback_id = orchestrator.db.save_synthesis_feedback(
            request.search_id,
            request.is_positive,
            request.comment
        )
        return {"success": True, "feedback_id": feedback_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/feedback/message")
async def save_message_feedback(request: MessageFeedbackRequest):
    """Save feedback on an individual message analysis"""
    try:
        feedback_id = orchestrator.db.save_message_feedback(
            request.search_id,
            request.message_id,
            request.is_positive,
            request.comment
        )
        return {"success": True, "feedback_id": feedback_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/feedback/{search_id}")
async def get_feedback(search_id: str):
    """Get all feedback for a search"""
    try:
        synthesis_feedback = orchestrator.db.get_synthesis_feedback(search_id)
        message_feedback = orchestrator.db.get_message_feedback(search_id)
        return {
            "success": True,
            "synthesis_feedback": dict(synthesis_feedback) if synthesis_feedback else None,
            "message_feedback": [dict(f) for f in message_feedback] if message_feedback else []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search-history")
async def get_search_history(limit: int = 50):
    """Get recent search history"""
    try:
        with orchestrator.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        s.id,
                        s.search_number,
                        COALESCE(
                            s.search_params->>'ai_intent',
                            s.keyword,
                            s.search_params->>'keywords_any',
                            s.search_params->>'keywords_all',
                            s.search_params->>'keywords_phrase',
                            s.search_params->>'s_keyword',
                            s.search_params->>'s_key_one',
                            CASE WHEN (s.search_params->>'s_postedby') IS NOT NULL 
                                 THEN CONCAT('Posted by: ', s.search_params->>'s_postedby')
                                 ELSE NULL END,
                            CASE WHEN (s.search_params->>'s_lname') IS NOT NULL 
                                 THEN CONCAT('Name search: ', COALESCE(s.search_params->>'s_fname', ''), ' ', COALESCE(s.search_params->>'s_lname', ''))
                                 ELSE NULL END,
                            CASE WHEN (s.search_params->>'s_fname') IS NOT NULL 
                                 THEN CONCAT('Name search: ', COALESCE(s.search_params->>'s_fname', ''))
                                 ELSE NULL END,
                            'Search'
                        ) as query_text,
                        s.search_params->>'ai_intent' as ai_intent,
                        s.status,
                        s.created_at,
                        (SELECT COUNT(*) FROM search_results WHERE search_id = s.id) as result_count,
                        (SELECT COUNT(*) FROM analyses WHERE search_id = s.id AND is_relevant = true) as relevant_count,
                        sf.is_positive as feedback_positive
                    FROM searches s
                    LEFT JOIN synthesis_feedback sf ON sf.search_id = s.id
                    ORDER BY s.created_at DESC
                    LIMIT %s
                """, (limit,))
                
                results = cur.fetchall()
                
                history = []
                for row in results:
                    history.append({
                        'id': row[0],
                        'search_number': row[1],
                        'query': row[2],  # query_text from COALESCE
                        'ai_intent': row[3],
                        'status': row[4],
                        'created_at': row[5].isoformat() if row[5] else None,
                        'result_count': row[6] or 0,
                        'relevant_count': row[7] or 0,
                        'feedback_positive': row[8]  # True, False, or None
                    })
                
                return {"success": True, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/analyze")
async def ai_analyze(request: AIAnalyzeRequest):
    """AI analyzes user intent - asks follow-up if vague, uses QueryEnhancer if specific"""
    
    try:
        if not orchestrator.client:
            raise HTTPException(status_code=503, detail="AI service not available")
        
        # STEP 1: Check if query is too vague and needs clarification
        vagueness_check = f"""You are the Vagueness Checker in a 3-part legal research system:

SYSTEM OVERVIEW:
1. YOU (Vagueness Checker) → Determine if query needs clarification to identify the REAL question
2. Query Enhancer → Translates the REAL question into search parameters
3. Relevance Analyzer → Scores messages for how well they answer the REAL question

YOUR SPECIFIC ROLE:
You are an expert California workers' compensation attorney. The user is also a California workers' compensation attorney using this system. Your job is to determine if a user's typed question contains enough information for the Query Enhancer to understand their REAL legal question and generate effective search parameters.

THE REAL QUESTION CONCEPT:
Users often ask imprecise questions. Their REAL question (what they actually want to know) may differ from what they typed. Your job is to identify when the gap between their typed question and their REAL question is too large for the Query Enhancer to bridge without clarification.

IMPORTANT - USER CONTEXT:
The user is a California workers' compensation attorney. When asking follow-up questions, assume they understand legal terminology, acronyms (QME, IMR, SIBTF, LC, PD, WCAB, etc.), and the workers' compensation system. Ask professional, attorney-to-attorney clarifying questions - do not explain basic legal concepts or treat them as non-experts.

TO MAKE THIS DETERMINATION, YOU NEED TO KNOW:
The Query Enhancer can generate search parameters using these fields:
- posted_by: Filter by WHO SENT the message (listserv poster)
- author_first_name + author_last_name: Filter by WITNESS/EXPERT mentioned (QMEs, doctors, medical experts)
- keyword: Simple keyword search
- keywords_all: Must contain ALL these keywords (comma-separated)
- keywords_any: Must contain at least ONE of these keywords (comma-separated) - PRIMARY TOOL for broad searches
- keywords_phrase: Exact phrase match
- keywords_exclude: Must NOT contain these keywords
- listserv: Filter by list ("all", "lawnet", "lavaaa", "lamaaa", "scaaa")
- attachment_filter: Filter by attachments ("all", "with_attachments", "without_attachments")
- date_from / date_to: Filter by date range (YYYY-MM-DD)
- search_in: Search "subject_and_body" or "subject_only"

WHEN TO ASK FOLLOW-UPS:
Ask a follow-up ONLY when:
- The Query Enhancer would generate SIGNIFICANTLY different search parameters depending on interpretation
- Missing information would cause the Query Enhancer to make assumptions that could lead to irrelevant results
- The question is so broad that any search would return too many irrelevant messages

WHEN NOT TO ASK:
- The question is clear enough for an expert attorney to infer the REAL question
- Common legal terms/acronyms are used (QME, IMR, SIBTF, LC, PD, etc.) - trust your expertise
- The Query Enhancer can reasonably infer the REAL question from context
- Person names with clear intent markers ("BY X" = posted_by, "QME Dr. X" = author fields)

YOUR EXPERTISE:
As an expert California workers' compensation attorney, you recognize when a question is clear enough, even if it's not perfectly precise. Trust that expertise. Only ask follow-ups when genuinely necessary to identify the REAL question.

USER'S TYPED QUESTION: "{request.intent}"

Determine if this query needs clarification before proceeding to Query Enhancement. Return JSON:
{{
  "is_vague": true/false,
  "follow_up_question": "specific clarifying question that helps identify the REAL question" OR null,
  "reasoning": "brief explanation of why vague or why clear"
}}"""

        vagueness_response = orchestrator.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": vagueness_check + " Respond with JSON only."}]
        )
        
        _raw = vagueness_response.content[0].text
        import re as _re
        _match = _re.search(r"\{[\s\S]*\}", _raw)
        vagueness_result = json.loads(_match.group() if _match else _raw)
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

@app.get("/admin/refresh-cookies", response_class=HTMLResponse)
async def refresh_cookies_page():
    """Web page for refreshing CAAA login cookies
    
    EMAIL THIS LINK TO USER: http://134.199.196.31:8000/admin/refresh-cookies
    Or add a button to frontend that opens this in new tab
    """
    import subprocess
    import time
    
    # Stop persistent browser
    subprocess.run(["systemctl", "stop", "caaa-browser"], capture_output=True)
    
    # Kill any existing VNC processes
    subprocess.run(["pkill", "-f", "Xvfb"], capture_output=True)
    subprocess.run(["pkill", "-f", "x11vnc"], capture_output=True)
    subprocess.run(["pkill", "-f", "websockify"], capture_output=True)
    time.sleep(1)
    
    # Start Xvfb (virtual framebuffer) on display :99
    subprocess.Popen(
        ["Xvfb", ":99", "-screen", "0", "1280x1024x24"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(1)
    
    # Start x11vnc to expose the display
    subprocess.Popen(
        ["x11vnc", "-display", ":99", "-forever", "-nopw", "-shared"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(1)
    
    # Start noVNC websocket proxy (web browser accessible VNC on port 6080)
    subprocess.Popen(
        ["websockify", "--web=/usr/share/novnc", "6080", "localhost:5900"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(1)
    
    # Launch cookie capture WEB script in background on VNC display
    subprocess.Popen(
        ["/srv/caaa_scraper/venv/bin/python", "/srv/caaa_scraper/cookie_capture_web.py"],
        env={"DISPLAY": ":99", "PATH": "/usr/bin:/bin"},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Refresh CAAA Login</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { color: #333; }
            .step {
                background: #e3f2fd;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                border-left: 4px solid #2196f3;
            }
            .btn {
                display: inline-block;
                padding: 15px 30px;
                background: #2196f3;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-size: 18px;
                margin: 20px 0;
            }
            .btn:hover { background: #1976d2; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 Refresh CAAA Login Cookies</h1>
            
            <div class="step">
                <strong>Step 1:</strong> Click the button below to open the login window
            </div>
            
            <a href="http://134.199.196.31:6080/vnc.html" target="_blank" class="btn">
                🖥️ Open Login Window
            </a>
            
            <div class="step">
                <strong>Step 2:</strong> In the new window, log into CAAA with your credentials
            </div>
            
            <div class="step">
                <strong>Step 3:</strong> After logging in successfully and you can see your dashboard, click the button below:
            </div>
            
            <button onclick="completeLogin()" class="btn" style="background: #4caf50; cursor: pointer; border: none;">
                ✅ I've Finished Logging In
            </button>
            
            <div id="status" style="margin-top: 20px; padding: 15px; border-radius: 5px; display: none;"></div>
            
            <p style="color: #666; margin-top: 30px;">
                <strong>Note:</strong> The login window opens in a remote desktop viewer. 
                Everything happens on the server - nothing is installed on your computer.
            </p>
        </div>
        
        <script>
            async function completeLogin() {
                const statusDiv = document.getElementById('status');
                statusDiv.style.display = 'block';
                statusDiv.style.background = '#fff3cd';
                statusDiv.innerHTML = '⏳ Saving login cookies... please wait...';
                
                try {
                    const response = await fetch('/admin/complete-login', { method: 'POST' });
                    const data = await response.json();
                    
                    // Poll for completion
                    let attempts = 0;
                    const checkStatus = async () => {
                        const statusResp = await fetch('/admin/cookie-status');
                        const status = await statusResp.json();
                        
                        if (status.status === 'complete') {
                            statusDiv.style.background = '#d4edda';
                            statusDiv.innerHTML = '✅ Success! Cookies saved and browser restarted. You can close this tab.';
                        } else if (status.status === 'warning') {
                            statusDiv.style.background = '#fff3cd';
                            statusDiv.innerHTML = '⚠️ Warning: ' + status.message + '<br><br><strong>The auth cookie (mcidme) was not found. This usually means you were not fully logged in when you clicked complete.</strong><br><br>Please try again and make sure you can see your CAAA dashboard before clicking the button.';
                        } else if (status.status === 'error') {
                            statusDiv.style.background = '#f8d7da';
                            statusDiv.innerHTML = '❌ Error: ' + status.message;
                        } else if (attempts < 30) {
                            attempts++;
                            statusDiv.innerHTML = '⏳ ' + (status.message || 'Processing...') + ' (' + attempts + 's)';
                            setTimeout(checkStatus, 1000);
                        } else {
                            statusDiv.style.background = '#f8d7da';
                            statusDiv.innerHTML = '❌ Timeout - please try again';
                        }
                    };
                    
                    setTimeout(checkStatus, 2000);
                } catch (e) {
                    statusDiv.style.background = '#f8d7da';
                    statusDiv.innerHTML = '❌ Error: ' + e.message;
                }
            }
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.post("/admin/complete-login")
async def complete_login():
    """Signal that user has completed login - triggers cookie capture"""
    signal_file = "/srv/caaa_scraper/login_complete.signal"
    with open(signal_file, "w") as f:
        f.write("done")
    return {"status": "ok", "message": "Login completion signal sent"}

@app.get("/admin/cookie-status")
async def cookie_status():
    """Get current status of cookie capture process"""
    status_file = "/srv/caaa_scraper/cookie_status.json"
    if os.path.exists(status_file):
        with open(status_file, "r") as f:
            return json.load(f)
    return {"status": "unknown", "message": "No status available"}

# ============================================================
# Helper Functions
# ============================================================

async def run_search_async(query_type: str, search_fields: Optional[dict], ai_intent: Optional[str], 
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
        # For doctor evaluation, force AI enhancement to find doctor
        if query_type == "doctor_evaluation":
            # Extract doctor name from ai_intent (format: "Evaluate doctor: Dr. John Smith")
            doctor_name = ai_intent.replace("Evaluate doctor:", "").strip()
            # Use QueryEnhancer to find the doctor
            search_params = orchestrator.query_enhancer.enhance_query(f"Find all messages mentioning doctor {doctor_name}")
        elif query_type == "judge_evaluation":
            # Extract judge name from ai_intent (format: "Evaluate judge: Judge Smith")
            judge_name = ai_intent.replace("Evaluate judge:", "").strip()
            # Strip common prefixes to get clean name for keywords_all
            clean_name = judge_name.replace("Judge ", "").replace("Hon. ", "").replace("Hon ", "").replace("WCJ ", "").replace("Honorable ", "").strip()
            # DETERMINISTIC: keywords_all=name (MUST HAVE), keywords_any=judge context words
            search_params = SearchParams(
                keywords_all=clean_name,
                keywords_any="judge, WCJ, Hon, Honorable, ruling, decision, presiding, presided, tribunal, hearing, bench, courtroom"
            )
        elif query_type == "adjuster_evaluation":
            # Extract adjuster name from ai_intent (format: "Evaluate adjuster: John Smith")
            adjuster_name = ai_intent.replace("Evaluate adjuster:", "").strip()
            # Use QueryEnhancer to find the adjuster
            search_params = orchestrator.query_enhancer.enhance_query(f"Find all messages mentioning adjuster {adjuster_name}")
        elif query_type == "defense_attorney_evaluation":
            # Extract defense attorney name from ai_intent (format: "Evaluate defense attorney: John Smith")
            defense_attorney_name = ai_intent.replace("Evaluate defense attorney:", "").strip()
            # Get clean last name for keywords_all (handle "First Last" format)
            name_parts = defense_attorney_name.split()
            clean_name = name_parts[-1] if name_parts else defense_attorney_name  # Use last name
            # DETERMINISTIC: keywords_all=name (MUST HAVE), keywords_any=defense attorney context words
            search_params = SearchParams(
                keywords_all=clean_name,
                keywords_any="defense, defendant, opposing, counsel, attorney, negotiate, settlement, deposition, lien"
            )
        elif query_type == "insurance_company_evaluation":
            # Extract insurance company info from ai_intent
            # Format: "Evaluate insurance company: Name" or "Evaluate insurance company: Name (also known as: Abbrev)"
            raw_company_info = ai_intent.replace("Evaluate insurance company:", "").strip()
            
            # Parse out the abbreviation if provided
            import re
            abbrev_match = re.search(r'\(also known as:\s*([^)]+)\)', raw_company_info)
            if abbrev_match:
                user_abbreviation = abbrev_match.group(1).strip()
                insurance_company_name = re.sub(r'\s*\(also known as:[^)]+\)', '', raw_company_info).strip()
            else:
                user_abbreviation = None
                insurance_company_name = raw_company_info
            
            # Use AI to determine the best search term
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                
                prompt = f"""For the California workers' compensation insurance company "{insurance_company_name}"{f' (also known as: {user_abbreviation})' if user_abbreviation else ''}, what is the MOST COMMON way attorneys refer to this company in casual discussion?

Return ONLY the single most common term/abbreviation, nothing else. Examples:
- "State Compensation Insurance Fund" → SCIF
- "Liberty Mutual Insurance Company" → Liberty Mutual  
- "Zenith Insurance" → Zenith
- "American International Group" → AIG

Response (just the term):"""

                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=50,
                    temperature=0,
                    messages=[{"role": "user", "content": prompt}]
                )
                best_search_term = response.content[0].text.strip()
                print(f"🤖 AI determined best search term for '{insurance_company_name}': '{best_search_term}'", flush=True)
            except Exception as e:
                print(f"⚠️ AI abbreviation lookup failed: {e}, using user input", flush=True)
                # Fallback: use user abbreviation if provided, otherwise first word of company name
                best_search_term = user_abbreviation if user_abbreviation else insurance_company_name.split()[0]
            
            # Use AI-determined term in keywords_all
            search_params = SearchParams(
                keywords_all=best_search_term,
                keywords_any="insurance, carrier, insurer, claim, adjuster, authorization, denial, coverage, settlement, premium"
            )
        else:
            search_params = orchestrator.query_enhancer.enhance_query(ai_intent)
    else:
        # Fallback to simple keyword from AI intent
        search_params = SearchParams(keyword=ai_intent or "")
    
    # Apply limits
    search_params.max_messages = max_messages
    search_params.max_pages = max_pages
    
    # CRITICAL: If user provided manual search_fields, reconstruct ai_intent from ACTUAL fields being used
    # This ensures the REAL question matches what the user is actually searching for, not the original query
    if search_fields:
        # User is using manual fields (either applied AI suggestions or manually entered)
        # Reconstruct ai_intent from the ACTUAL search parameters to ensure relevance analysis uses correct question
        intent_parts = []
        has_content_criteria = False
        
        # Content-based criteria
        if search_params.keywords_all:
            intent_parts.append(f"messages containing all: {search_params.keywords_all}")
            has_content_criteria = True
        if search_params.keywords_phrase:
            intent_parts.append(f"exact phrase: {search_params.keywords_phrase}")
            has_content_criteria = True
        if search_params.keywords_any:
            intent_parts.append(f"containing: {search_params.keywords_any}")
            has_content_criteria = True
        if search_params.keyword:
            intent_parts.append(f"keyword: {search_params.keyword}")
            has_content_criteria = True
        if search_params.keywords_exclude:
            intent_parts.append(f"excluding: {search_params.keywords_exclude}")
            has_content_criteria = True
        
        # Author/Person criteria
        author_criteria = []
        if search_params.posted_by:
            author_criteria.append(f"posted by: {search_params.posted_by}")
        if search_params.author_first_name and search_params.author_last_name:
            author_criteria.append(f"expert: {search_params.author_first_name} {search_params.author_last_name}")
        elif search_params.author_first_name:
            author_criteria.append(f"expert first name: {search_params.author_first_name}")
        elif search_params.author_last_name:
            author_criteria.append(f"expert: {search_params.author_last_name}")
        
        # Temporal criteria
        temporal_criteria = []
        if search_params.date_from:
            temporal_criteria.append(f"from {search_params.date_from}")
        if search_params.date_to:
            temporal_criteria.append(f"until {search_params.date_to}")
        
        # Listserv filter
        listserv_info = ""
        if search_params.listserv and search_params.listserv != "all":
            listserv_info = f" on {search_params.listserv} listserv"
        
        # Attachment filter
        attachment_info = ""
        if search_params.attachment_filter == "with_attachments":
            attachment_info = " with attachments"
        elif search_params.attachment_filter == "without_attachments":
            attachment_info = " without attachments"
        
        # Search scope
        search_scope = ""
        if search_params.search_in == "subject_only":
            search_scope = " (subject line only)"
        
        # Construct the REAL question from all criteria
        all_criteria = intent_parts + author_criteria + temporal_criteria
        base_intent = ", ".join(all_criteria) if all_criteria else "all messages"
        
        # If ONLY author criteria (no content keywords), make it clear we want ALL messages from that person
        if author_criteria and not has_content_criteria and not temporal_criteria:
            ai_intent = f"Find ALL messages from {', '.join(author_criteria)}{listserv_info}{attachment_info}{search_scope}. Any message from this person is relevant regardless of content."
        elif all_criteria:
            ai_intent = f"Looking for {base_intent}{listserv_info}{attachment_info}{search_scope}"
        else:
            ai_intent = f"all messages matching search criteria{listserv_info}{attachment_info}{search_scope}"
        
        print(f"📝 Reconstructed AI intent from ACTUAL search fields: {ai_intent}", flush=True)
    # If no AI intent provided and no search_fields, construct one from search parameters for relevance analysis
    elif not ai_intent or ai_intent.strip() == "":
        intent_parts = []
        has_content_criteria = False
        
        # Content-based criteria
        if search_params.keywords_all:
            intent_parts.append(f"messages containing all: {search_params.keywords_all}")
            has_content_criteria = True
        if search_params.keywords_phrase:
            intent_parts.append(f"exact phrase: {search_params.keywords_phrase}")
            has_content_criteria = True
        if search_params.keywords_any:
            intent_parts.append(f"containing: {search_params.keywords_any}")
            has_content_criteria = True
        if search_params.keyword:
            intent_parts.append(f"keyword: {search_params.keyword}")
            has_content_criteria = True
        if search_params.keywords_exclude:
            intent_parts.append(f"excluding: {search_params.keywords_exclude}")
            has_content_criteria = True
        
        # Author/Person criteria
        author_criteria = []
        if search_params.posted_by:
            author_criteria.append(f"posted by: {search_params.posted_by}")
        if search_params.author_first_name and search_params.author_last_name:
            author_criteria.append(f"expert: {search_params.author_first_name} {search_params.author_last_name}")
        elif search_params.author_first_name:
            author_criteria.append(f"expert first name: {search_params.author_first_name}")
        elif search_params.author_last_name:
            author_criteria.append(f"expert: {search_params.author_last_name}")
        
        # Temporal criteria
        temporal_criteria = []
        if search_params.date_from:
            temporal_criteria.append(f"from {search_params.date_from}")
        if search_params.date_to:
            temporal_criteria.append(f"until {search_params.date_to}")
        
        # Listserv filter
        listserv_info = ""
        if search_params.listserv and search_params.listserv != "all":
            listserv_info = f" on {search_params.listserv} listserv"
        
        # Attachment filter
        attachment_info = ""
        if search_params.attachment_filter == "with_attachments":
            attachment_info = " with attachments"
        elif search_params.attachment_filter == "without_attachments":
            attachment_info = " without attachments"
        
        # Search scope
        search_scope = ""
        if search_params.search_in == "subject_only":
            search_scope = " (subject line only)"
        
        # Construct the REAL question from all criteria
        all_criteria = intent_parts + author_criteria + temporal_criteria
        base_intent = ", ".join(all_criteria) if all_criteria else "all messages"
        
        # If ONLY author criteria (no content keywords), make it clear we want ALL messages from that person
        if author_criteria and not has_content_criteria and not temporal_criteria:
            ai_intent = f"Find ALL messages from {', '.join(author_criteria)}{listserv_info}{attachment_info}{search_scope}. Any message from this person is relevant regardless of content."
        elif all_criteria:
            ai_intent = f"Looking for {base_intent}{listserv_info}{attachment_info}{search_scope}"
        else:
            ai_intent = f"all messages matching search criteria{listserv_info}{attachment_info}{search_scope}"
        
        print(f"📝 Generated AI intent from search fields: {ai_intent}", flush=True)
    
    # Create search record (store ai_intent as REAL question)
    print(f"🔵 Creating search in database", flush=True)
    search_id = orchestrator.db.create_search(search_params, ai_intent=ai_intent)
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
            ai_intent,
            query_type  # Pass query_type to worker
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

