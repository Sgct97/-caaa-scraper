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
    query: str
    use_ai_enhancement: bool = True
    max_messages: int = 100
    max_pages: int = 10

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
        # Validate query
        if not search_req.query or len(search_req.query.strip()) == 0:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Start search in background
        search_id = await run_search_async(
            search_req.query,
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

async def run_search_async(query: str, use_ai: bool, max_messages: int, max_pages: int) -> str:
    """Run search asynchronously"""
    
    # Import here to avoid circular dependency
    from search_params import SearchParams
    from query_enhancer import QueryEnhancer
    
    # Get AI-enhanced params if enabled
    if use_ai and orchestrator.query_enhancer:
        search_params = orchestrator.query_enhancer.enhance_query(query)
    else:
        search_params = SearchParams(keyword=query)
    
    # Apply limits
    search_params.max_messages = max_messages
    search_params.max_pages = max_pages
    
    # Create search record
    search_id = orchestrator.db.create_search(search_params)
    orchestrator.db.update_search_status(search_id, 'running')
    
    # Run in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_search_sync, search_id, search_params, query)
    
    return search_id

def run_search_sync(search_id: str, search_params, query: str):
    """Synchronous search execution (runs in background)"""
    
    try:
        # Scrape
        messages = orchestrator.scraper.scrape(search_params)
        
        # Store messages
        for msg in messages:
            message_id = orchestrator.db.get_or_create_message(msg['caaa_message_id'], msg)
            orchestrator.db.add_search_result(search_id, message_id, msg['position'], msg['page'])
        
        orchestrator.db.update_search_status(search_id, 'running', total_found=len(messages))
        
        # Analyze relevance with AI
        if orchestrator.ai_analyzer:
            relevant_count = orchestrator._analyze_relevance(search_id, messages, query)
        else:
            relevant_count = len(messages)
        
        # Mark complete
        orchestrator.db.update_search_status(search_id, 'completed', total_relevant=relevant_count)
        
    except Exception as e:
        orchestrator.db.update_search_status(search_id, 'failed')
        print(f"❌ Search {search_id} failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

